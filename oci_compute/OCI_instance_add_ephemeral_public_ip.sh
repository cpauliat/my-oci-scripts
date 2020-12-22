#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script adds a new ephemeral public IP to a compute instance using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2020-01-27: Initial Version
#    2020-03-20: check oci exists
# --------------------------------------------------------------------------------------------------------------

# -------- functions

usage()
{
cat << EOF
Usage: $0 OCI_PROFILE INSTANCE_ID

Notes: 
- OCI_PROFILE must exist in ~/.oci/config file (see example below)
- INSTANCE_ID is the OCID of the compute instance

[EMEAOSCf]
tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
key_file    = /Users/cpauliat/.oci/api_key.pem
region      = eu-frankfurt-1
EOF
  exit 1
}

trap_ctrl_c()
{
  echo
  echo -e "${COLOR_BREAK}SCRIPT INTERRUPTED BY USER ! ${COLOR_NORMAL}"
  echo

  exit 99
}

# ---- Colored output or not
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLORED_OUTPUT=true
if [ "$COLORED_OUTPUT" == true ]
then
  COLOR_TITLE0="\033[95m"             # light magenta
  COLOR_TITLE1="\033[91m"             # light red
  COLOR_TITLE2="\033[32m"             # green
  COLOR_COMP="\033[93m"               # light yellow
  COLOR_BREAK="\033[91m"              # light red
  COLOR_NORMAL="\033[39m"
else
  COLOR_TITLE0=""
  COLOR_TITLE1=""
  COLOR_TITLE2=""
  COLOR_COMP=""
  COLOR_BREAK=""
  COLOR_NORMAL=""
fi

# -------- main

OCI_CONFIG_FILE=~/.oci/config
OCI=$HOME/bin/oci

if [ $# -eq 2 ]; then PROFILE=$1; INSTANCE_ID=$2; else usage; fi

# -- trap ctrl-c and call trap_ctrl_c()
trap trap_ctrl_c INT

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- get the ID of the primary VNIC of the instance
echo "# -- get the ID of the primary VNIC of the instance"
VNIC_ID=`$OCI --profile $PROFILE compute instance list-vnics --instance-id $INSTANCE_ID --all --query "data [?\"is-primary\"].{id:id}" |jq -r '.[].id'`

# -- get the ID of the private ID from the VNIC
echo "# -- get the ID of the private ID from the VNIC"
PRIVATE_IP_ID=`$OCI --profile $PROFILE network private-ip list --vnic-id $VNIC_ID --query "data[].id" | jq -r '.[]'`

# -- get the compartment ID of the private IP
echo "# -- get the compartment ID of the private IP"
CPT_ID=`$OCI --profile $PROFILE network private-ip list --vnic-id $VNIC_ID --query 'data[]."compartment-id"' | jq -r '.[]'`

# -- create a new ephemeral public IP 
echo "# -- create a new ephemeral public IP"
$OCI --profile $PROFILE network public-ip create -c $CPT_ID --lifetime EPHEMERAL --private-ip-id $PRIVATE_IP_ID 

exit 0
