#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script will list the compartment names and IDs in a OCI tenant using OCI CLI
# It will also list all subcompartments
# Note: OCI tenant given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2019-05-24: Initial Version
#    2019-05-31: if -h or --help provided, display the usage message
#    2019-10-02: change default behaviour (does not display deleted compartment)
#                and add option -d to list deleted compartments
#    2020-03-20: check oci exists
# --------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 [-d] OCI_PROFILE

    If -d is provided, deleted compartments are also listed.
    If not, only active compartments are listed.

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
LIST_DELETED=false

if [ $# -ne 1 ] && [ $# -ne 2 ]; then usage; fi

if [ "$1"  == "-h" ] || [ "$1"  == "--help" ]; then usage; fi
if [ "$2"  == "-h" ] || [ "$2"  == "--help" ]; then usage; fi

case $# in 
1) PROFILE=$1
   ;;
2) PROFILE=$2
   if [ "$1" == "-d" ]; then LIST_DELETED=true; else usage; fi
   ;;
esac

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- list compartments and all sub-compartments (excluding root compartment)
if [ $LIST_DELETED == true ]
then
  oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --output table --query "data [*].{Name:name, OCID:id, Status:\"lifecycle-state\"}"
else
  oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --output table --query "data [?\"lifecycle-state\" == 'ACTIVE'].{Name:name, OCID:id}"
fi
