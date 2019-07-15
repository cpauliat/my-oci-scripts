#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script lists all objects (detailed list below) in all compartments in a region or all active regions using OCI CLI
##
# Supported objects:
# - Compute       : compute instances, custom images, boot volumes, boot volumes backups
# - Block Storage : block volumes, block volumes backups, volume groups, volume groups backups
# - Object Storage: buckets
# - File Storage  : file systems, mount targets
# - networking    : VCN, DRG, CPE, IPsec connection, LB, public IPs
# - IAM           : Policies
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
#                 script OCI_objects_list_in_compartment.sh available in PATH
# Versions
#    2019-05-29: Initial Version
#    2019-06-03: Fix error in usage message about -a
#    2019-07-15: Use dirname $0 to find required script
# --------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 [-a] OCI_PROFILE
    or $0 [-a] OCI_PROFILE

    By default, only the objects in the region provided in the profile are listed
    If -a is provided, the objects from all active regions are listed

Examples:
    $0 -a EMEAOSCf
    $0 EMEAOSCf

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

OCI_CONFIG_FILE=~/.oci/config
DIR=`dirname $0`
REQUIRED_SCRIPT=$DIR/OCI_objects_list_in_compartment.sh

# -- Check usage
if [ $# -ne 1 ] && [ $# -ne 2 ]; then usage; fi

case $# in
  1) PROFILE=$1;  ALL_REGIONS=""
     ;;
  2) if [ "$1" != "-a" ]; then usage; fi
     PROFILE=$2;  ALL_REGIONS="-a"
     ;;
esac

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: profile $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- Check if script OCI_objects_list_in_compartment.sh is available
which $REQUIRED_SCRIPT > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: required script $REQUIRED_SCRIPT not found ! If present, make sure to update PATH !"; exit 4; fi

# -- Get the names of active compartments
COMP_LIST=`echo root;oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --query "data [?\"lifecycle-state\" == 'ACTIVE']" |jq '.[].name' | sed 's#"##g'`

# -- for all compartements, list all objects
for comp in $COMP_LIST
do
  $REQUIRED_SCRIPT $ALL_REGIONS $PROFILE $comp
done
