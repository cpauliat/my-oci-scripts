#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script looks for compute instances with a specific tag key and stop (or start) them if the 
#     tag value for the tag key matches the current time.
# You can use it to automatically stop some compute instances during non working hours
#     and start them again at the beginning of working hours to save cloud credits
# This script needs to be executed every hour during working days by an external scheduler 
#     (cron table on Linux for example)
# You can add the 2 tag keys to the default tags for root compartment so that every new compute 
#     instance get those 2 tag keys with default value ("off" or a specific UTC time)
#
# This script looks in all compartments in a OCI tenant in a region using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed, OCI config file configured with profiles and jq JSON parser
#
# Versions
#    2019-10-10: Initial Version
#    2019-10-11: Add support for all active regions
#    2019-10-14: Add quiet mode option
#    2020-03-20: change location of temporary files to /tmp + check oci exists
#    2020-03-23: use TAG_NS and TAG_KEY in process_compartment function instead of hardcoded values
#    2020-04-15: Enhance features to enable automatic shutdown/start at a given UTC time using 2 tag keys
#                This script now needs to be run every hour using crontab or another scheduler
#    2020-04-22: use single instance of script for both stop and start actions to minimize number of API calls
#                and optimize/simplify script
# --------------------------------------------------------------------------------------------------------------

# ---------- Tag names, key and value to look for
# Instances tagged using this will be stopped/started.
# Update these to match your tags.
TAG_NS="osc"
TAG_KEY_STOP="automatic_shutdown"
TAG_KEY_START="automatic_startup"

# ---------- Functions
usage()
{
cat << EOF
Usage: $0 [-a] [--confirm_stop] [--confirm_start] OCI_PROFILE

Notes: 
- If -a is provided, the script processes all active regions instead of singe region provided in profile
- If --confirm_stop  is not provided, the instances to stop are listed but not actually stopped
- If --confirm_start is not provided, the instances to start are listed but not actually started
- OCI_PROFILE must exist in ~/.oci/config file (see example below)

[EMEAOSCf]
tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
key_file    = /Users/cpauliat/.oci/api_key.pem
region      = eu-frankfurt-1
EOF
  exit 1
}

process_compartment()
{
  local lcompid=$1
  local lcompname=$2
  local lregion=$3
 
  # find compute instances in this compartment
  oci --profile $PROFILE compute instance list -c $lcompid --region $lregion | jq -r '.data[].id' > $TMP_FILE
  
  # if no instance found in this compartment (TMP_FILE empty), exit the function
  if [ ! -s $TMP_FILE ]; then rm -f $TMP_FILE; return; fi 

  # otherwise, we look at each compute instance
  for inst_id in `cat $TMP_FILE`
  do
    echo "   DEBUG: inst=$inst_id"
    oci --profile $PROFILE compute instance get --region $lregion --instance-id $inst_id > ${TMP_FILE}_INST 2>/dev/null
    inst_status=`cat ${TMP_FILE}_INST| jq -r '.[]."lifecycle-state"' 2>/dev/null`
    inst_name=`cat ${TMP_FILE}_INST  | jq -r '.[]."display-name"' 2>/dev/null`
    ltag_value_stop=`cat  ${TMP_FILE}_INST| jq -r '.[]."defined-tags".'\"$TAG_NS\"'.'\"$TAG_KEY_STOP\"''  2>/dev/null`
    ltag_value_start=`cat ${TMP_FILE}_INST| jq -r '.[]."defined-tags".'\"$TAG_NS\"'.'\"$TAG_KEY_START\"'' 2>/dev/null`

    # Is it time to start this instance ?
    if [ "$inst_status" == "STOPPED" ] && [ "$ltag_value_start" == "$CURRENT_UTC_TIME" ]; then
        printf "`date '+%Y/%m/%d %H:%M'`, region $lregion, cpt $lcompname: "
        if [ $CONFIRM_START == true ]; then
            echo "STARTING instance $inst_name ($inst_id)"
            oci --profile $PROFILE compute instance action --region $lregion --instance-id $inst_id --action START >/dev/null 2>&1
        else
            echo "Instance $inst_name ($inst_id) SHOULD BE STARTED --> re-run script with --confirm_start to actually start instances" 
        fi

    # Is it time to stop this instance ?
    elif [ "$inst_status" == "RUNNING" ] && [ "$ltag_value_stop" == "$CURRENT_UTC_TIME" ]; then
        printf "`date '+%Y/%m/%d %H:%M'`, region $lregion, cpt $lcompname: "
        if [ $CONFIRM_STOP == true ]; then
            echo "STOPPING instance $inst_name ($inst_id)"
            oci --profile $PROFILE compute instance action --region $lregion --instance-id $inst_id --action SOFTSTOP >/dev/null 2>&1
        else
            echo "Instance $inst_name ($inst_id) SHOULD BE STOPPED --> re-run script with --confirm_stop to actually stop instances"
        fi
    fi
    rm -f ${TMP_FILE}_INST
  done
  rm -f $TMP_FILE
}

