#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script looks for compute instances with a specific tag value and start or stop them
# You can use it to automatically stop some instances during non working hours
#     and start them again at the beginning of working hours 
# This script can be executed by an external scheduler (cron table on Linux for instance)
# This script looks in all compartments in a OCI tenant in a region using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed, OCI config file configured with profiles and jq JSON parser
#
# Versions
#    2019-10-10: Initial Version
# --------------------------------------------------------------------------------------------------------------

# ---------- Tag names, key and value to look for
# Instances tagged using this will be stopped/started.
# Update these to match your tags.
# IMPORTANT: also update command (look for WORKAROUND)
TAG_NS="osc"
TAG_KEY="stop_non_working_hours"
TAG_VALUE="on"

# ---------- Functions
usage()
{
cat << EOF
Usage: $0 OCI_PROFILE start|stop [--confirm]

notes: 
- OCI_PROFILE must exist in ~/.oci/config file (see example below)
- If --confirm is not provided, the instances to stop are listed but not actually stopped

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

  CHANGED_FLAG=${TMP_FILE}_changed 
  rm -f $CHANGED_FLAG

  ${OCI} --profile $PROFILE compute instance list -c $lcompid --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id, Status:\"lifecycle-state\"}" > $TMP_FILE
  cat $TMP_FILE

  # if no instance found in this compartment (TMP_FILE empty), exit the function
  if [ ! -s $TMP_FILE ]; then rm -f $TMP_FILE; return; fi 

  cat $TMP_FILE | sed '1,3d;$d' | while read s1 inst_name s2 inst_id s3 inst_status s4
  do
    if ( [ "$inst_status" == "STOPPED" ] && [ "$ACTION" == "start" ] ) || ( [ "$inst_status" == "RUNNING" ] && [ "$ACTION" == "stop" ] )
    then 
      # WORKAROUND: cannot use variable, hardcode TAG_NS and TAG_KEY
      ltag_value=`${OCI} --profile $PROFILE compute instance get --instance-id $inst_id | jq -r '.[]."defined-tags"."osc"."stop_non_working_hours"' 2>/dev/null`
      if [ "$ltag_value" == "$TAG_VALUE" ]
      then 
        if [ $CONFIRM == true ]
        then
          case $ACTION in
            "start") echo "--> STARTING instance $inst_name ($inst_id) because of TAG VALUE"
                     ${OCI} --profile $PROFILE compute instance action --instance-id $inst_id --action START >/dev/null 2>&1
                     ;;
            "stop")  echo "--> STOPPING instance $inst_name ($inst_id) because of TAG VALUE"
                     ${OCI} --profile $PROFILE compute instance action --instance-id $inst_id --action SOFTSTOP >/dev/null 2>&1
                     ;;
          esac
          touch $CHANGED_FLAG
        else
          case $ACTION in
            "start")  echo "--> Instance $inst_name ($inst_id) SHOULD BE STARTED because of TAG VALUE --> re-run script with --confirm to actually start instances"  ;;
            "stop")   echo "--> Instance $inst_name ($inst_id) SHOULD BE STOPPED because of TAG VALUE --> re-run script with --confirm to actually stop instances"  ;;
          esac
        fi
      fi
    fi
  done

  if [ -f $CHANGED_FLAG ]
  then
    ${OCI} --profile $PROFILE compute instance list -c $lcompid --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id, Status:\"lifecycle-state\"}" 
    rm -f $CHANGED_FLAG
  fi
  
  rm -f $TMP_FILE
}

# -------- main

OCI_CONFIG_FILE=~/.oci/config
OCI=$HOME/bin/oci

CONFIRM=false

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

TMP_FILE=tmp_$$

echo "BEGIN SCRIPT: `date`"

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 2; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- list instances in the root compartment
echo
echo "Compartment root, OCID=$TENANCYOCID"
process_compartment $TENANCYOCID 

# -- list instances compartment by compartment (excluding root compartment but including all subcompartments). Only ACTIVE compartments
${OCI} --profile $PROFILE iam compartment list -c $TENANCYOCID --compartment-id-in-subtree true --all --query "data [?\"lifecycle-state\" == 'ACTIVE']" 2>/dev/null| egrep "^ *\"name|^ *\"id"|awk -F'"' '{ print $4 }' | while read compid
do
  read compname
  echo
  echo "Compartment $compname, OCID=$compid"
  process_compartment $compid
done

echo "END SCRIPT: `date`"

rm -f $TMP_FILE
exit 0