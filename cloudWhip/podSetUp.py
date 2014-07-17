__author__ = 'shekar_n_h'

import getTags
import os
import logging
import sys
import time
import subprocess
from boto import ec2
import netIps


class PodSetUp(object):
    def __init__(self, ec2Connection, vpcConnection):
        self.conn = ec2Connection
        self.vpcConn = vpcConnection
        self.getTags = getTags.GetTags(
            os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'all_tags.yaml'))
        self.ipAddrBlks = netIps.NetIps()
        self.logger = logging.getLogger(__name__)

    # TODO: verify if required field exists [ami_id, count, public_ip]
    def verify_instance_fields(self):
        pass

    def get_pod_settings(self, name=None, pod_items=[]):
        pod_settings = {}
        for p_setting in pod_items:
            if p_setting['name'] == name:
                pod_settings = p_setting
                break
        if not len(pod_settings):
            self.logger.error("'{0}' POD Name not found in the config file".format(name))
            sys.exit(2)
        return pod_settings

    # TODO: Idempotence
    def create_pod(self, podSettings=[], podList=[], dryRun_flag=False):
        pod_list_settings = podSettings

        # update the tags file
        self.getTags.update_tag_file()
        # for each item in podList setup the pods on cloud
        if not len(podList):
            # default select all PODS
            for pod_list in pod_list_settings:
                podList.append(pod_list['name'])
        for pod_item in podList:
            current_pod_setting = self.get_pod_settings(pod_item, pod_list_settings)
            pod_count = int(current_pod_setting['count'])
            self.logger.info("Creating %d %s POD(s)", pod_count, pod_item)
            current_pod_subnet = current_pod_setting['associate_subnet_group_name']
            current_all_ids = self.getTags.get_resource_id(current_pod_subnet)
            current_pod_subnet_ids = []
            for current_id in current_all_ids:
                if current_id.startswith('subnet'):
                    current_pod_subnet_ids.append(current_id)

            # get cidr blocks for each subnet
            current_pod_subent_cidr = {}    # Dict containing subnet_id: cidr_block
            describe_subnets = self.vpcConn.get_all_subnets(subnet_ids=current_pod_subnet_ids)
            for subnet_id in describe_subnets:
                current_pod_subent_cidr[subnet_id.id] = subnet_id.cidr_block

            # prepare list of available ips in the subnet
            current_pod_subnet_reserved_instance_ip = {}    # Dict containing subnet_id: reserved_private_ips
            current_pod_subnet_avail_hosts = {}     # Dict containing subnet_id: list of avail hosts
            subnet_available_hosts = []

            for subnet_id, subnet_cidr in current_pod_subent_cidr.iteritems():
                subnet_available_hosts = self.ipAddrBlks.get_subnet_hosts(subnet_cidr)
                reserved_instances_private_ip = []
                subnet_reservations = self.conn.get_all_instances(filters={'subnet-id': subnet_id})
                subnet_instances = [i for r in subnet_reservations for i in r.instances]
                for inst in subnet_instances:
                    private_ip = inst.private_ip_address
                    reserved_instances_private_ip.append(private_ip)
                    if private_ip in subnet_available_hosts:
                        subnet_available_hosts.remove(private_ip)
                current_pod_subnet_reserved_instance_ip[subnet_id] = reserved_instances_private_ip
                current_pod_subnet_avail_hosts[subnet_id] = subnet_available_hosts

            inst_settings = current_pod_setting['instance_settings']

            for subnet_id, subnet_cidr in current_pod_subent_cidr.iteritems():
                for inst_st in inst_settings:
                    current_inst_private_ip = None
                    inst_private_ip_wc = inst_st['private_ip']
                    inst_private_ip_wc_space = self.ipAddrBlks.generate_private_ip_space(subnet_cidr, inst_private_ip_wc)
                    for cnt in xrange(0, pod_count):
                        # assign the current instance private ip address
                        if inst_private_ip_wc_space[0] in current_pod_subnet_avail_hosts[subnet_id]:
                            current_inst_private_ip = inst_private_ip_wc_space[0]
                            inst_private_ip_wc_space.remove(current_inst_private_ip)
                            current_pod_subnet_avail_hosts[subnet_id].remove(current_inst_private_ip)
                        else:
                            self.logger.error("No available Private IPs within the mentioned wild card bits")
                            sys.exit(2)
                        # check again to be safe
                        if current_inst_private_ip is not None:
                            if inst_st['public_ip']:
                                # creating interfaces is a hack to assign public ip for instances in VPCs
                                pub_interface = ec2.networkinterface.NetworkInterfaceSpecification(
                                    subnet_id=subnet_id,
                                    associate_public_ip_address=True,
                                    private_ip_address=current_inst_private_ip)
                                pub_interfaces = ec2.networkinterface.NetworkInterfaceCollection(pub_interface)
                                reservation = self.conn.run_instances(str(inst_st['ami_id']),
                                                                      key_name=inst_st['key_name'],
                                                                      network_interfaces=pub_interfaces)
                            else:
                                reservation = self.conn.run_instances(str(inst_st['ami_id']),
                                                                      key_name=inst_st['key_name'],
                                                                      subnet_id=subnet_id,
                                                                      private_ip_address=current_inst_private_ip)
                            instance = reservation.instances[0]

                            # wait for instance to run
                            self.logger.info("Instance %s launched but waiting for it to run", inst_st['inst_name'])
                            while instance.state != 'running':
                                sys.stdout.write('. ')
                                sys.stdout.flush()
                                time.sleep(5)
                                instance.update()
                            sys.stdout.write('\n')
                            sys.stdout.flush()
                            self.logger.info("Instance %s launched and running", inst_st['inst_name'])

                            # change security group if mentioned
                            associate_sg_id = []
                            associate_sg_name = inst_st['associate_sg']
                            if associate_sg_name is not None:
                                self.logger.info("Changing Security Group to {0}".format(associate_sg_name))
                                associate_sg_id = self.getTags.get_resource_id(associate_sg_name)
                                instance.modify_attribute('groupSet', associate_sg_id)

                            # add tag
                            self.logger.debug('Adding Name tag')
                            current_inst_name_tag = "{0}:{1}:{2}".format(self.getTags.get_resource_value(subnet_id),
                                                                         inst_st['inst_name'],
                                                                         cnt)
                            instance.add_tag("Name", current_inst_name_tag)

    def delete_pod(self, podSettings=[], podList=[], dryRun_flag=False):
        pod_list_settings = podSettings

        # update the tags file
        self.getTags.update_tag_file()
        # for each item in podList setup the pods on cloud
        if not len(podList):
            # default select all PODS
            for pod_list in pod_list_settings:
                podList.append(pod_list['name'])
        for pod_item in podList:
            current_pod_setting = self.get_pod_settings(pod_item, pod_list_settings)
            pod_count = int(current_pod_setting['count'])
            self.logger.info("Deleting {0} {1} POD(s)".format(pod_count, pod_item))

            # get all subnet ids from the associate subnet group
            current_pod_subnet = current_pod_setting['associate_subnet_group_name']
            current_all_ids = self.getTags.get_resource_id(current_pod_subnet)
            current_pod_subnet_ids = []
            for current_id in current_all_ids:
                if current_id.startswith('subnet'):
                    current_pod_subnet_ids.append(current_id)

            for subnet_id in current_pod_subnet_ids:
                subnet_reservations = self.conn.get_all_instances(filters={'subnet-id': subnet_id})
                subnet_instances = [i for r in subnet_reservations for i in r.instances]
                instance_id_list = []
                for inst in subnet_instances:
                    instance_id_list.append(inst.id)
                # delete all instances
                self.logger.warning("Terminating {0} Instances from subnet id: {1}".format(len(instance_id_list), subnet_id))
                self.conn.terminate_instances(instance_ids=instance_id_list)

    # TODO: Update action
    def update_pod(self, podSettings=[], podList=[], dryRun_flag=False):
        self.logger.warning("This feature is under development.")
        pod_list_settings = podSettings

        # TODO: Uncomment update tags
        # update the tags file
        # self.getTags.update_tag_file()
        # for each item in podList setup the pods on cloud
        if not len(podList):
            # default select all PODS
            for pod_list in pod_list_settings:
                podList.append(pod_list['name'])
        for pod_item in podList:
            current_pod_setting = self.get_pod_settings(pod_item, pod_list_settings)
            pod_count = int(current_pod_setting['count'])
            self.logger.info("Updating %d %s POD(s)", pod_count, pod_item)
            inst_settings = current_pod_setting['instance_settings']
            # get all subnet ids from the associate subnet group
            current_pod_subnet = current_pod_setting['associate_subnet_group_name']
            current_all_ids = self.getTags.get_resource_id(current_pod_subnet)
            current_pod_subnet_ids = []
            for current_id in current_all_ids:
                if current_id.startswith('subnet'):
                    current_pod_subnet_ids.append(current_id)

            for subnet_id in current_pod_subnet_ids:
                pass