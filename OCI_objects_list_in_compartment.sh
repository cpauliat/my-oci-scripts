#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script lists all objects (detailed list below) in a given compartment in a region using OCI CLI
#
# Supported objects:
# - Compute       : compute instances, custom images, boot volumes, boot volumes backups
# - Block Storage : block volumes, block volumes backups, volume groups, volume groups backups
# - Object Storage: buckets
# - File Storage  : file systems, mount targets
# - networking    : VCN, DRG, CPE, IPsec connection, LB, public IPs
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Last update   : May 14, 2019
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed and OCI config file configured with profiles
# --------------------------------------------------------------------------------------------------------------


usage()
{
cat << EOF
Usage: $0 OCI_PROFILE compartment_ocid

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

list_compute_instances()
{
  oci --profile $PROFILE compute instance list -c $COMPID --output table --query "data [*].{InstanceName:\"display-name\", InstanceOCID:id}"
}

# ---------------- main

OCI_CONFIG_FILE=~/.oci/config
TMP_COMPID_LIST=tmp_compid_list_$$

# -- Check usage
if [ $# -ne 1 ]; then usage; fi

PROFILE=$1
COMPID=$2

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: profile $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 2; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- Get the list of compartment OCIDs
echo $TENANCYOCID > $TMP_COMPID_LIST            # root compartment
oci --profile $PROFILE iam compartment list -c $TENANCYOCID --all 2>/dev/null|egrep "ocid1.compartment"|awk -F'"' '{ print $4 }' >> $TMP_COMPID_LIST

# -- Check if provided compartment OCID exists
grep "^$COMPID$" $TMP_COMPID_LIST > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: compartement OCID $COMPID does not exist in this tenancy !"; exit 3; fi

# -- list instances the compartment
list_compute_instances
