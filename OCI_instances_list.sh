#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script will list the instance names and IDs in all compartments in a OCI tenant in a region using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Last update   : May 14, 2019
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

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- list instances in the root compartment
echo
echo "Compartment root, OCID=$TENANCYOCID"
oci --profile $PROFILE compute instance list -c $TENANCYOCID --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id, Status:\"lifecycle-state\"}"

# -- list instances compartment by compartment (excluding root compartment)
oci --profile $PROFILE iam compartment list -c $TENANCYOCID --all 2>/dev/null|egrep "name|ocid1.compartment"|awk -F'"' '{ print $4 }'|while read compid
do
  read compname
  echo
  echo "Compartment $compname, OCID=$compid"
  #oci --profile $PROFILE compute instance list -c $compid --output table --query "data [*].{CompartmentOCID:\"compartment-id\",InstanceName:\"display-name\", InstanceOCID:id}"
  oci --profile $PROFILE compute instance list -c $compid --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id, Status:\"lifecycle-state\"}"
done
