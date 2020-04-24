#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script looks for OCI resources having a specific defined tag key and value 
# it looks in all compartments in a OCI tenant in a region using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
#
# Authors       : Matthieu Bordonne and Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed, OCI config file configured with profiles and jq JSON parser
#
# Versions
#    2020-04-24: Initial Version
# --------------------------------------------------------------------------------------------------------------

# ---------- Functions 
usage()
{
  cat << EOF
Usage: ${0##*/} OCI_PROFILE tag_namespace tag_key tag_value

Notes:
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

# -------- main

# -- parsing args
if [ $# -ne 4 ]; then usage; fi

PROFILE=$1
TAG_NS=$2
TAG_KEY=$3
TAG_VALUE=$4

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Search
oci --profile $PROFILE search resource structured-search \
  --query-text "query all resources where (definedTags.namespace = '$TAG_NS' \
  && definedTags.key = '$TAG_KEY' \
  && definedTags.value = '$TAG_VALUE')" \
  --output table \
  --query "data.items[*] | sort_by(@,&\"resource-type\") [].{Name:\"display-name\",Type:\"resource-type\",ID:identifier}"
