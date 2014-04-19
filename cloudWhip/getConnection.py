__author__ = 'shekarnh'

from boto.ec2 import connect_to_region
from boto.vpc import VPCConnection


class GetConnection(object):
    def __init__(self, settings=[]):
        self.setting = settings

    def ec2_connect(self):
        return connect_to_region(self.setting['connect_to_region'],
                                  aws_access_key_id=self.setting['aws_access_key_id'],
                                  aws_secret_access_key=self.setting['aws_secret_access_key'])

    def vpc_connect(self):
        return VPCConnection(aws_access_key_id=self.setting['aws_access_key_id'],
                             aws_secret_access_key=self.setting['aws_secret_access_key'])

    def get_connect_to_region(self):
        return self.setting['connect_to_region']

    def get_aws_access_key_id(self):
        return self.setting['aws_access_key_id']

    def get_secret_access_key(self):
        return self.setting['aws_secret_access_key']
