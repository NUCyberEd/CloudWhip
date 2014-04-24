__author__ = 'shekar_n_h'

import sys
import logging
import getTags
import os


class VpcSetUp(object):
    def __init__(self, vpcConnection):
        self.conn = vpcConnection
        self.getTags = getTags.GetTags(
            os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'all_tags.yaml'))
        self.logger = logging.getLogger(__name__)

    # TODO: verify if required filed exists
    def verify_vpc_fields(self):
        pass

    def set_up_internet_gw(self, v_id, v_setting):
        # check if gateway exists and attached before
        if not self.conn.get_all_internet_gateways(filters={'attachment.vpc-id': v_id.id}):
            internet_gw = self.conn.create_internet_gateway()
            # add name tag for Internet Gateway
            internet_gw.add_tag("Name", v_setting['name_tag'] + "_internet_gw")
            #attach Internet Gateway
            self.conn.attach_internet_gateway(internet_gw.id, v_id.id)
            self.logger.info("Internet Gateway Created and attached-- %s", internet_gw.id)
            return internet_gw

    def set_up_route_table(self, v_id, sub_id, int_gw, sub_setting):
        # create route tables
        route_table = self.conn.create_route_table(v_id.id)
        route_table.add_tag("Name", sub_setting['subnet_name_tag'] + "_rt")
        # associate with the subnet
        self.conn.associate_route_table(route_table.id, sub_id.id)
        # add routes
        rules_dict = sub_setting['route_table']
        destination_list = rules_dict['Destination']
        target_list = rules_dict['Target']

        for dest in destination_list:
            try:
                target = target_list[destination_list.index(dest)]
                if not target:
                    target = int_gw.id
            except IndexError:
                target = int_gw.id
            self.conn.create_route(route_table.id, str(dest), gateway_id=target)
        self.logger.info("Route Table and Routes Created for subnet -- %s", sub_setting['subnet_name_tag'])

    def create_vpc(self, vpcSettings=[], dryRun_flag=False):
        # create VPC and Subnet
        vpc_setting = vpcSettings
        resultIds = {}

        if not len(vpcSettings):
            self.logger.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        verify_vpc = self.conn.get_all_vpcs(filters={"cidrBlock": vpc_setting['cidr_block']})
        if not len(verify_vpc):
            vpc_id = self.conn.create_vpc(vpc_setting['cidr_block'], vpc_setting['instance_tenancy'],
                                         dry_run=dryRun_flag)
            self.logger.info("VPC Created -- %s", vpc_id.id)
            resultIds['vpc'] = vpc_id.id
        else:
            vpc_id = verify_vpc.pop(0)
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
        # close the connection
        self.conn.close()
        return resultIds
        
    # TODO: procedure to delete given VPC
    # TODO: Check for attached instance
    def delete_vpc(self, vpcSettings=[], dryRun_flag=False):
        if not len(vpcSettings):
            self.logger.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        # self.getTags.update_tag_file()
        for vpc_id in self.conn.get_all_vpcs():
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
            main_route_table = self.conn.get_all_route_tables(filters={"association.main": 'true'})
            attached_route_table = self.conn.get_all_route_tables(filters={"vpc-id": vpc_id.id})
            if len(attached_route_table):
                for rt in attached_route_table:
                    if str(rt.id) != str(main_route_table[0].id):
                        self.conn.delete_route_table(rt.id)
                        self.logger.info("Deleted Route Table -- %s", rt.id)

            self.conn.delete_vpc(vpc_id.id, dry_run=dryRun_flag)

            self.conn.close()

    # TODO: Update action
    def update_vpc(self, vpcSettings=[], dryRun_flag=False):
        self.logger.warning("This feature is under development")
        pass