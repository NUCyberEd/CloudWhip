__author__ = 'shekarnh'

"""
Recipe for creating and updating security groups programmatically.

Orginal author: Mike Steder
url: https://gist.github.com/steder/1498451

"""

import collections
import logging
import sys
import getTags
import os
import time


class SecurityGroups(object):

    def __init__(self, ec2Connection):
        self.conn = ec2Connection
        self.logger = logging.getLogger(__name__)
        self.getTags = getTags.GetTags(
            os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'all_tags.yaml'))
        # to define the cluster security group rules and client security group rules.
        self.securityGroupRule = collections.namedtuple("SecurityGroupRule", ["ip_protocol", "from_port",
                                                                              "to_port", "cidr_ip", "src_grp_name"])

    def get_or_create_security_group(self, group_name, description="", vpc_id=None):
        """
        """
        groups = [g for g in self.conn.get_all_security_groups() if g.name == group_name]
        group = groups[0] if groups else None
        if not group:
            self.logger.info("Creating group '%s'...", (group_name,))
            group = self.conn.create_security_group(group_name, description, vpc_id)
            # TODO: Find a better way to verify creation
            time.sleep(3)
            group.add_tag("Name", group_name)
        return group

    def modify_sg(self, group, rule, authorize=False, revoke=False):

        if rule.cidr_ip:
            rule_cidr_ip = rule.cidr_ip
            rule_src_group = None
        else:
            rule_cidr_ip = None
            self.getTags.update_tag_file()
            src_grp_id = self.getTags.get_resource_id(rule.src_grp_name)
            rule_src_group = src_grp_id

        if authorize and not revoke:
            self.logger.info("Authorizing missing rule %s...", (rule,))
            group.authorize(ip_protocol=rule.ip_protocol,
                            from_port=rule.from_port,
                            to_port=rule.to_port,
                            cidr_ip=rule_cidr_ip,
                            src_group=rule_src_group)

        elif not authorize and revoke:
            self.logger.info("Revoking unexpected rule %s...", (rule,))
            group.revoke(ip_protocol=rule.ip_protocol,
                         from_port=rule.from_port,
                         to_port=rule.to_port,
                         cidr_ip=rule_cidr_ip,
                         src_group=rule_src_group)

    def authorize(self, group, rule):
        """Authorize `rule` on `group`."""
        return self.modify_sg(group, rule, authorize=True)

    def revoke(self, group, rule):
        """Revoke `rule` on `group`."""
        return self.modify_sg(group, rule, revoke=True)

    def update_security_group(self, group, expected_rules):
        """
        """
        self.logger.info('Updating group "%s"...', group.name)
        self.logger.debug("Expected Rules:")
        self.logger.debug(expected_rules)


        current_rules = []
        for rule in group.rules:
            if not rule.grants[0].cidr_ip:
                current_rule = self.securityGroupRule(rule.ip_protocol,
                                  rule.from_port,
                                  rule.to_port,
                                  None,
                                  rule.grants[0].name)
            else:
                current_rule = self.securityGroupRule(rule.ip_protocol,
                                  rule.from_port,
                                  rule.to_port,
                                  rule.grants[0].cidr_ip,
                                  None)

            if current_rule not in expected_rules:
                self.revoke(group, current_rule)
            else:
                current_rules.append(current_rule)

        self.logger.debug("Current Rules:")
        self.logger.debug(current_rules)

        for rule in expected_rules:
            if rule not in current_rules:
                self.authorize(group, rule)

    def create_security_groups(self, sgName, sgDescription, vpcId, sgRules):
        """
        attempts to be idempotent:

        if the sg does not exist create it,
        otherwise just check that the security group contains the rules
        we expect it to contain and updates it if it does not.
        """
        group_name = sgName

        rules = []
        for sgRule in sgRules:
            if len(sgRule) == 5:
                rule = self.securityGroupRule(sgRule[0], sgRule[1], sgRule[2], sgRule[3], sgRule[4])
                rules.append(rule)
            else:
                self.logger.error("Expected 5 fields but found %d fields.", len(sgRule))
                sys.exit(2)

        group = self.get_or_create_security_group(group_name, sgDescription, vpcId)
        self.update_security_group(group, rules)