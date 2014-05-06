__author__ = 'shekar_n_h'

import getTags
import os
import logging
import sys
import time
import subprocess
from boto import ec2


class PodSetUp(object):
    def __init__(self, ec2Connection):
        self.conn = ec2Connection
        self.getTags = getTags.GetTags(
            os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'all_tags.yaml'))
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
            self.logger.error("{0} POD Name not found in the config file".format(name))
            sys.exit(2)
        return pod_settings

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
            inst_settings = current_pod_setting['instance_settings']
            for cnt in xrange(0, pod_count):
                for inst_st in inst_settings:
                    associate_subnet_id = self.getTags.get_resource_id(inst_st['associate_subnet'])
                    if not associate_subnet_id:
                        self.logger.error("Resource Value not found. Check if the Subnet is created and '%s' Name tag exists.", inst_st['associate_subnet'])
                        sys.exit(2)
                    # associate public ip
                    if bool(inst_st['public_ip']) == True:
                        # creating interfaces is a hack to assign public ip for instances in VPCs
                        pub_interface = ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=associate_subnet_id,
                                                                        associate_public_ip_address=True)
                        pub_interfaces = ec2.networkinterface.NetworkInterfaceCollection(pub_interface)
                        reservation = self.conn.run_instances(str(inst_st['ami_id']), key_name=inst_st['key_name'], network_interfaces=pub_interfaces)
                    else:
                        reservation = self.conn.run_instances(str(inst_st['ami_id']), key_name=inst_st['key_name'], subnet_id=associate_subnet_id)
                    instance = reservation.instances[0]
                    # self.logger.debug("Using awscli to launch the instance")
                    # launch_command = 'aws ec2 run-instances --image-id {0} --key-name {1} ' \
                    #                  '--subnet-id {2} --associate-public-ip-address'.format(inst_st['ami_id'], inst_st['key_name'], associate_subnet_id)
                    # instance = subprocess.check_output(launch_command.split())
                    # print instance

                    # wait for instance to run
                    self.logger.info("Instance %s launched but waiting for it to run", inst_st['name'])
                    while instance.state != 'running':
                        sys.stdout.write('. ')
                        sys.stdout.flush()
                        time.sleep(5)
                        instance.update()
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    self.logger.info("Instance %s launched and running", inst_st['name'])

                    # add tag
                    self.logger.debug('Adding Name tag')
                    instance.add_tag("Name", inst_st['name'])

    # TODO: Delete action not complete
    def delete_pod(self, podSettings=[], podList=[], dryRun_flag=False):
        self.logger.warning("This feature is under development. Please delete it from your AWS Console")
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
            self.logger.info("Deleting %d %s POD(s)", pod_count, pod_item)
            inst_settings = current_pod_setting['instance_settings']
            for inst_st in inst_settings:
                associate_subnet_id = self.getTags.get_resource_id(inst_st['associate_subnet'])
                if not associate_subnet_id:
                    self.logger.error("Resource Value not found. Check if the Subnet is created and '%s' Name tag exists.", inst_st['associate_subnet'])
                    sys.exit(2)
                # associate public ip
                if bool(inst_st['public_ip']) == True:
                    # creating interfaces is a hack to assign public ip for instances in VPCs
                    pub_interface = ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=associate_subnet_id,
                                                                    associate_public_ip_address=True)
                    pub_interfaces = ec2.networkinterface.NetworkInterfaceCollection(pub_interface)
                    reservation = self.conn.run_instances(str(inst_st['ami_id']), key_name=inst_st['key_name'], network_interfaces=pub_interfaces)
                else:
                    reservation = self.conn.run_instances(str(inst_st['ami_id']), key_name=inst_st['key_name'], subnet_id=associate_subnet_id)
                instance = reservation.instances[0]
                # self.logger.debug("Using awscli to launch the instance")
                # launch_command = 'aws ec2 run-instances --image-id {0} --key-name {1} ' \
                #                  '--subnet-id {2} --associate-public-ip-address'.format(inst_st['ami_id'], inst_st['key_name'], associate_subnet_id)
                # instance = subprocess.check_output(launch_command.split())
                # print instance

                # wait for instance to run
                self.logger.info("Instance %s launched but waiting for it to run", inst_st['name'])
                while instance.state != 'running':
                    sys.stdout.write('. ')
                    sys.stdout.flush()
                    time.sleep(5)
                    instance.update()
                sys.stdout.write('\n')
                sys.stdout.flush()
                self.logger.info("Instance %s launched and running", inst_st['name'])

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