# -- Exit script with return code
my_exit()
{
  CR=$1   # return code
  echo "`date '+%Y/%m/%d %H:%M'`: END SCRIPT PID=$PID"
  exit $CR
}

# -- Get the current region from the profile
get_region_from_profile()
{
  egrep "^\[|^region" ${OCI_CONFIG_FILE} | fgrep -A 1 "[${PROFILE}]" |grep "^region" > $TMP_FILE 2>&1
  if [ $? -ne 0 ]; then echo "ERROR: region not found in OCI config file $OCI_CONFIG_FILE for profile $PROFILE !"; cleanup; my_exit 5; fi
  awk -F'=' '{ print $2 }' $TMP_FILE | sed 's# ##g'
}

# -- Get the list of all active regions
get_all_active_regions()
{
  oci --profile $PROFILE iam region-subscription list --query "data [].{Region:\"region-name\"}" |jq -r '.[].Region'
}

# -------- main

# -- variables
OCI_CONFIG_FILE=~/.oci/config
ALL_REGIONS=false
CONFIRM_STOP=false
CONFIRM_START=false
TMP_FILE=/tmp/tmp_$$
PID=$$
LOCK_FILE=/tmp/`basename $0`.lock

# -- args parsing
if [ "$1" == "-a" ]; then ALL_REGIONS=true; shift; fi
if [ "$1" == "--confirm_stop" ]; then CONFIRM_STOP=true; shift; fi
if [ "$1" == "--confirm_start" ]; then CONFIRM_START=true; shift; fi

if [ $# -ne 1 ]; then usage; fi
PROFILE=$1

if [ "$PROFILE" == "-h" ] || [ "PROFILE" == "--help" ]; then usage; fi

# -- starting
echo "`date '+%Y/%m/%d %H:%M'`: BEGIN SCRIPT PID=$PID"

# -- Get current time in UTC timezone in format "HH:00 UTC"
# -- This will be compared to tag values
CURRENT_UTC_TIME=`TZ=UTC date '+%H:00_UTC'`

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; my_exit 2; fi

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; my_exit 3; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; my_exit 4; fi

# -- If this script is already running, exit with an error message
if [ -f $LOCK_FILE ]; then
    echo "ERROR: lock file detected, meaning another instance of this script is already running."
    my_exit 99 false
else
    touch $LOCK_FILE
fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- set the list of regions
if [ $ALL_REGIONS == true ]; then
    REGIONS_LIST=`get_all_active_regions`
else
    REGIONS_LIST=`get_region_from_profile`
fi

# -- process required regions list
for region in $REGIONS_LIST
do
  # -- list instances in the root compartment
  process_compartment $TENANCYOCID root $region

  # -- list instances compartment by compartment (excluding root compartment but including all subcompartments). Only ACTIVE compartments
  oci --profile $PROFILE iam compartment list -c $TENANCYOCID --compartment-id-in-subtree true --all --query "data [?\"lifecycle-state\" == 'ACTIVE']" 2>/dev/null| egrep "^ *\"name|^ *\"id"|awk -F'"' '{ print $4 }' | while read compid
  do
    read compname
    process_compartment $compid $compname $region
  done
done

# -- the end
rm -f $TMP_FILE
rm -f $LOCK_FILE
my_exit 0