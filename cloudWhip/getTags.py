__author__ = 'shekarnh'

import json
import subprocess
import yaml
import logging
import sys


class GetTags(object):
    def __init__(self, tagFile):
        self.outTagFile = tagFile
        self.logger = logging.getLogger(__name__)

    def update_tag_file(self):
        # requires awscli installed and credentials configured
        command = 'aws ec2 describe-tags'
        all_tags = subprocess.check_output(command.split())
        all_tags_json = json.loads(all_tags)
        with open(self.outTagFile, 'w') as outFile:
            self.logger.info("Updating Tags File")
            yaml.safe_dump(all_tags_json, outFile)

    def get_resource_id(self, resource_value):
        with open(self.outTagFile, 'r') as tagFile:
            all_tags = yaml.load(tagFile)

        tags = all_tags['Tags']
        resource_id_list = []
        for resource in tags:
            if str(resource['Value']).startswith(str(resource_value)):
                resource_id_list.append(str(resource['ResourceId']))

        return resource_id_list

        self.logger.error("{0} resource name not found in the tag file".format(resource_value))
        sys.exit(2)

    def get_resource_value(self, resource_id):
        with open(self.outTagFile, 'r') as tagFile:
            all_tags = yaml.load(tagFile)

        tags = all_tags['Tags']
        resource_value = None
        for resource in tags:
            if str(resource['ResourceId']) in str(resource_id).lower():
                resource_value = resource['Value']
                return resource_value

        self.logger.error("{0} resource id not found in the tag file".format(resource_id))
        sys.exit(2)