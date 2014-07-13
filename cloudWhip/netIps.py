__author__ = 'shekarnh'

import itertools
import sys
import logging
from ipaddress import ip_network
import re


class NetIps(object):

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_cidr_blocks(self, input_string):
        ip_block = input_string.split('/')
        if len(ip_block) < 2:
            self.logger.error("Please check if network mask is specified for the subnet cidr block")
            sys.exit(2)
        subnet_mask = int(ip_block[1])
        if not 0 <= subnet_mask <= 32:
            self.logger.error("Subnet mask out of range. Allowed [0-32]")
            sys.exit(2)
        octets = ip_block[0].split('.')
        chunks = [map(int, octet.split('-')) for octet in octets]
        ranges = [range(c[0], c[1] + 1) if len(c) == 2 else c for c in chunks]

        cidr_blck_list = []
        for address in itertools.product(*ranges):
            ip_addr = '.'.join(map(str, address))
            cidr_blck_list.append("{0}/{1}".format(ip_addr, subnet_mask))

        return cidr_blck_list

    def get_subnet_hosts(self, input_string):
        subnet_cidr_ip = list(ip_network(input_string).hosts())
        subnet_cidr_ip_str = []
        for ip_addr in subnet_cidr_ip:
            subnet_cidr_ip_str.append(str(ip_addr))
        return subnet_cidr_ip_str

    def generate_private_ip_space(self, cidrBlock, privateIPWildCard):
        wc_regex = re.compile("\$")
        allowed_hosts = self.get_subnet_hosts(cidrBlock)
        # AWS reserves first four and last ip address in every subnet
        # http://aws.amazon.com/vpc/faqs/
        allowed_hosts = allowed_hosts[4:-1]
        octets = str(privateIPWildCard).split('.')
        available_private_ip_space = []
        wc_index = 0
        wc_octet = None
        for oc in octets:
            if re.match(wc_regex, oc):
                wc_index = octets.index(oc)
                wc_octet = oc
                break
        if wc_octet is not None and wc_octet.find('$') >= 0:
            wc_mask_bits = wc_octet.replace('$', '')
            if wc_octet.startswith('$'):
                for host_ip in allowed_hosts:
                    host_octets = host_ip.split('.')
                    if host_octets[wc_index].endswith(wc_mask_bits):
                        available_private_ip_space.append(host_ip)
        else:
            self.logger.warning("Private IP wild card missing. Using the next available IP")
            available_private_ip_space = allowed_hosts
        return available_private_ip_space