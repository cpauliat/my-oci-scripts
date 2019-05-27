#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script lists all objects (detailed list below) in a given compartment in a region using OCI CLI
#
# Note: this script does not list objects in the subcompartments of the given compartment
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
# Last update   : May 27, 2019
# Platforms     : MacOS / Linux
#
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2019-05-14: Initial Version
#    2019-05-27: Add policies + support for compartment name
# --------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 OCI_PROFILE compartment_name
    or $0 OCI_PROFILE compartment_ocid

Examples:
    $0 EMEAOSCf root
    $0 EMEAOSCf osci152506_cpauliat
    $0 EMEAOSCf ocid1.compartment.oc1..aaaaaaaakqmkvukdc2k7rmrhudttz2tpztari36v6mkaikl7wnu2wpkw2iqw      (non-root compartment OCID)
    $0 EMEAOSCf ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5h7l6ypedgnj3lfd2eeku6fq4lq34v3r3qqmmqx          (root compartment OCID)

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

# ---- Colored output (modify to "" if you don't want colored output)
COLOR_TITLE="\033[32m"              # green
COLOR_COMP="\033[93m"               # light yellow
COLOR_NORMAL="\033[39m"

# ---------------- functions to list objects
list_compute_instances()
{
  echo
  echo -e "${COLOR_TITLE}========== Compute Instances${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE compute instance list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_custom_images()
{
  echo
  echo -e "${COLOR_TITLE}========== Custom Images${COLOR_NORMAL}"
  echo
  #oci --profile $PROFILE compute image list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
  oci --profile $PROFILE compute image list -c $COMPID --output table --all --query "data [?\"compartment-id\"!=null].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_boot_volumes()
{
  echo
  echo -e "${COLOR_TITLE}========== Boot volumes${COLOR_NORMAL}"
  echo
  for ad in $ADS
  do
    echo "Availability-domain $ad"
    oci --profile $PROFILE bv boot-volume list -c $COMPID --output table --all --availability-domain $ad --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
  done
}

list_boot_volume_backups()
{
  echo
  echo -e "${COLOR_TITLE}========== Boot volume backups${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE bv boot-volume-backup list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_block_volumes()
{
  echo
  echo -e "${COLOR_TITLE}========== Block volumes${COLOR_NORMAL}"
  echo
  for ad in $ADS
  do
    echo "Availability-domain $ad"
    oci --profile $PROFILE bv volume list -c $COMPID --output table --all --availability-domain $ad --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
  done
}

list_block_volume_backups()
{
  echo
  echo -e "${COLOR_TITLE}========== Block volume backups${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE bv backup list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_volume_groups()
{
  echo
  echo -e "${COLOR_TITLE}========== Volumes groups${COLOR_NORMAL}"
  echo
  for ad in $ADS
  do
    echo "Availability-domain $ad"
    oci --profile $PROFILE bv volume-group list -c $COMPID --output table --all --availability-domain $ad --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
  done
}

list_volume_group_backups()
{
  echo
  echo -e "${COLOR_TITLE}========== Volumes group backups${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE bv volume-group-backup list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_filesystems()
{
  echo
  echo -e "${COLOR_TITLE}========== File Storage - Filesystems ${COLOR_NORMAL}"
  echo
  for ad in $ADS
  do
    echo "Availability-domain $ad"
    oci --profile $PROFILE fs file-system list -c $COMPID --output table --all --availability-domain $ad --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
  done
}

list_mount_targets()
{
  echo
  echo -e "${COLOR_TITLE}========== File Storage - Mount targets ${COLOR_NORMAL}"
  echo
  for ad in $ADS
  do
    echo "Availability-domain $ad"
    oci --profile $PROFILE fs mount-target list -c $COMPID --output table --all --availability-domain $ad --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
  done
}

list_vcns()
{
  echo
  echo -e "${COLOR_TITLE}========== Virtal Cloud Networks (VCNs)${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE network vcn list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_drgs()
{
  echo
  echo -e "${COLOR_TITLE}========== Dynamic Routing Gateways (DRGs)${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE network drg list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_cpes()
{
  echo
  echo -e "${COLOR_TITLE}========== Customer Premises Equipments (CPEs)${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE network cpe list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id}"
}

# - networking    : VCN, DRG, CPE, IPsec connection, LB, public IPs

list_ipsecs()
{
  echo
  echo -e "${COLOR_TITLE}========== IPsec connections${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE network ip-sec-connection list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_lbs()
{
  echo
  echo -e "${COLOR_TITLE}========== Load balancers${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE lb load-balancer list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_public_ips()
{
  echo
  echo -e "${COLOR_TITLE}========== Reserved Public IPs${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE network public-ip list -c $COMPID --scope region --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_policies()
{
  echo
  echo -e "${COLOR_TITLE}========== Policies${COLOR_NORMAL}"
  echo
  oci --profile $PROFILE iam policy list -c $COMPID --output table --all --query "data [*].{Name:\"name\", OCID:id, Status:\"lifecycle-state\"}"
}

# ---------------- misc
get_comp_id_from_comp_name()
{
  local name=$1
  if [ "$name" == "root" ]
  then
    echo $TENANCYOCID
  else
    oci --profile $PROFILE iam compartment list --all --query "data [?\"name\" == '$name'].{id:id}" |jq -r '.[].id'
  fi
}

get_comp_name_from_comp_id()
{
  local id=$1
  echo $id | grep "ocid1.tenancy.oc1" > /dev/null 2>&1
  if [ $? -eq 0 ]
  then
    echo root
  else
    oci --profile $PROFILE iam compartment list --all --query "data [?\"id\" == '$id'].{name:name}" |jq -r '.[].name'
  fi
}

# ---------------- main

OCI_CONFIG_FILE=~/.oci/config
TMP_COMPID_LIST=tmp_compid_list_$$
TMP_COMPNAME_LIST=tmp_compname_list_$$

# -- Check usage
if [ $# -ne 2 ]; then usage; fi

PROFILE=$1
COMP=$2

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: profile $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- Get the list of compartment OCIDs
echo $TENANCYOCID > $TMP_COMPID_LIST            # root compartment
oci --profile $PROFILE iam compartment list -c $TENANCYOCID --all |jq '.data[].id' | sed 's#"##g' >> $TMP_COMPID_LIST

# -- Get the list of compartment names
echo "root" > $TMP_COMPNAME_LIST                # root compartment
oci --profile $PROFILE iam compartment list -c $TENANCYOCID --all |jq '.data[].name' | sed 's#"##g' >> $TMP_COMPNAME_LIST

# -- Check if provided compartment is an existing compartment name
grep "^$COMP" $TMP_COMPNAME_LIST > /dev/null 2>&1
if [ $? -eq 0 ]
then
  COMPNAME=$COMP; COMPID=`get_comp_id_from_comp_name $COMPNAME`
else
  # -- if not, check if it is an existing compartment OCID
  grep "^$COMP" $TMP_COMPID_LIST > /dev/null 2>&1
  if [ $? -eq 0 ]
  then
    COMPID=$COMP; COMPNAME=`get_comp_name_from_comp_id $COMPID`
  else
    echo "ERROR: $COMP is not an existing compartment name or compartment id in this tenancy !"; exit 4; fi
    rm -f $TMP_COMPID_LIST
    rm -f $TMP_COMPNAME_LIST
  fi

rm -f $TMP_COMPID_LIST
rm -f $TMP_COMPNAME_LIST

# -- Get list of availability domains
ADS=`oci --profile $PROFILE iam availability-domain list|jq '.data[].name'|sed 's#"##g'`

# -- list objects in compartment
echo -e "${COLOR_TITLE}==================== OCI Objects list for compartment ${COLOR_COMP}${COMPNAME}${COLOR_TITLE} (${COLOR_COMP}${COMPID}${COLOR_TITLE})"
echo

list_compute_instances
list_custom_images
list_boot_volumes
list_boot_volume_backups
list_block_volumes
list_block_volume_backups
list_volume_groups
list_volume_group_backups
list_filesystems
list_mount_targets
list_vcns
list_drgs
list_cpes
list_ipsecs
list_lbs
list_public_ips
list_policies
