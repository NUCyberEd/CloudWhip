__author__ = 'shekar_n_h'

import sys
import logging
import getTags
import os
import secGroups
import time
import netIps


class VpcSetUp(object):
    def __init__(self, vpcConnection, ec2Connection):
        self.conn = vpcConnection
        self.ec2Conn = ec2Connection  # ec2 connection for security groups
        self.getTags = getTags.GetTags(
            os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'all_tags.yaml'))
        self.ipAddrBlks = netIps.NetIps()
        self.logger = logging.getLogger(__name__)

    # TODO: verify if required filed exists[cidr_block]
    def verify_vpc_fields(self):
        pass

    def get_vpc_settings(self, name=None, vpc_items=[]):
        vpc_settings = {}
        for v_setting in vpc_items:
            if v_setting['name'] == name:
                vpc_settings = v_setting
                break
        if not len(vpc_settings):
            self.logger.error("'{0}' VPC Name not found in the config file".format(name))
            sys.exit(2)
        return vpc_settings

    def set_up_internet_gw(self, v_id, v_setting):
        # check if gateway exists and attached before
        if not self.conn.get_all_internet_gateways(filters={'attachment.vpc-id': v_id.id}):
            internet_gw = self.conn.create_internet_gateway()
            time.sleep(3)
            #attach Internet Gateway
            self.conn.attach_internet_gateway(internet_gw.id, v_id.id)
            # add name tag for Internet Gateway
            internet_gw.add_tag("Name", "{0}_internet_gw".format(v_setting['name']))
            self.logger.info("Internet Gateway Created and attached -- {0}".format(internet_gw.id))
            internet_gw_id = internet_gw.id
        else:
            internet_gw_id = self.conn.get_all_internet_gateways(filters={'attachment.vpc-id': v_id.id})[0]

        return internet_gw_id

    def set_up_route_table(self, v_id, sub_id, int_gw_id, sub_setting, sub_idx):
        # create route tables
        route_table = self.conn.create_route_table(v_id.id)
        time.sleep(3)
        # add tag
        route_table.add_tag("Name", "{0}_{1}_rt".format(sub_setting['subnet_group_name'], sub_idx))

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
                    target = int_gw_id
            except IndexError:
                target = int_gw_id
            rt_id = self.conn.create_route(route_table.id, str(dest), gateway_id=target)
            # **************
            # while not rt_id:
            #     self.logger.debug("Route for {0}_{1} created but waiting for it to be available".format(sub_setting['subnet_group_name'], sub_idx))
            #     time.sleep(3)
        self.logger.info("Route Table and Routes Created for subnet -- {0}_{1}".format(sub_setting['subnet_group_name'], sub_idx))

    def create_vpc(self, vpcSettings=[], vpcList=[], dryRun_flag=False):
        # create VPC and Subnet
        vpc_setting = vpcSettings
        resultIds = {}

        if not len(vpcSettings):
            self.logger.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        #for each item in vpcList setup the VPCs on cloud
        if not len(vpcList):
            #default select all VPCs
            for vpc_list in vpc_setting:
                vpcList.append(vpc_list['name'])
        for vpc_item in vpcList:
            current_vpc_setting = self.get_vpc_settings(vpc_item, vpc_setting)
            # verify if the vpc exists
            verify_vpc = self.conn.get_all_vpcs(filters={"cidrBlock": current_vpc_setting['cidr_block']})
            if not len(verify_vpc):
                vpc_id = self.conn.create_vpc(current_vpc_setting['cidr_block'], current_vpc_setting['instance_tenancy'],
                                             dry_run=dryRun_flag)
                self.logger.info("VPC Created -- {0}".format(vpc_id.id))
                resultIds['vpc'] = vpc_id.id
            else:
                vpc_id = verify_vpc.pop(0)
                self.logger.warning("Resquested VPC already exists! -- {0}".format(vpc_id.id))

            while vpc_id.state != 'available':
                self.logger.debug("VPC {0} created but waiting for it to be available".format(current_vpc_setting['name']))
                time.sleep(3)
                vpc_id.update()
            # Add name tag
            vpc_id.add_tag("Name", "{0}_vpc".format(current_vpc_setting['name']))

            # Set up internet GW for the VPC
            internet_gateway = self.set_up_internet_gw(vpc_id, current_vpc_setting)

            # for each subnet config found create them if already do not exist
            created_subnet = []
            for subnet_setting in current_vpc_setting['subnet_settings']:
                current_subnet_cnt = int(subnet_setting['count'])
                current_subnet_grp_cidr_blks = self.ipAddrBlks.generate_cidr_blocks(subnet_setting['subnet_cidr_block'])
                if current_subnet_cnt != len(current_subnet_grp_cidr_blks):
                    self.logger.error("Subnet count and Subnet CIDR Block range do not match for {0}".format(subnet_setting['subnet_group_name']))
                    sys.exit(2)
                # loop through each CIDR Block range
                subnet_idx = 1
                for current_cidr_blk in current_subnet_grp_cidr_blks:
                    verify_subnet = self.conn.get_all_subnets(filters={"cidrBlock": current_cidr_blk})
                    if not len(verify_subnet):
                        subnet_id = self.conn.create_subnet(vpc_id.id, current_cidr_blk, dryRun_flag)
                        self.logger.info("Created Subnet -- {0}".format(subnet_id.id))
                        # setup route table
                        self.set_up_route_table(vpc_id, subnet_id, internet_gateway, subnet_setting, subnet_idx)
                    else:
                        subnet_id = verify_subnet.pop(0)
                        self.logger.warning("Resquested Subnet already exists! -- {0}".format(subnet_id.id))
                    subnet_id.add_tag("Name", "{0}_{1}".format(subnet_setting['subnet_group_name'], subnet_idx))
                    subnet_idx += 1
                resultIds['subnets'] = created_subnet

            # update tag file
            self.getTags.update_tag_file()

            # create or update security groups
            for sg_setting in current_vpc_setting['security_groups']:
                associate_vpc_id = self.getTags.get_resource_id("{0}_vpc".format(sg_setting['associate_vpc']))[0]
                sg_setup = secGroups.SecurityGroups(self.ec2Conn)
                sg_id = sg_setup.create_security_groups(sg_setting['sg_name'], sg_setting['description'],
                                                associate_vpc_id, sg_setting['rules'])

        # close the connection
        self.conn.close()
        self.ec2Conn.close()

        return resultIds

    def delete_vpc(self, vpcSettings=[], vpcList=[], dryRun_flag=False):
        if not len(vpcSettings):
            self.logger.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        # update the tag file
        self.getTags.update_tag_file()

        #for each item in vpcList delete the VPCs on cloud
        if not len(vpcList):
            #default select all VPCs
            for vpc_list in vpcSettings:
                vpcList.append(vpc_list['name'])

        for vpc_name in vpcList:
            vpc_id = self.getTags.get_resource_id("{0}_vpc".format(vpc_name))[0]
            # check if instance are attached to VPC first.
            instances_attached = self.ec2Conn.get_all_instances(filters={"vpc-id": vpc_id})
            if len(instances_attached):
                self.logger.warning("Instances are attched to the VPC {0}.\n"
                                    "Please delete the POD using cloudWhip.py -c pod -a delete -l [pod_name]".format(vpc_name))
                sys.exit(2)
            self.logger.info("Deleting all components attached to '{0}' VPC first.".format(vpc_name))
            # detach and delete security groups
            main_sgs = self.conn.get_all_security_groups(filters={"group-name": 'default', "vpc-id": vpc_id})
            attached_sgs = self.conn.get_all_security_groups(filters={"vpc-id": vpc_id})
            if len(attached_sgs):
                for attached_sg in attached_sgs:
                    if str(attached_sg.id) != str(main_sgs[0].id):
                        self.ec2Conn.delete_security_group(group_id=attached_sg.id)
                        self.logger.debug("Deleted Security Group -- {0}".format(attached_sg.id))

            # detach and delete internet gateways
            attached_internet_gw = self.conn.get_all_internet_gateways(filters={"attachment.vpc-id": vpc_id})
            if len(attached_internet_gw):
                for int_gw in attached_internet_gw:
                    self.conn.detach_internet_gateway(int_gw.id, vpc_id)
                    self.conn.delete_internet_gateway(int_gw.id)
                    self.logger.debug("Deleted Internet Gateway-- {0}".format(int_gw.id))

            # delete the subnets
            attached_subnets = self.conn.get_all_subnets(filters={"vpcId": vpc_id})
            if len(attached_subnets):
                for s_id in attached_subnets:
                    self.conn.delete_subnet(s_id.id)
                    self.logger.debug("Deleted Subnet -- {0}".format(s_id.id))

            # delete route tables
            main_route_tables = self.conn.get_all_route_tables(filters={"association.main": 'true', "vpc-id": vpc_id})
            attached_route_tables = self.conn.get_all_route_tables(filters={"vpc-id": vpc_id})
            if len(attached_route_tables):
                for rt in attached_route_tables:
                    if str(rt.id) != str(main_route_tables[0].id):
                        self.conn.delete_route_table(rt.id)
                        self.logger.debug("Deleted Route Table -- {0}".format(rt.id))

            self.conn.delete_vpc(vpc_id, dry_run=dryRun_flag)
            self.logger.info("VPC '{0}' deleted successfully".format(vpc_name))

        # finally close the connection
        self.conn.close()

    # TODO: Update action
    def update_vpc(self, vpcSettings=[], dryRun_flag=False):
        self.logger.warning("This feature is under development")
        pass