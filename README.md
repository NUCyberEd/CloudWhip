# CloudWhip

CloudWhip is a provisioning tool to conduct Cyber security labs on Amazon Cloud Services. Using CloudWhip course instructors can easily deploy and manage lab environments using a single configuration file.

## Setup
Copy the setting.cfg.template as setting.cfg and update your AWS account information in its respective fields. Fill the respective VPC and POD component fields according to you lab requirements.

## Usage
```
python cloudWhip.py -c <component> -a <action> -s [settings]
```
## Available Features
* Create VPC, Subnets
* Delete VPC, Subnets
* Run, Stop, Delete Instance

## TODO List
* Quick Start Guide
* Update action for VPC, Subnets, Instances.
* AWS Account information for boto config file.
* Applying Route Tables
* Applying Security groups
* Add dryrun and pod to use arguments
* Delete specific VPC, Subnet, Instance.