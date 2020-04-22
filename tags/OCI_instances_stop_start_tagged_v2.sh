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
Usage: $0 [-q] [-a] OCI_PROFILE start|stop [--confirm]

Notes: 
- If -q is provided, output is minimal (quiet mode): only stopped/started instances are displayed.
- If -a is provided, the script processes all active regions instead of singe region provided in profile
- If --confirm is not provided, the instances to stop (or start) are listed but not actually stopped (or started)
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

  CHANGED_FLAG=${TMP_FILE}_changed 
  rm -f $CHANGED_FLAG

  oci --profile $PROFILE compute instance list -c $lcompid --region $lregion --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id, Status:\"lifecycle-state\"}" > $TMP_FILE
  if [ $QUIET_MODE == false ]; then cat $TMP_FILE; fi
  
  # if no instance found in this compartment (TMP_FILE empty), exit the function
  if [ ! -s $TMP_FILE ]; then rm -f $TMP_FILE; return; fi 

  cat $TMP_FILE | sed '1,3d;$d' | sed -e 's#^.*ocid1.instance#ocid1.instance#' -e 's# .*$##' | while read inst_id
  do
    inst_status=`oci --profile $PROFILE compute instance get --region $lregion --instance-id $inst_id | jq -r '.[]."lifecycle-state"' 2>/dev/null`
    if ( [ "$inst_status" == "STOPPED" ] && [ "$ACTION" == "start" ] ) || ( [ "$inst_status" == "RUNNING" ] && [ "$ACTION" == "stop" ] )
    then 
      inst_name=`oci --profile $PROFILE compute instance get --region $lregion --instance-id $inst_id | jq -r '.[]."display-name"' 2>/dev/null`
      ltag_value=`oci --profile $PROFILE compute instance get --region $lregion --instance-id $inst_id | jq -r '.[]."defined-tags".'\"$TAG_NS\"'.'\"$TAG_KEY\"'' 2>/dev/null`
      if [ "$ltag_value" == "$CURRENT_UTC_TIME" ]
      then 
        if [ $QUIET_MODE == true ]; then printf "region $lregion, cpt $lcompname: "; else printf " --> "; fi             
        if [ $CONFIRM == true ]
        then
          case $ACTION in
            "start") echo "`date '+%Y/%m/%d %H:%M'`: STARTING instance $inst_name ($inst_id)"
                     oci --profile $PROFILE compute instance action --region $lregion --instance-id $inst_id --action START >/dev/null 2>&1
                     ;;
            "stop")  echo "`date '+%Y/%m/%d %H:%M'`: STOPPING instance $inst_name ($inst_id)"
                     oci --profile $PROFILE compute instance action --region $lregion --instance-id $inst_id --action SOFTSTOP >/dev/null 2>&1
                     ;;
          esac
          touch $CHANGED_FLAG
        else
          case $ACTION in
            "start")  echo "Instance $inst_name ($inst_id) SHOULD BE STARTED --> re-run script with --confirm to actually start instances"  ;;
            "stop")   echo "Instance $inst_name ($inst_id) SHOULD BE STOPPED --> re-run script with --confirm to actually stop instances"  ;;
          esac
        fi
      fi
    fi
  done

  if [ -f $CHANGED_FLAG ]
  then
    rm -f $CHANGED_FLAG
    if [ $QUIET_MODE == false ]; then 
      oci --profile $PROFILE compute instance list -c $lcompid --region $lregion --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id, Status:\"lifecycle-state\"}" 
    fi
  fi
  
  rm -f $TMP_FILE
}

# -- Get the current region from the profile
get_region_from_profile()
{
  egrep "^\[|^region" ${OCI_CONFIG_FILE} | fgrep -A 1 "[${PROFILE}]" |grep "^region" > $TMP_FILE 2>&1
  if [ $? -ne 0 ]; then echo "ERROR: region not found in OCI config file $OCI_CONFIG_FILE for profile $PROFILE !"; cleanup; exit 5; fi
  awk -F'=' '{ print $2 }' $TMP_FILE | sed 's# ##g'
}

# -- Get the list of all active regions
get_all_active_regions()
{
  oci --profile $PROFILE iam region-subscription list --query "data [].{Region:\"region-name\"}" |jq -r '.[].Region'
}

# -------- main

OCI_CONFIG_FILE=~/.oci/config
OCI=$HOME/bin/oci

ALL_REGIONS=false
CONFIRM=false
QUIET_MODE=false

if [ "$1" == "-q" ]; then QUIET_MODE=true; shift; fi
if [ "$1" == "-a" ]; then ALL_REGIONS=true; shift; fi

case $# in 
  2) PROFILE=$1
     ACTION=$2
     ;;
  3) PROFILE=$1
     ACTION=$2
     if [ "$3" != "--confirm" ]; then usage; fi
     CONFIRM=true
     ;;
  *) usage 
     ;;
esac

if [ "$PROFILE" == "-h" ] || [ "PROFILE" == "--help" ]; then usage; fi
if [ "$ACTION" != "start" ] && [ "$ACTION" != "stop" ]; then usage; fi

TMP_FILE=/tmp/tmp_$$

LABEL=$$

echo "`date '+%Y/%m/%d %H:%M'`: BEGIN SCRIPT LABEL=$LABEL action $ACTION"

# -- Get current time in UTC timezone in format "HH:00 UTC"
# -- This will be compared to tag values
CURRENT_UTC_TIME=`TZ=UTC date '+%H:00_UTC'`

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- set the tag key according to action
case $ACTION in
  "start") TAG_KEY=$TAG_KEY_START ;;
  "stop")  TAG_KEY=$TAG_KEY_STOP  ;;
esac

# -- set the list of regions
if [ $ALL_REGIONS == false ]
then
  REGIONS_LIST=`get_region_from_profile`
else
  REGIONS_LIST=`get_all_active_regions`
fi
 
# -- process required regions list
for region in $REGIONS_LIST
do
  if [ $QUIET_MODE == false ]
  then
    echo -e "==================== REGION ${region}"
  fi

  # -- list instances in the root compartment
  if [ $QUIET_MODE == false ]
  then
    echo
    echo "Compartment root, OCID=$TENANCYOCID"
  fi
  process_compartment $TENANCYOCID root $region

  # -- list instances compartment by compartment (excluding root compartment but including all subcompartments). Only ACTIVE compartments
  oci --profile $PROFILE iam compartment list -c $TENANCYOCID --compartment-id-in-subtree true --all --query "data [?\"lifecycle-state\" == 'ACTIVE']" 2>/dev/null| egrep "^ *\"name|^ *\"id"|awk -F'"' '{ print $4 }' | while read compid
  do
    read compname
    if [ $QUIET_MODE == false ]
    then
      echo
      echo "Compartment $compname, OCID=$compid"
    fi
    process_compartment $compid $compname $region
  done
done

echo "`date '+%Y/%m/%d %H:%M'`: END SCRIPT LABEL=$LABEL action $ACTION"

rm -f $TMP_FILE
exit 0