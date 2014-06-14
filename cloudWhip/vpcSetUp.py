__author__ = 'shekar_n_h'

import sys
import logging
import getTags
import os
import secGroups
import time


class VpcSetUp(object):
    def __init__(self, vpcConnection, ec2Connection):
        self.conn = vpcConnection
        self.ec2Conn = ec2Connection  # ec2 connection for security groups
        self.getTags = getTags.GetTags(
            os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'all_tags.yaml'))
        self.logger = logging.getLogger(__name__)

    # TODO: verify if required filed exists[cidr_block]
    def verify_vpc_fields(self):
        pass

    def set_up_internet_gw(self, v_id, v_setting):
        # check if gateway exists and attached before
        if not self.conn.get_all_internet_gateways(filters={'attachment.vpc-id': v_id.id}):
            internet_gw = self.conn.create_internet_gateway()
            #attach Internet Gateway
            self.conn.attach_internet_gateway(internet_gw.id, v_id.id)
            # add name tag for Internet Gateway
            internet_gw.add_tag("Name", v_setting['name_tag'] + "_internet_gw")
            self.logger.info("Internet Gateway Created and attached-- %s", internet_gw.id)
            internet_gw_id = internet_gw.id
        else:
            internet_gw_id = self.conn.get_all_internet_gateways(filters={'attachment.vpc-id': v_id.id})[0]

        return internet_gw_id

    def set_up_route_table(self, v_id, sub_id, int_gw_id, sub_setting):
        # create route tables
        route_table = self.conn.create_route_table(v_id.id)

        # associate with the subnet
        self.conn.associate_route_table(route_table.id, sub_id.id)
        # TODO: Find a better way
        time.sleep(3)
        # add tag
        route_table.add_tag("Name", sub_setting['subnet_name_tag'] + "_rt")

        # add routes
        rules_dict = sub_setting['route_table']
        destination_list = rules_dict['Destination']
        target_list = rules_dict['Target']

        for dest in destination_list:
            try:
                target = target_list[destination_list.index(dest)]
                if not target:
                    target = int_gw_id
            except IndexError:
                target = int_gw_id
            rt_id = self.conn.create_route(route_table.id, str(dest), gateway_id=target)
            while not rt_id:
                self.logger.debug("Route for %s created but waiting for it to be availabel", sub_setting['subnet_name_tag'])

        self.logger.info("Route Table and Routes Created for subnet -- %s", sub_setting['subnet_name_tag'])

    def create_vpc(self, vpcSettings=[], dryRun_flag=False):
        # create VPC and Subnet
        vpc_setting = vpcSettings
        resultIds = {}

        if not len(vpcSettings):
            self.logger.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        # verify if the vpc exists
        verify_vpc = self.conn.get_all_vpcs(filters={"cidrBlock": vpc_setting['cidr_block']})
        if not len(verify_vpc):
            vpc_id = self.conn.create_vpc(vpc_setting['cidr_block'], vpc_setting['instance_tenancy'],
                                         dry_run=dryRun_flag)
            self.logger.info("VPC Created -- %s", vpc_id.id)
            resultIds['vpc'] = vpc_id.id
        else:
            vpc_id = verify_vpc.pop(0)
            while vpc_id.state != 'available':
                self.logger.debug("VPC %s created but waiting for it to be availabel", vpc_setting['name_tag'])
            self.logger.warning("Resquested VPC already exists! -- %s", vpc_id.id)
        # Add name tag
        vpc_id.add_tag("Name", vpc_setting['name_tag'])

        # Set up internet GW for the VPC
        internet_gateway = self.set_up_internet_gw(vpc_id, vpc_setting)

        # for each subnet config found create them if already do not exist
        created_subnet = []
        for subnet_setting in vpc_setting['subnet_settings']:
            verify_subnet = self.conn.get_all_subnets(filters={"cidrBlock": subnet_setting['subnet_cidr_block']})
            if not len(verify_subnet):
                subnet_id = self.conn.create_subnet(vpc_id.id, subnet_setting['subnet_cidr_block'], dryRun_flag)
                self.logger.info("Created Subnet -- %s", subnet_id.id)
                # setup route table
                self.set_up_route_table(vpc_id, subnet_id, internet_gateway, subnet_setting)
            else:
                subnet_id = verify_subnet.pop(0)
                self.logger.warning("Resquested Subnet already exists! -- %s", subnet_id.id)
            subnet_id.add_tag("Name", subnet_setting['subnet_name_tag'])
        resultIds['subnets'] = created_subnet

        # update tag file
        self.getTags.update_tag_file()

        # create or update security groups
        for sg_setting in vpc_setting['security_groups']:
            associate_vpc_id = self.getTags.get_resource_id(sg_setting['associate_vpc'])
            sg_setup = secGroups.SecurityGroups(self.ec2Conn)
            sg_id = sg_setup.create_security_groups(sg_setting['sg_name'], sg_setting['description'],
                                            associate_vpc_id, sg_setting['rules'])

        # close the connection
        self.conn.close()
        self.ec2Conn.close()

        return resultIds
        
    # TODO: procedure to delete given VPC
    # TODO: Check for attached instance
    def delete_vpc(self, vpcSettings=[], dryRun_flag=False):
        if not len(vpcSettings):
            self.logger.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        # self.getTags.update_tag_file()
        for vpc_id in self.conn.get_all_vpcs():
            # detach and delete security groups
            main_sgs = self.conn.get_all_security_groups(filters={"group-name": 'default', "vpc-id": vpc_id.id})
            attached_sgs = self.conn.get_all_security_groups(filters={"vpc-id": vpc_id.id})
            if len(attached_sgs):
                for attached_sg in attached_sgs:
                    if str(attached_sg.id) != str(main_sgs[0].id):
                        self.ec2Conn.delete_security_group(group_id=attached_sg.id)
                        self.logger.info("Deleted Security Group -- %s", attached_sg.id)

            # detach and delete internet gateways
            attached_internet_gw = self.conn.get_all_internet_gateways(filters={"attachment.vpc-id": vpc_id.id})
            if len(attached_internet_gw):
                for int_gw in attached_internet_gw:
                    self.conn.detach_internet_gateway(int_gw.id, vpc_id.id)
                    self.conn.delete_internet_gateway(int_gw.id)
                    self.logger.info("Deleted Internet Gateway-- %s", int_gw.id)

            # delete the subnets
            attached_subnets = self.conn.get_all_subnets(filters={"vpcId": vpc_id.id})
            if len(attached_subnets):
                for s_id in attached_subnets:
                    self.conn.delete_subnet(s_id.id)
                    self.logger.info("Deleted Subnet -- %s", s_id.id)

            # delete route tables
            main_route_tables = self.conn.get_all_route_tables(filters={"association.main": 'true', "vpc-id": vpc_id.id})
            attached_route_tables = self.conn.get_all_route_tables(filters={"vpc-id": vpc_id.id})
            if len(attached_route_tables):
                for rt in attached_route_tables:
                    if str(rt.id) != str(main_route_tables[0].id):
                        self.conn.delete_route_table(rt.id)
                        self.logger.info("Deleted Route Table -- %s", rt.id)

            self.conn.delete_vpc(vpc_id.id, dry_run=dryRun_flag)

            self.conn.close()

    # TODO: Update action
    def update_vpc(self, vpcSettings=[], dryRun_flag=False):
        self.logger.warning("This feature is under development")
        pass