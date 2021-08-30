#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script looks for OCI resources from a free text
# it looks in all compartments in a OCI tenant in a region using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
#
# Authors       : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed, OCI config file configured with profiles and jq JSON parser
#
# Versions
#    2021-08-30: Initial Version
# --------------------------------------------------------------------------------------------------------------

# ---------- Functions 
usage()
{
  cat << EOF
Usage: ${0##*/} OCI_PROFILE searched_text

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
if [ $# -ne 2 ]; then usage; fi

PROFILE=$1
TEXT=$2

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 3; fi

# -- Search
oci --profile $PROFILE search resource free-text-search --text $TEXT | jq .
