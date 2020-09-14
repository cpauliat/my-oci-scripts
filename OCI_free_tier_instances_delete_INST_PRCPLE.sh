#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script looks for free tier compute instances in an OCI tenant (in home region) and delete them if found
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : jq (JSON parser) installed, OCI CLI 2.6.11+ installed 
#
# THIS SCRIPT MUST BE EXECUTED FROM AN OCI COMPUTE INSTANCE WITH INSTANCE PRINCIPAL PERMISSIONS
#
# Versions
#    2020-09-09: Initial Version
# --------------------------------------------------------------------------------------------------------------

# -------- functions

usage()
{
cat << EOF
Usage: $0 [--confirm]

Notes: 
- If --confirm is provided, found compute instances are deleted, otherwise only listed.

EOF
  exit 1
}

# -- Get the tenancy OCID
get_tenancy_ocid()
{
  oci iam compartment list --query 'data[].{id:"compartment-id"}' | jq -r '.[] | .id' | uniq
}

# -- Get the home region 
get_home_region()
{
  oci iam region-subscription list --query "data[].{home:\"is-home-region\",name:\"region-name\"}" | jq -r '.[] |  select(.home == true) | .name'
}

# -- Get list of compartment IDs for active compartments (excluding root)
get_comp_ids()
{
  oci iam compartment list --compartment-id-in-subtree true --all --query "data [?\"lifecycle-state\" == 'ACTIVE']" 2>/dev/null| egrep "^ *\"id"|awk -F'"' '{ print $4 }'
}

cleanup()
{
  rm -f $TMP_FILE
}

trap_ctrl_c()
{
  echo
  echo -e "SCRIPT INTERRUPTED BY USER !"
  echo

  cleanup
  echo "`date '+%Y/%m/%d %H:%M'`: END"
  exit 99
}

# -- look for free compute instances in given compartment
look_for_free_instances()
{
  local lcompid=$1
  
  #echo "DEBUG: comp $lcompid"

  oci compute instance list -c $lcompid --region $HOME_REGION --all \
       --query "data [?"shape" == 'VM.Standard.E2.1.Micro' && \"lifecycle-state\" != 'TERMINATED'].{InstanceOCID:id}" 2>/dev/null | jq -r '.[].InstanceOCID' | \
  while read id
  do  
    if [ $CONFIRM == true ]; then 
      echo "`date '+%Y/%m/%d %H:%M'`: TERMINATING free compute instance $id in compartment $lcompid"
      oci compute instance terminate --instance-id $id --force    # this also deletes the boot volume
    else
      echo "`date '+%Y/%m/%d %H:%M'`: FOUND free compute instance $id in compartment $lcompid but not terminated since --confirm not provided"
    fi
  done
}

# -------- main

export OCI_CLI_AUTH="instance_principal"
CONFIRM=false
TMP_FILE=/tmp/tmp_$$

case $# in
0) CONFIRM=false
   ;;
1) if [ "$1" == "--confirm" ]; then CONFIRM=true; else usage; fi
   ;;
*) usage
   ;;
esac

echo "`date '+%Y/%m/%d %H:%M'`: BEGIN"

# -- trap ctrl-c and call trap_ctrl_c()
trap trap_ctrl_c INT

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- get tenancy OCID
TENANCY_OCID=`get_tenancy_ocid`

# -- get home region
HOME_REGION=`get_home_region`

# -- Check in root compartment
look_for_free_instances $TENANCY_OCID 

# -- Check in all other active compartments
CPT_IDS=`get_comp_ids`
for id in $CPT_IDS
do
  look_for_free_instances $id
done

# -- end
cleanup
echo "`date '+%Y/%m/%d %H:%M'`: END"
exit 0