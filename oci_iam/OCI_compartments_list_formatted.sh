#!/bin/bash
# --------------------------------------------------------------------------------------------------------------
# This script will list the compartment names and IDs in a OCI tenant using OCI CLI
# It will also list all subcompartments
# The output will be formatted with colors and indents to easily identify parents of subcompartments
#
# Note: OCI tenant given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Last update   : May 24, 2019
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2019-05-24: Initial Version
#    2019-05-31: if -h or --help provided, display the usage message
#    2019-10-02: change default behaviour (does not display deleted compartment)
#                and add option -d to list deleted compartments
#    2019-10-11: fix minor display bug
#    2020-03-20: change location of temporary files to /tmp + check oci exists
# --------------------------------------------------------------------------------------------------------------

# ---------- Colors for output
COLOR_YELLOW="\e[93m"
COLOR_RED="\e[91m"
COLOR_GREEN="\e[32m"
COLOR_NORMAL="\e[39m"
COLOR_CYAN="\e[96m"
COLOR_BLUE="\e[94m"
COLOR_GREY="\e[90m"

# ---------- Functions
usage()
{
cat << EOF
Usage: $0 [-d] OCI_PROFILE

    If -d is provided, deleted compartments are also listed.
    If not, only active compartments are listed.

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

get_cpt_name_from_id()
{
  id=$1
  grep -A 2 $id $TMP_FILE|egrep -v "ocid1.compartment|ACTIVE|DELETED"
}

get_cpt_state_from_id()
{
  id=$1
  grep -A 2 $id $TMP_FILE|egrep  "ACTIVE|DELETED"
}

# $1 = parent compartment
list_compartments()
{
  local parent_id=$1
  local level=$2    # 0 for root, 1 for 1st level compartments, ...
  local i
  local nb_cpts

  i=1;
  while [ $i -lt $level ]
  do
    if [ `cat ${TMP_FILE}_$i` == "0" ]; then printf "${COLOR_CYAN}│      "; else printf "       "; fi
    ((i++))
  done
  if [ $level -gt 0 ]; then
    if [ `cat ${TMP_FILE}_$level` == "0" ]; then printf "${COLOR_CYAN}├───── "; else printf "${COLOR_CYAN}└───── "; fi
  fi

  if [ $level -gt 0 ]; then
    cptname=`get_cpt_name_from_id $parent_id`
    state=`get_cpt_state_from_id $parent_id`
  else
    cptname='root'
    state="ACTIVE"
  fi
  if [ "$state" == "ACTIVE" ]; then
    printf "${COLOR_GREEN}%s ${COLOR_NORMAL}%s ${COLOR_YELLOW}ACTIVE ${COLOR_NORMAL}\n" "$cptname" "$parent_id"
  else
    printf "${COLOR_BLUE}%s ${COLOR_GREY}%s ${COLOR_RED}DELETED ${COLOR_NORMAL}\n" "$cptname" "$parent_id"
  fi

  if [ $LIST_DELETED == true ]
  then
    cptid_list=`oci --profile $PROFILE iam compartment list -c $parent_id --all 2>/dev/null| grep "^ *\"id" |awk -F'"' '{ print $4 }'`
  else
    cptid_list=`oci --profile $PROFILE iam compartment list -c $parent_id --all --query "data [?\"lifecycle-state\" == 'ACTIVE'].{id:id}" 2>/dev/null | grep "^ *\"id" |awk -F'"' '{ print $4 }'`
  fi

  if [ "$cptid_list" != "" ]; then
    nb_cpts=`echo $cptid_list | wc -w`
    i=1
    for cptid in $cptid_list
    do
      level1=`expr $level + 1`
      if [ $i -eq $nb_cpts ]; then echo 1 > ${TMP_FILE}_$level1; else echo 0 > ${TMP_FILE}_$level1; fi
      list_compartments $cptid `expr $level + 1`
      ((i++))
    done
  fi
}

cleanup()
{
  rm -f $TMP_FILE ${TMP_FILE}_*
}

trap_ctrl_c()
{
  echo
  echo -e "${COLOR_RED}SCRIPT INTERRUPTED BY USER ! ${COLOR_NORMAL}"
  echo

  cleanup
  exit 99
}

# -------- main

OCI_CONFIG_FILE=~/.oci/config

TMP_FILE=/tmp/tmp_$$
LIST_DELETED=false

if [ $# -ne 1 ] && [ $# -ne 2 ]; then usage; fi

if [ "$1"  == "-h" ] || [ "$1"  == "--help" ]; then usage; fi
if [ "$2"  == "-h" ] || [ "$2"  == "--help" ]; then usage; fi

case $# in 
1) PROFILE=$1
   ;;
2) PROFILE=$2
   if [ "$1" == "-d" ]; then LIST_DELETED=true; else usage; fi
   ;;
esac

# -- trap ctrl-c and call trap_ctrl_c()
trap trap_ctrl_c INT

# -- Check if oci is installed
which oci > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: oci not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: PROFILE $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- get the list of all compartments and sub-compartments (excluding root compartment)
oci --profile $PROFILE iam compartment list -c $TENANCYOCID --compartment-id-in-subtree true --all 2>/dev/null| egrep "^ *\"name|^ *\"id|^ *\"lifecycle-state"|awk -F'"' '{ print $4 }' >$TMP_FILE

# -- recursive call to list all compartments and sub-compartments in right order
list_compartments $TENANCYOCID 0

cleanup
exit 0