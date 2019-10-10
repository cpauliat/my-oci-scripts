#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script looks for compute instances with a specific tag value and stop them if they are running
# You can use it to automatically stop some instances you don't need during non working hours for example
# It looks in all compartments in a OCI tenant in a region using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Last update   : October 9, 2019
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed, OCI config file configured with profiles and jq JSON parser
# --------------------------------------------------------------------------------------------------------------

# ---------- Tag names, key and value to look for
# instances tagged using this will be stopped.
# update these to match your tags
# also update command (look for WORKAROUND)
TAG_NS="tag_ns1"
TAG_KEY="stop_non_working_hours"
TAG_VALUE="on"

# ---------- Functions
usage()
{
cat << EOF
Usage: $0 OCI_PROFILE [--confirm]

note: OCI_PROFILE must exist in ~/.oci/config file (see example below)
      If --confirm is not provided, the instances to stop are listed but not actually stopped

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
  oci --profile $PROFILE compute instance list -c $lcompid --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id, Status:\"lifecycle-state\"}" > $TMPFILE
  cat $TMPFILE

  # if no instance found in this compartment (TMPFILE empty), exit the function
  if [ ! -s $TMPFILE ]; then rm -f $TMPFILE; return; fi 

  cat $TMPFILE | sed '1,3d;$d' | while read s1 inst_name s2 inst_id s3 inst_status s4
  do
    if [ "$inst_status" == "RUNNING" ]
    then 
      # WORKAROUND: cannot use variable, hardcode TAG_NS and TAG_KEY
      ltag_value=`oci --profile $PROFILE compute instance get --instance-id $inst_id | jq -r '.[]."defined-tags"."tag_ns1"."stop_non_working_hours"' 2>/dev/null`
      if [ "$ltag_value" == "$TAG_VALUE" ]
      then 
        if [ $CONFIRM == true ]
        then
          echo "--> STOPPING instance $inst_name ($inst_id) because of TAG VALUE"
          oci --profile $PROFILE compute instance action --instance-id $inst_id --action STOP >/dev/null 2>&1
        else
          echo "--> Instance $inst_name ($inst_id) SHOULD BE STOPPED because of TAG VALUE --> re-run script with --confirm to actually stop instances"
        fi
      fi
    fi
  done
  rm -f $TMPFILE
}

# -------- main

OCI_CONFIG_FILE=~/.oci/config

CONFIRM=false

case $# in 
  1) if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then usage; fi
     PROFILE=$1
     ;;
  2) PROFILE=$1
     if [ "$2" != "--confirm" ]; then usage; fi
     CONFIRM=true
     ;;
  *) usage 
     ;;
esac

TMPFILE=tmp_$$

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

# -- list instances compartment by compartment (excluding root compartment but including all subcompartments)
oci --profile $PROFILE iam compartment list -c $TENANCYOCID --compartment-id-in-subtree true --all 2>/dev/null| egrep "^ *\"name|^ *\"id"|awk -F'"' '{ print $4 }'|while read compid
do
  read compname
  echo
  echo "Compartment $compname, OCID=$compid"
  process_compartment $compid
done

rm -f $TMPFILE
exit 0