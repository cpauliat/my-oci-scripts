#!/bin/bash

# --------------------------------------------------------------------------------------------------------------------------
# This script displays the variables of an OCI Resource Manager stack using OCI CLI
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
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
Usage: $0 OCI_PROFILE stack_ocid

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
if [ $# -ne 2 ]; then usage; fi

PROFILE=$1  
STACK_ID=$2

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 3; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: profile $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 4; fi

# -- get Stack configuration
( printf '{ "variables": '
  oci --profile $PROFILE resource-manager stack get --stack-id $STACK_ID | jq '.data.variables'
  echo "}" ) | jq