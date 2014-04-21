__author__ = 'shekarnh'

import json
import subprocess
import yaml
import logging


class GetTags(object):
    def __init__(self, tagFile):
        self.outTagFile = tagFile

    def updateTagFile(self):
        # requires awscli installed and credentials configured
        command = 'aws ec2 describe-tags'
        all_tags = subprocess.check_output(command.split())
        all_tags_json = json.loads(all_tags)
        with open(self.outTagFile, 'w') as outFile:
            logging.info("Updating Tags File")
            yaml.safe_dump(all_tags_json, outFile)

    def getResourceID(self, resource_value):
        with open(self.outTagFile, 'r') as tagFile:
            all_tags = yaml.load(tagFile)

        tags = all_tags['Tags']
        for resource in tags:
            if str(resource['Value']) == str(resource_value):
                return str(resource['ResourceId'])