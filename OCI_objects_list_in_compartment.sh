#!/bin/bash

# --------------------------------------------------------------------------------------------------------------------------
# This script lists all objects (detailed list below) in a given compartment in a region or all active regions using OCI CLI
#
# Note: this script does not list objects in the subcompartments of the given compartment
#
# Supported objects:
# - COMPUTE            : compute instances, custom images, boot volumes, boot volumes backups
# - BLOCK STORAGE      : block volumes, block volumes backups, volume groups, volume groups backups
# - OBJECT STORAGE     : buckets
# - FILE STORAGE       : file systems, mount targets
# - NETWORKING         : VCN, DRG, CPE, IPsec connection, LB, public IPs
# - DATABASE           : DB Systems, DB Systems backups, Autonomous DB, Autonomous DB backups
# - RESOURCE MANAGER   : Stacks
# - EDGE SERVICES      : DNS zones
# - DEVELOPER SERVICES : Container clusters (OKE)
# - IDENTITY           : Policies
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2019-05-14: Initial Version
#    2019-05-27: Add policies + support for compartment name
#    2019-05-29: Add -a to list in all active regions
#    2019-05-31: if -h or --help provided, display the usage message
#    2019-06-03: fix bug for sub-compartments + add ctrl-C handler
#    2019-06-06: list more objects (DATABASE, OBJECT STORAGE, RESOURCE MANAGER, EDGE SERVICES, DEVELOPER SERVICES)
# --------------------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 [-a] OCI_PROFILE compartment_name
    or $0 [-a] OCI_PROFILE compartment_ocid

    By default, only the objects in the region provided in the profile are listed
    If -a is provided, the objects from all active regions are listed

Examples:
    $0 -a EMEAOSCf root
    $0 EMEAOSCf osci157078_cpauliat
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

# ---- Colored output or not
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLORED_OUTPUT=true
if [ "$COLORED_OUTPUT" == true ]
then
  COLOR_TITLE1="\033[91m"             # green
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

# ---------------- functions to list objects
list_compute_instances()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== COMPUTE: Instances${COLOR_NORMAL}"
  oci --profile $lp compute instance list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_compute_custom_images()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== COMPUTE: Custom Images${COLOR_NORMAL}"
  oci --profile $lp compute image list -c $COMPID --output table --all --query 'data [?"compartment-id"!=null].{Name:"display-name", OCID:id, Status:"lifecycle-state"}' 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show."
}

list_compute_boot_volumes()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== COMPUTE: Boot volumes${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $lp bv boot-volume list -c $COMPID --output table --all --availability-domain $ad --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
  done
}

list_compute_boot_volume_backups()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== COMPUTE: Boot volume backups${COLOR_NORMAL}"
  oci --profile $lp bv boot-volume-backup list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_block_storage_volumes()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Block volumes${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $lp bv volume list -c $COMPID --output table --all --availability-domain $ad --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
  done
}

list_block_storage_volume_backups()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Block volume backups${COLOR_NORMAL}"
  oci --profile $lp bv backup list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_block_storage_volume_groups()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Volumes groups${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $lp bv volume-group list -c $COMPID --output table --all --availability-domain $ad --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
  done
}

list_block_storage_volume_group_backups()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Volumes group backups${COLOR_NORMAL}"
  oci --profile $lp bv volume-group-backup list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_object_storage_buckets()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== OBJECT STORAGE: Buckets${COLOR_NORMAL}"
  oci --profile $lp os bucket list -c $COMPID --output table --all --query 'data [*].{Name:name}'
}

list_file_storage_filesystems()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== FILE STORAGE: Filesystems ${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $lp fs file-system list -c $COMPID --output table --all --availability-domain $ad --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
  done
}

list_file_storage_mount_targets()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== FILE STORAGE: Mount targets ${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $lp fs mount-target list -c $COMPID --output table --all --availability-domain $ad --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
  done
}

list_networking_vcns()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== NETWORKING: Virtal Cloud Networks (VCNs)${COLOR_NORMAL}"
  oci --profile $lp network vcn list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_drgs()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== NETWORKING: Dynamic Routing Gateways (DRGs)${COLOR_NORMAL}"
  oci --profile $lp network drg list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_cpes()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== NETWORKING: Customer Premises Equipments (CPEs)${COLOR_NORMAL}"
  oci --profile $lp network cpe list -c $COMPID --output table --all --query "data [*].{Name:\"display-name\", OCID:id}"
}

