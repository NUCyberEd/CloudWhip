#!/bin/bash

# This is an example script to deploy PODs containing three custom instances (2 Linux and 1 Windows) for Lab 1: Gaining Access to OS & Application.
# Note that the VPC and Subnets are manually created using the AWS VPC Wizard and this script is used only for deploying the instances in their respective subnets.

studentcount=25
counter=0
for j in $( seq 0 1);
do
	for i in $( seq 1 $studentcount); 
	do
		# start Source w/ pub IP
		instance_id=$(aws ec2 run-instances --image-id [YOUR CUSTOM AMI-ID] --count 1 --instance-type m1.small --key-name [YOUR KEY-PAIR NAME] --private-ip-address 172.16.$j.$i'1' --subnet-id [YOUR SUBNET ID] --associate-public-ip-address | grep InstanceId |awk '{print $2 }' | cut -d '"' -f2)
		counter=$((counter+1))
       		# create a name tag
		aws ec2 create-tags --resources $instance_id --tags Key=Name,Value=S$counter’:Source’$j.$i’1’
		
		#start Linux target
		instance_id=$(aws ec2 run-instances --image-id [YOUR CUSTOM AMI-ID] --count 1 --instance-type m1.small --key-name [YOUR KEY-PAIR NAME] --private-ip-address  172.16.$j.$i'2' --subnet-id [YOUR SUBNET ID] | grep InstanceId |awk '{print $2 }' | cut -d '"' -f2)
		#Create a name tag
		aws ec2 create-tags --resources $instance_id --tags Key=Name,Value=S$counter’:Linux.’$j.$i’2’

		#start win2k3
		instance_id=$(aws ec2 run-instances --image-id [YOUR CUSTOM AMI-ID] --count 1 --instance-type m1.small --key-name [YOUR KEY-PAIR NAME] --private-ip-address 172.16.$j.$i'3' --subnet-id [YOUR SUBNET ID] | grep InstanceId |awk '{print $2 }' | cut -d '"' -f2)
		#Create a name tag
		aws ec2 create-tags --resources $instance_id --tags Key=Name,Value=S1:Win.$j.$i’3’



	done

done

