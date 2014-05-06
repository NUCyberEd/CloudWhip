# CloudWhip

CloudWhip is a provisioning tool to conduct Cyber security labs on Amazon Cloud Services. Using CloudWhip course instructors can easily deploy and manage lab environments using a single configuration file.

## Setup
Copy the setting.cfg.template as setting.cfg and update your AWS account information in its respective fields. Fill the respective VPC and POD component fields according to your lab requirements.

## Usage
```
python cloudWhip.py -c <component> -a <action> [options]
```

## Available Features
* Create VPC, Subnets
* Delete VPC, Subnets
* Run Instance

Try help command to list all available arguments

```
python cloudWhip.py -h
```

### Output:
```
usage: cloudWhip.py [-h] -c COMPONENT -a ACTION [-p PODLIST] [-s SETTING]
                    [-d DRYRUN]

%prog -c <component> -a <action> [options]

optional arguments:
  -h, --help            show this help message and exit
  -c COMPONENT, --component COMPONENT
                        Specifies one of the component from the config file.
                        One of ['VPC', 'POD']
  -a ACTION, --action ACTION
                        Specifies the action to be performed. One of
                        ['CREATE', 'UPDATE', 'DELETE']
  -p PODLIST, --podlist PODLIST
                        Specifies the pod list upon which the action is
                        performed. Defaults to all entries found in the config
                        file
  -s SETTING, --setting SETTING
                        Specifies the absolute path to the settings file
  -d DRYRUN, --dryrun DRYRUN
                        Specifies boolean value for dryrun flag. Default set
                        to False
```

## TODO List
* Quick Start Guide
* Stop and Terminate Instances.
* Update action for VPC, Subnets, Instances.
* AWS Account information from boto config file.
* Applying Route Tables
* Applying Security groups
* Delete specific VPC, Subnet, Instance.