list_networking_ipsecs()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== NETWORKING: IPsec connections${COLOR_NORMAL}"
  oci --profile $lp network ip-sec-connection list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_lbs()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== NETWORKING: Load balancers${COLOR_NORMAL}"
  oci --profile $lp lb load-balancer list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_public_ips()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== NETWORKING: Public IPs${COLOR_NORMAL}"
  oci --profile $lp network public-ip list -c $COMPID --scope region --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_db_systems()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== DATABASE: DB Systems${COLOR_NORMAL}"
  oci --profile $lp db system list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_db_systems_backups()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== DATABASE: DB Systems backups${COLOR_NORMAL}"
  oci --profile $lp db backup list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_autonomous_db()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== DATABASE: Autonomous databases (ATP/ADW)${COLOR_NORMAL}"
  oci --profile $lp db autonomous-database list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_autonomous_backups()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== DATABASE: Autonomous databases backups${COLOR_NORMAL}"
  oci --profile $lp db autonomous-database-backup list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_resource_manager_stacks()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== RESOURCE MANAGER: Stacks${COLOR_NORMAL}"
  oci --profile $lp resource-manager stack list -c $COMPID --output table --all --query 'data [*].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_edge_services_dns_zones()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== EDGE SERVICES: DNS zones${COLOR_NORMAL}"
  oci --profile $lp dns zone list -c $COMPID --output table --all --query 'data [*].{Name:name, OCID:id, Status:"lifecycle-state"}' 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show."
}

list_developer_services_oke()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== DEVELOPER SERVICES: Container clusters (OKE)${COLOR_NORMAL}"
  oci --profile $lp ce cluster list -c $COMPID --output table --all --query 'data [*].{Name:name, OCID:id, Status:"lifecycle-state"}'
}

list_identity_policies()
{
  local lp=$1
  echo -e "${COLOR_TITLE2}========== IDENTITY: Policies${COLOR_NORMAL}"
  oci --profile $lp iam policy list -c $COMPID --output table --all --query 'data [*].{Name:name, OCID:id, Status:"lifecycle-state"}'
}

list_all_objects()
{
  local lregion=$1
  local lcptname=$2
  local lcptid=$3
  local lprofile

  if [ "$lregion" == "$CURRENT_REGION" ]
  then
    lprofile=$PROFILE
  else
    lprofile=$TMP_PROFILE
    cp -p $OCI_CONFIG_FILE ${OCI_CONFIG_FILE_BACKUP}
    grep -A 5 "\[${PROFILE}\]" ${OCI_CONFIG_FILE_BACKUP} | sed -e "s#${PROFILE}#${TMP_PROFILE}#g" -e "s#${CURRENT_REGION}#${lregion}#" >> $OCI_CONFIG_FILE
  fi

  # -- Get list of availability domains
  ADS=`oci --profile $lprofile iam availability-domain list|jq '.data[].name'|sed 's#"##g'`

  echo
  echo -e "${COLOR_TITLE1}==================== OCI Objects list for compartment ${COLOR_COMP}${lcptname}"
  echo -e "${COLOR_TITLE1}====================     (${COLOR_COMP}${lcptid}${COLOR_TITLE1})"
  echo -e "${COLOR_TITLE1}==================== in region ${COLOR_COMP}${lregion}${COLOR_NORMAL}"

  list_compute_instances $lprofile
  list_compute_custom_images $lprofile
  list_compute_boot_volumes $lprofile
  list_compute_boot_volume_backups $lprofile
  list_block_storage_volumes $lprofile
  list_block_storage_volume_backups $lprofile
  list_block_storage_volume_groups $lprofile
  list_block_storage_volume_group_backups $lprofile
  list_object_storage_buckets $lprofile
  list_file_storage_filesystems $lprofile
  list_file_storage_mount_targets $lprofile
  list_networking_vcns $lprofile
  list_networking_drgs $lprofile
  list_networking_cpes $lprofile
  list_networking_ipsecs $lprofile
  list_networking_lbs $lprofile
  list_networking_public_ips $lprofile
  list_database_db_systems $lprofile
  list_database_db_systems_backups $lprofile
  list_database_autonomous_db $lprofile
  list_database_autonomous_backups $lprofile
  list_resource_manager_stacks $lprofile
  list_edge_services_dns_zones $lprofile
  list_developer_services_oke $lprofile
  list_identity_policies $lprofile

  if [ "$lregion" != "$CURRENT_REGION" ]
  then
    cp -p ${OCI_CONFIG_FILE_BACKUP} $OCI_CONFIG_FILE
    rm -f ${OCI_CONFIG_FILE_BACKUP}
  fi

  echo -e "${COLOR_TITLE1}==================== End of OBJECTS LIST in region ${COLOR_COMP}${lregion}${COLOR_NORMAL}"
}

# ---------------- misc

get_comp_id_from_comp_name()
{
  local name=$1
  if [ "$name" == "root" ]
  then
    echo $TENANCYOCID
  else
    oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --query "data [?\"name\" == '$name'].{id:id}" |jq -r '.[].id'
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
    oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --query "data [?\"id\" == '$id'].{name:name}" |jq -r '.[].name'
  fi
}

get_all_active_regions()
{
  oci --profile $PROFILE iam region-subscription list --query "data [].{Region:\"region-name\"}" |jq -r '.[].Region'
}

