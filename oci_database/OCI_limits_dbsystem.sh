#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# script OCI_limits_dbsystem.sh
#
# This script will list the database systems limits in a specific region on an OCI tenant
# Note: OCI tenant given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI 2.6.2 or later installed and OCI config file configured with profiles
#
# Versions
#    2020-11-05: Initial Version 
# --------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 [-a] [-z] OCI_PROFILE 
 
    By default, only the limits in the region provided in the profile are listed
    If -a is provided, the limits from all active regions are listed
    If -z is provided, limits with quota set to 0 are also listed
    Note: if both -a and -z are provided, -a must be provided first

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

# ---- Colored output or not
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLORED_OUTPUT=true
if [ "$COLORED_OUTPUT" == true ]
then
  COLOR_TITLE1="\033[91m"             # light red
  COLOR_TITLE2="\033[32m"             # green
  COLOR_AD="\033[94m"                 # light blue
  COLOR_COMP="\033[93m"               # light yellow
  COLOR_BREAK="\033[91m"              # light red
  COLOR_NORMAL="\033[39m"
else
  COLOR_TITLE1=""
  COLOR_TITLE2=""
  COLOR_AD=""
  COLOR_COMP=""
  COLOR_BREAK=""
  COLOR_NORMAL=""
fi

list_limits()
{
  local lregion=$1

  echo
  echo -e "${COLOR_TITLE1}==================== DATABASE LIMITS for region ${COLOR_COMP}${lregion}${COLOR_NORMAL}"
  echo

  # Get list of availability domains
  ADS=`oci --profile $PROFILE --region $lregion iam availability-domain list|jq '.data[].name'|sed 's#"##g'`

  max=0
  for ad in $ADS
  do
    printf "${COLOR_AD}   AD = %-33s${COLOR_NORMAL}\n" $ad > ${TMP_FILE}_AD_$ad
    oci --profile $PROFILE limits value list --service-name database --region $lregion --availability-domain $ad \
        --compartment-id $TENANCYOCID --all --output table --query "data [*].{Shape:name, Number:value}" | while read myline
    do
      value=`echo $myline| awk -F' ' '{ print $2 }'`
      if [ "$value" != 0 ]; then 
        printf "${COLOR_COMP}%-40s${COLOR_NORMAL}\n" "$myline"
      else
        if [ $LIST_ZEROS == true ]; then printf "${COLOR_NORMAL}%-40s${COLOR_NORMAL}\n" "$myline"; fi
      fi
    done >> ${TMP_FILE}_AD_$ad

    # find the maximum number of lines of the tempo files
    nb_lines=`wc -l ${TMP_FILE}_AD_$ad | awk -F' ' '{print $1}'`
    if [ $nb_lines -gt $max ]; then max=$nb_lines; fi
  done

  # add space lines to each tempo files so that they all have the same number of lines
  for ad in $ADS
  do
    nb_lines=`wc -l ${TMP_FILE}_AD_$ad | awk -F' ' '{print $1}'`
    i=$nb_lines
    while [ $i -lt $max ]
    do
      printf "%-41s\n" "" >> ${TMP_FILE}_AD_$ad
      i=`expr $i + 1`
    done
  done

  # display the AD files in columns
  paste ${TMP_FILE}_AD_*
  
  rm -f ${TMP_FILE}_AD_*
} 


# ---------------- misc

get_all_active_regions()
{
  oci --profile $PROFILE iam region-subscription list --query "data [].{Region:\"region-name\"}" |jq -r '.[].Region'
}

cleanup()
{
  rm -f $TMP_FILE
  rm -f ${TMP_FILE}_AD_*
}

trap_ctrl_c()
{
  echo
  echo -e "${COLOR_BREAK}SCRIPT INTERRUPTED BY USER ! ${COLOR_NORMAL}"
  echo

  cleanup
  exit 99
}

# -------- main

OCI_CONFIG_FILE=~/.oci/config
TMP_FILE=/tmp/tmp_$$
TMP_PROFILE=/tmp/tmp_$$_profile

ALL_REGIONS=false
LIST_ZEROS=false

# -- Check usage
if [ $# -ne 1 ] && [ $# -ne 2 ] && [ $# -ne 3 ]; then usage; fi

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then usage; fi
if [ "$2" == "-h" ] || [ "$2" == "--help" ]; then usage; fi

case $# in
  1) PROFILE=$1
     ;;
  2) PROFILE=$2;
     if [ "$1" == "-a" ]; then ALL_REGIONS=true;
     elif [ "$1" == "-z" ]; then LIST_ZEROS=true; else usage; fi
     ;;
  3) PROFILE=$3;
     if [ "$1" == "-a" ]; then ALL_REGIONS=true; else usage; fi
     if [ "$2" == "-z" ]; then LIST_ZEROS=true; else usage; fi
     ;;
esac

# -- trap ctrl-c and call ctrl_c()
trap trap_ctrl_c INT

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: profile $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- list database limits in tenancy
if [ $ALL_REGIONS == false ]
then
  # Get the current region from the profile
  egrep "^\[|^region" ${OCI_CONFIG_FILE} | fgrep -A 1 "[${PROFILE}]" |grep "^region" > $TMP_FILE 2>&1
  if [ $? -ne 0 ]; then echo "ERROR: region not found in OCI config file $OCI_CONFIG_FILE for profile $PROFILE !"; cleanup; exit 5; fi
  CURRENT_REGION=`awk -F'=' '{ print $2 }' $TMP_FILE | sed 's# ##g'`

  list_limits $CURRENT_REGION 
else
  REGIONS_LIST=`get_all_active_regions`

  echo -e "${COLOR_TITLE1}==================== List of active regions in tenancy${COLOR_NORMAL}"
  for region in $REGIONS_LIST; do echo $region; done

  for region in $REGIONS_LIST
  do
    list_limits $region 
  done
fi

# -- Normal completion of script without errors
cleanup
exit 0