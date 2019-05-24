#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script will list the compartment names and IDs in a OCI tenant using OCI CLI
# It will also list all subcompartments
# Note: OCI tenant given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Last update   : May 24, 2019
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed and OCI config file configured with profiles
# --------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 OCI_PROFILE

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

# -------- main

OCI_CONFIG_FILE=~/.oci/config

if [ $# -ne 1 ]; then usage; fi

PROFILE=$1

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 2; fi

# -- list compartments and all sub-compartments (excluding root compartment)
oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --output table --query "data [*].{Name:name, OCID:id, Status:\"lifecycle-state\"}"
