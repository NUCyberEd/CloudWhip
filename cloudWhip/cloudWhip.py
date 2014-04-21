__author__ = 'shekar_n_h'

import yaml
import vpcSetUp
import podSetUp
import getConnection
import argparse
import sys
import logging
import os


def setup_logging(
        default_path=os.path.join(os.path.join(os.path.dirname(__file__), os.pardir), 'logging.yaml'),
        default_level=logging.INFO
):
    """
    Setup logging configuration
    """
    path = default_path
    if os.path.exists(path):
        with open(path, 'rt') as logConF:
            logConfig = yaml.load(logConF.read())
        logging.config.dictConfig(logConfig)
    else:
        logging.basicConfig(level=default_level)


def setUpVPC(action, account_settings, vpc_settings, dryrun_flag):

    getConn = getConnection.GetConnection(account_settings)
    vpc_conn = getConn.vpc_connect()

    vpc_setup = vpcSetUp.VpcSetUp(vpc_conn)
    if action == "CREATE":
        vpc_setup.createVPC(vpc_settings, dryrun_flag)
    elif action == "UPDATE":
        pass
    elif action == "DELETE":
        vpc_setup.deleteVPC(vpc_settings, dryrun_flag)

    # close connections
    vpc_conn.close()


def setUpPOD(action, account_settings, pod_settings, pod_list, dryrun_flag):
    getConn = getConnection.GetConnection(account_settings)
    ec2_conn = getConn.ec2_connect()

    pod_setup = podSetUp.PodSetUp(ec2_conn)
    if action == "CREATE":
        pod_setup.createPOD(pod_settings, pod_list, dryrun_flag)
    elif action == "UPDATE":
        pass
    elif action == "DELETE":
        pass

    # close connections
    ec2_conn.close()


def main():
    # setup logging
    setup_logging()
    # list the names of the pod to be created [default everything in the settings file is created]
    usage_msg = "%prog <component> <action> [parameters]"

    parser = argparse.ArgumentParser(description=usage_msg)
    component_list = ["VPC", "POD"]
    parser.add_argument('-c', '--component', help='Specifies one of the component from '
                                                  'the config file. One of {0}'.format(component_list), required=True)
    action_type_list = ["CREATE", "UPDATE", "DELETE"]
    parser.add_argument('-a', '--action', help='Specifies the action to be performed. '
                                               'One of {0}'.format(action_type_list), required=True)

    parser.add_argument('-s', '--setting', help='Specifies the absolute path to the settings file',
                        default='../settings.cfg', required=False)

    #TODO: Add dryrun flag parameter and pod to use
    dryRun = False
    pod_to_use = []     # default all pods in the config file are used

    args = vars(parser.parse_args())

    # validate the args
    if len(args) == 0:
        parser.print_help()
        sys.exit(2)

    sel_component = str(args['component']).upper()
    sel_action = str(args['action']).upper()

    if sel_component not in component_list:
        logging.error("Invalid component. Allowed components are: %s", component_list)
        sys.exit(2)
    if sel_action not in action_type_list:
        logging.error("Invalid action. Allowed actions are: %s", action_type_list)
        sys.exit(2)

    #TODO: Use account settings from Boto config file
    # read the configuration file
    config_stream = open(args['setting'])
    settings = yaml.load(config_stream)
    aws_account_settings = settings['ACCOUNT']
    pod_list_settings = settings['POD']
    vpc_setting = settings['VPC']

    # perform requested action on the component
    if sel_component == "VPC":
        setUpVPC(sel_action, aws_account_settings, vpc_setting, dryRun)
    elif sel_component == "POD":
        setUpPOD(sel_action, aws_account_settings, pod_list_settings, pod_to_use, dryRun)


if __name__ == "__main__":
    main()