cleanup()
{
  rm -f $TMP_FILE_COMPID_LIST
  rm -f $TMP_FILE_COMPNAME_LIST
  rm -f $TMP_FILE
}

trap_ctrl_c()
{
  echo
  echo -e "${COLOR_BREAK}SCRIPT INTERRUPTED BY USER ! ${COLOR_NORMAL}"
  echo

  cleanup
  if [ -f ${OCI_CONFIG_FILE_BACKUP} ]
  then
    cp -p ${OCI_CONFIG_FILE_BACKUP} $OCI_CONFIG_FILE
    rm -f ${OCI_CONFIG_FILE_BACKUP}
  fi

  exit 99
}

# ---------------- main

OCI_CONFIG_FILE=~/.oci/config
OCI_CONFIG_FILE_BACKUP=~/.oci/config_backup.$$
TMP_FILE=tmp_$$
TMP_FILE_COMPID_LIST=${TMP_FILE}_compid_list
TMP_FILE_COMPNAME_LIST=${TMP_FILE}_compname_list
TMP_PROFILE=tmp$$

# -- Check usage
if [ $# -ne 2 ] && [ $# -ne 3 ]; then usage; fi

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then usage; fi
if [ "$2" == "-h" ] || [ "$2" == "--help" ]; then usage; fi
if [ "$3" == "-h" ] || [ "$3" == "--help" ]; then usage; fi

case $# in
  2) PROFILE=$1;  COMP=$2;  ALL_REGIONS=false
     ;;
  3) if [ "$1" != "-a" ]; then usage; fi
     PROFILE=$2;  COMP=$3;  ALL_REGIONS=true
     ;;
esac

# -- trap ctrl-c and call ctrl_c()
trap trap_ctrl_c INT

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: jq not found !"; exit 2; fi

# -- Check if the PROFILE exists
grep "\[$PROFILE\]" $OCI_CONFIG_FILE > /dev/null 2>&1
if [ $? -ne 0 ]; then echo "ERROR: profile $PROFILE does not exist in file $OCI_CONFIG_FILE !"; exit 3; fi

# -- get tenancy OCID from OCI PROFILE
TENANCYOCID=`egrep "^\[|ocid1.tenancy" $OCI_CONFIG_FILE|sed -n -e "/\[$PROFILE\]/,/tenancy/p"|tail -1| awk -F'=' '{ print $2 }' | sed 's/ //g'`

# -- Get the list of compartment OCIDs and names
echo $TENANCYOCID > $TMP_FILE_COMPID_LIST            # root compartment
echo "root"       > $TMP_FILE_COMPNAME_LIST          # root compartment
oci --profile $PROFILE iam compartment list -c $TENANCYOCID --compartment-id-in-subtree true --all > $TMP_FILE
jq '.data[].id'   < $TMP_FILE | sed 's#"##g' >> $TMP_FILE_COMPID_LIST
jq '.data[].name' < $TMP_FILE | sed 's#"##g' >> $TMP_FILE_COMPNAME_LIST
rm -f $TMP_FILE

# -- Check if provided compartment is an existing compartment name
grep "^${COMP}$" $TMP_FILE_COMPNAME_LIST > /dev/null 2>&1
if [ $? -eq 0 ]
then
  COMPNAME=$COMP; COMPID=`get_comp_id_from_comp_name $COMPNAME`
else
  # -- if not, check if it is an existing compartment OCID
  grep "^$COMP" $TMP_FILE_COMPID_LIST > /dev/null 2>&1
  if [ $? -eq 0 ]
  then
    COMPID=$COMP; COMPNAME=`get_comp_name_from_comp_id $COMPID`
  else
    echo "ERROR: $COMP is not an existing compartment name or compartment id in this tenancy !"
    cleanup; exit 4
  fi
fi

# -- Get the current region from the profile
egrep "^\[|^region" ${OCI_CONFIG_FILE} | fgrep -A 1 "[${PROFILE}]" |grep "^region" > $TMP_FILE 2>&1
if [ $? -ne 0 ]; then echo "ERROR: region not found in OCI config file $OCI_CONFIG_FILE for profile $PROFILE !"; cleanup; exit 5; fi
CURRENT_REGION=`awk -F'=' '{ print $2 }' $TMP_FILE | sed 's# ##g'`

# -- list objects in compartment
if [ $ALL_REGIONS == false ]
then
  list_all_objects $CURRENT_REGION $COMPNAME $COMPID
else
  REGIONS_LIST=`get_all_active_regions`
  echo -e "${COLOR_TITLE1}==================== List of active regions in tenancy${COLOR_NORMAL}"
  for region in $REGIONS_LIST; do echo $region; done

  for region in $REGIONS_LIST
  do
    list_all_objects $region $COMPNAME $COMPID
  done
fi

# -- Normal completion of script without errors
cleanup
exit 0
