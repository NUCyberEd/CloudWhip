__author__ = 'shekar_n_h'

import getTags
import os


class PodSetUp(object):
    def __init__(self, ec2Connection):
        self.conn = ec2Connection
        self.getTags = getTags.GetTags(
            os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'all_tags.json')
        )

    # TODO: verify if required field exists [ami_id, count, public_ip]
    def verify_instance_fields(self):
        pass

    def get_pod_settings(self, name=None, pod_items=[]):
        return [p_setting for p_setting in pod_items if p_setting['name'] == name]

    def createPOD(self, podSettings=[], podList=[], dryRun_flag=False):
        pod_list_settings = podSettings

        # update the tags file
        self.getTags.updateTagFile()
        # for each item in podList setup the pods on cloud
        if not len(podList):
            # default select all PODS
            for pod_list in pod_list_settings:
                podList.append(pod_list['name'])
        for pod_item in podList:
            current_pod_setting = self.get_pod_settings(pod_item, pod_list_settings)[0]
            pod_count = int(current_pod_setting['count'])
            print "Creating {0} {1} POD(s)".format(pod_count, pod_item)
            # print '{0} == {1}'.format(pod_item, current_pod_setting)
            inst_settings = current_pod_setting['instance_settings']
            for inst_st in inst_settings:
                associate_subnet_id = self.getTags.getValue(inst_st['associate_subnet'])
                # create instance
                self.conn.run_instances(str(inst_st['ami_id']))
                print associate_subnet_id


    # TODO: Update action