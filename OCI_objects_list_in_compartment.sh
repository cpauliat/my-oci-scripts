#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script lists all objects (detailed list below) in a given compartment in a region using OCI CLI
#
# Note: it does not list objects in the subcompartments of the given compartment
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

For example:
    $0 EMEAOSCf ocid1.compartment.oc1..aaaaaaaakqmkvukdc2k7rmrhudttz2tpztari36v6mkaikl7wnu2wpkw2iqw

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
  echo
  echo -e "\033[32m========== Compute Instances\033[39m"
  echo
  oci --profile $PROFILE compute instance list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_custom_images()
{
  echo
  echo -e "\033[32m========== Custom Images\033[39m"
  echo
  #oci --profile $PROFILE compute image list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
  oci --profile $PROFILE compute image list -c $COMPID --output table --all --query "data [?\"compartment-id\"!=null].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_boot_volumes()
{
  echo
  echo -e "\033[32m========== Boot volumes\033[39m"
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
  echo -e "\033[32m========== Boot volume backups\033[39m"
  echo
  oci --profile $PROFILE bv boot-volume-backup list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_block_volumes()
{
  echo
  echo -e "\033[32m========== Block volumes\033[39m"
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
  echo -e "\033[32m========== Block volume backups\033[39m"
  echo
  oci --profile $PROFILE bv backup list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_volume_groups()
{
  echo
  echo -e "\033[32m========== Volumes groups\033[39m"
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
  echo -e "\033[32m========== Volumes group backups\033[39m"
  echo
  oci --profile $PROFILE bv volume-group-backup list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_filesystems()
{
  echo
  echo -e "\033[32m========== File Storage - Filesystems \033[39m"
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
  echo -e "\033[32m========== File Storage - Mount targets \033[39m"
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
  echo -e "\033[32m========== Virtal Cloud Networks (VCNs)\033[39m"
  echo
  oci --profile $PROFILE network vcn list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_drgs()
{
  echo
  echo -e "\033[32m========== Dynamic Routing Gateways (DRGs)\033[39m"
  echo
  oci --profile $PROFILE network drg list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_cpes()
{
  echo
  echo -e "\033[32m========== Customer Premises Equipments (CPEs)\033[39m"
  echo
  oci --profile $PROFILE network cpe list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id}"
}

# - networking    : VCN, DRG, CPE, IPsec connection, LB, public IPs

list_ipsecs()
{
  echo
  echo -e "\033[32m========== IPsec connections\033[39m"
  echo
  oci --profile $PROFILE network ip-sec-connection list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_lbs()
{
  echo
  echo -e "\033[32m========== Load balancers\033[39m"
  echo
  oci --profile $PROFILE lb load-balancer list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

list_public_ips()
{
  echo
  echo -e "\033[32m========== Reserved Public IPs\033[39m"
  echo
  oci --profile $PROFILE network public-ip list -c $COMPID --scope region --output table --all --query "data [*].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}"
}

# ---------------- main

OCI_CONFIG_FILE=~/.oci/config
TMP_COMPID_LIST=tmp_compid_list_$$

# -- Check usage
if [ $# -ne 2 ]; then usage; fi

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
rm -f $TMP_COMPID_LIST

# -- Get list of availability domains
ADS=`oci --profile $PROFILE iam availability-domain list|grep name|awk -F'"' '{ print $4 }'`

# -- list objects in compartment

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
