__author__ = 'shekar_n_h'

import sys
import logging


class VpcSetUp(object):
    def __init__(self, vpcConnection):
        self.conn = vpcConnection

    # TODO: verify if required filed exists
    def verify_vpc_fields(self):
        pass

    def createVPC(self, vpcSettings=[], dryRun_flag=False):
        # create VPC and Subnet
        vpc_setting = vpcSettings
        resultIds = {}

        if not len(vpcSettings):
            logging.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        verify_vpc = self.conn.get_all_vpcs(filters={"cidrBlock": vpc_setting['cidr_block']})
        if not len(verify_vpc):
            vpc_id = self.conn.create_vpc(vpc_setting['cidr_block'], vpc_setting['instance_tenancy'],
                                         dry_run=dryRun_flag)
            vpc_id_str = str(vpc_id).split(':', 1)[1]
            logging.info("VPC Created -- %s", vpc_id_str)
            resultIds['vpc'] = vpc_id_str
        else:
            vpc_id = verify_vpc.pop(0)
            vpc_id_str = str(vpc_id).split(':', 1)[1]
            logging.warning("Resquested VPC already exists! -- %s", vpc_id_str)
        # Add name tag
        vpc_id.add_tag("Name", vpc_setting['name_tag'])

        # for each subnet config found create them if already do not exist
        created_subnet = []
        for subnet_setting in vpc_setting['subnet_settings']:
            verify_subnet = self.conn.get_all_subnets(filters={"cidrBlock": subnet_setting['subnet_cidr_block']})
            if not len(verify_subnet):
                subnet_id = self.conn.create_subnet(vpc_id_str, subnet_setting['subnet_cidr_block'], dryRun_flag)
                subnet_id_str = str(subnet_id).split(':', 1)[1]
                logging.info("Created Subnet -- %s", subnet_id_str)
                created_subnet.append(subnet_id_str)
            else:
                subnet_id = verify_subnet.pop(0)
                subnet_id_str = str(subnet_id).split(':', 1)[1]
                logging.warning("Resquested Subnet already exists! -- %s", subnet_id_str)
            subnet_id.add_tag("Name", subnet_setting['subnet_name_tag'])
        resultIds['subnets'] = created_subnet
        # close the connection
        self.conn.close()
        return resultIds
        
    # TODO: procedure to delete given VPC
    def deleteVPC(self, vpcSettings=[], dryRun_flag=False):
        if not len(vpcSettings):
            logging.error("VPC Setting is either missing or empty!")
            sys.exit(2)

        for vpc_id in self.conn.get_all_vpcs():
            vpc_id_str = str(vpc_id).split(':', 1)[1]

            # delete the subnets
            attached_subnets = self.conn.get_all_subnets(filters={"vpcId": vpc_id_str})
            if len(attached_subnets):
                for s_id in attached_subnets:
                    s_id_str = str(s_id).split(':', 1)[1]
                    self.conn.delete_subnet(s_id_str)

            self.conn.delete_vpc(vpc_id_str, dry_run=dryRun_flag)

            self.conn.close()

    # TODO: Update action
    def updateVPC(self, vpcSettings=[], dryRun_flag=False):
        logging.warning("This feature is under development")
        pass