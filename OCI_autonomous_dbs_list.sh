#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script will list the autonomous databases in all compartments in a OCI tenant in a region or all regions
# using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2019-10-14: Initial Version
# --------------------------------------------------------------------------------------------------------------

# -------- functions

usage()
{
cat << EOF
Usage: $0 [-q] [-a] OCI_PROFILE

Notes: 
- OCI_PROFILE must exist in ~/.oci/config file (see example below)
- If -q is provided, output is minimal (quiet mode): only stopped/started autonomous databases are displayed.
- If -a is provided, the script processes all active regions instead of singe region provided in profile

[EMEAOSCf]
tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx
key_file    = /Users/cpauliat/.oci/api_key.pem
region      = eu-frankfurt-1
EOF
  exit 1
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
  ${OCI} --profile $PROFILE iam region-subscription list --query "data [].{Region:\"region-name\"}" |jq -r '.[].Region'
}

cleanup()
{
  rm -f $TMP_FILE
}

trap_ctrl_c()
{
  echo
  echo -e "${COLOR_BREAK}SCRIPT INTERRUPTED BY USER ! ${COLOR_NORMAL}"
  echo

  cleanup
  exit 99
}

# ---- Colored output or not
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLORED_OUTPUT=true
if [ "$COLORED_OUTPUT" == true ]
then
  COLOR_TITLE0="\033[95m"             # light magenta
  COLOR_TITLE1="\033[91m"             # light red
  COLOR_TITLE2="\033[32m"             # green
  COLOR_COMP="\033[93m"               # light yellow
  COLOR_BREAK="\033[91m"              # light red
  COLOR_NORMAL="\033[39m"
else
  COLOR_TITLE0=""
  COLOR_TITLE1=""
  COLOR_TITLE2=""
  COLOR_COMP=""
  COLOR_BREAK=""
  COLOR_NORMAL=""
fi

quiet_display()
{
  local lregion=$1
  local lcompname=$2

  # remove first 3 lines and list line to get instances details
  cat $TMP_FILE | sed '1,3d;$d' | awk -F' ' '{ print $2 }' | while read adb_id
  do
    adb_status=`${OCI} --profile $PROFILE db autonomous-database get --region $lregion --autonomous-database-id $adb_id | jq -r '.[]."lifecycle-state"' 2>/dev/null`
    adb_name=`${OCI} --profile $PROFILE db autonomous-database get --region $lregion --autonomous-database-id $adb_id | jq -r '.[]."display-name"' 2>/dev/null`
    printf "%-15s %-20s %-20s %-100s %-10s\n" "$lregion" "$lcompname" "$adb_name" "$adb_id" "$adb_status"
  done
}
# -------- main

OCI_CONFIG_FILE=~/.oci/config
OCI=$HOME/bin/oci

TMP_FILE=tmp_$$

ALL_REGIONS=false
QUIET_MODE=false

if [ "$1" == "-q" ]; then QUIET_MODE=true; shift; fi
if [ "$1" == "-a" ]; then ALL_REGIONS=true; shift; fi

if [ $# -eq 1 ]; then PROFILE=$1; else usage; fi

# -- trap ctrl-c and call trap_ctrl_c()
trap trap_ctrl_c INT

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 2; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- set the list of regions
if [ $ALL_REGIONS == false ]
then
  REGIONS_LIST=`get_region_from_profile`
else
  REGIONS_LIST=`get_all_active_regions`
fi

for region in $REGIONS_LIST
do
  if [ $QUIET_MODE == false ]
  then
    echo -e "${COLOR_TITLE1}==================== REGION ${COLOR_COMP}${region}${COLOR_NORMAL}"
  
    # -- list autonomous dbs in the root compartment
    echo
    echo -e "${COLOR_TITLE0}========== COMPARTMENT ${COLOR_COMP}root${COLOR_TITLE0} (${COLOR_COMP}${TENANCYOCID}${COLOR_TITLE0}) ${COLOR_NORMAL}"
  fi
  ${OCI} --profile $PROFILE db autonomous-database list -c $TENANCYOCID --region $region --output table --query "data [*].{ADB_name:\"display-name\", ADB_id:id, Status:\"lifecycle-state\"}" > $TMP_FILE
  if [ -s $TMP_FILE ] 
  then
    if [ $QUIET_MODE == false ]
    then
      cat $TMP_FILE
    else
      quiet_display $region root 
    fi
  fi

  # -- list utonomous dbs compartment by compartment (excluding root compartment but including all subcompartments)
  ${OCI} --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --query "data [?\"lifecycle-state\" == 'ACTIVE']" 2>/dev/null| egrep "^ *\"name|^ *\"id"|awk -F'"' '{ print $4 }'|while read compid
  do
    read compname
    if [ $QUIET_MODE == false ]
    then
      echo
      echo -e "${COLOR_TITLE0}========== COMPARTMENT ${COLOR_COMP}${compname}${COLOR_TITLE0} (${COLOR_COMP}${compid}${COLOR_TITLE0}) ${COLOR_NORMAL}"
    fi
    ${OCI} --profile $PROFILE db autonomous-database list -c $compid --region $region --output table --query "data [*].{ADB_name:\"display-name\", ADB_id:id, Status:\"lifecycle-state\"}" > $TMP_FILE
    if [ -s $TMP_FILE ] 
    then
      if [ $QUIET_MODE == false ]
      then
        cat $TMP_FILE
      else
        quiet_display $region $compname 
      fi
    fi
  done
done 

cleanup
exit 0