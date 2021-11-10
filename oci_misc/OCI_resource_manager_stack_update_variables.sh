#!/bin/bash

# --------------------------------------------------------------------------------------------------------------------------
# This script updates the variables of an OCI Resource Manager stack using OCI CLI
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# Versions
#    2021-09-10: Initial Version
# --------------------------------------------------------------------------------------------------------------------------

# ---------------- main
OCI_CONFIG_FILE=~/.oci/config

# ---------------- functions
usage()
{
cat << EOF
Usage: $0 OCI_PROFILE stack_ocid config_file.json

How to use this script:
- First, use script OCI_resource_manager_stack_get_config.sh to get current variables of a stack and save output to a file
- Modify the JSON file created to match your needs
- Finally use this file in this script to update the variables of the stack

note: OCI_PROFILE must exist in ~/.oci/config file (see example below)

[EMEAOSCf]
tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
key_file    = /Users/cpauliat/.oci/api_key.pem
region      = eu-frankfurt-1
EOF
  exit 1
}


# ---------------- main

# -- Check usage
if [ $# -ne 3 ]; then usage; fi

PROFILE=$1  
STACK_ID=$2
JSON_FILE=$3

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: profile $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- Check if the file exists
if [ ! -f $JSON_FILE ]; then
    echo "ERROR: file $JSON_FILE does not exist or is not readable !"
    exit 4
fi

# -- update Stack configuration
oci --profile $PROFILE resource-manager stack update --stack-id $STACK_ID --from-json file://$JSON_FILE