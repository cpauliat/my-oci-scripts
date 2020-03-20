#!/bin/bash

# --------------------------------------------------------------------------------------------------------------------------
# This script lists all objects (detailed list below) in a given compartment in a region or all active regions using OCI CLI
#
# Supported objects:
# - COMPUTE                : compute instances, custom images, boot volumes, boot volumes backups
# - BLOCK STORAGE          : block volumes, block volumes backups, volume groups, volume groups backups
# - OBJECT STORAGE         : buckets
# - FILE STORAGE           : file systems, mount targets
# - NETWORKING             : VCN, DRG, CPE, IPsec connection, LB, public IPs, DNS zones (common to all regions)
# - DATABASE               : DB Systems, DB Systems backups, Autonomous DB, Autonomous DB backups
# - RESOURCE MANAGER       : Stacks
# - EMAIL DELIVERY         : approved senders
# - APPLICATION INTEGRATION: Notifications, Events, Content and Experience
# - DEVELOPER SERVICES     : Container clusters (OKE), Functions applications
# - IDENTITY               : Policies (common to all regions)
# - GOVERNANCE             : Tags namespaces (common to all regions)
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat with some help from Matthieu Bordonne
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
#    2019-06-06: do not list objects with status TERMINATED
#    2019-06-07: separate objects specific to a region and objects common to all regions
#    2019-07-15: add tag namespaces
#    2019-07-16: change title for DNS zone as now in Networking instead of Edge Services
#    2019-10-02: add support for sub-compartments (-r option) + print full compartment name
#    2020-02-01: add support for Functions applications, Notifications and Events
#    2020-03-20: add support for email approved senders
#    2020-03-20: change location of temporary files to /tmp + check oci exists
# --------------------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 [-a] [-r] OCI_PROFILE compartment_name
    or $0 [-a] [-r] OCI_PROFILE compartment_ocid

    By default, only the objects in the region provided in the profile are listed
    If -a is provided, the objects from all active regions are listed

    If -r is provided (recursive option), objects in active sub-compartments will also be listed.

    Note: if both -a and -r are provided, -a must be first argument and -r second argument

Examples:
    $0 -a EMEAOSCf root
    $0 -r EMEAOSCf oscinternal
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
  COLOR_TITLE0="\033[95m"             # light magenta
  COLOR_TITLE1="\033[91m"             # light red
  COLOR_TITLE2="\033[32m"             # green
  COLOR_AD="\033[94m"                 # light blue
  COLOR_COMP="\033[93m"               # light yellow
  COLOR_BREAK="\033[91m"              # light red
  COLOR_NORMAL="\033[39m"
else
  COLOR_TITLE0=""
  COLOR_TITLE1=""
  COLOR_TITLE2=""
  COLOR_AD=""
  COLOR_COMP=""
  COLOR_BREAK=""
  COLOR_NORMAL=""
fi

# ---------------- functions to list objects

# ------ list objects common to all regions
list_identity_policies()
{
  local lcpid=$1
  echo -e "${COLOR_TITLE2}========== IDENTITY: Policies${COLOR_NORMAL}"
  oci --profile $PROFILE iam policy list -c $lcpid --output table --all --query 'data[].{Name:name, OCID:id, Status:"lifecycle-state"}'
}

list_networking_dns_zones()
{
  local lcpid=$1
  echo -e "${COLOR_TITLE2}========== NETWORKING: DNS zones${COLOR_NORMAL}"
  oci --profile $PROFILE dns zone list -c $lcpid --output table --all --query 'data[].{Name:name, OCID:id, Status:"lifecycle-state"}' 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show."
}

list_governance_tag_namespaces()
{
  local lcpid=$1
  echo -e "${COLOR_TITLE2}========== GOVERNANCE: Tag Namespaces${COLOR_NORMAL}"
  oci --profile $PROFILE iam tag-namespace list -c $lcpid --output table --all --query 'data[].{Name:name, OCID:id, Status:"lifecycle-state"}' 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show."
}

list_objects_common_to_all_regions()
{
  local lcptname=$1
  local lcptid=$2

  echo
  echo -e "${COLOR_TITLE0}============================ COMPARTMENT ${COLOR_COMP}${lcptname}${COLOR_TITLE0} (${COLOR_COMP}${lcptid}${COLOR_TITLE0})"
  echo -e "${COLOR_TITLE1}==================== BEGIN: objects common to all regions${COLOR_NORMAL}"

  list_networking_dns_zones $lcptid
  list_identity_policies $lcptid
  list_governance_tag_namespaces $lcptid

  echo -e "${COLOR_TITLE1}==================== END: objects common to all regions${COLOR_NORMAL}"
}

# ------ objects specific to a region
list_compute_instances()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== COMPUTE: Instances${COLOR_NORMAL}"
  oci --profile $PROFILE compute instance list -c $lcpid --region $lr --output table --all --query "data[?\"lifecycle-state\"!='TERMINATED'].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}" 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show." when only TERMINATED objects are returned
}

list_compute_custom_images()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== COMPUTE: Custom Images${COLOR_NORMAL}"
  oci --profile $PROFILE compute image list -c $lcpid --region $lr --output table --all --query 'data[?"compartment-id"!=null].{Name:"display-name", OCID:id, Status:"lifecycle-state"}' 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show."
}

list_compute_boot_volumes()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== COMPUTE: Boot volumes${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $PROFILE bv boot-volume list -c $lcpid --region $lr --output table --all --availability-domain $ad --query "data[?\"lifecycle-state\"!='TERMINATED'].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}" 2>/dev/null
    # 2>/dev/null needed to remove message "Query returned empty result, no output to show." when only TERMINATED objects are returned
  done
}

list_compute_boot_volume_backups()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== COMPUTE: Boot volume backups${COLOR_NORMAL}"
  oci --profile $PROFILE bv boot-volume-backup list -c $lcpid --region $lr --output table --all --query "data[?\"lifecycle-state\"!='TERMINATED'].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}" 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show." when only TERMINATED objects are returned
}

list_block_storage_volumes()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Block volumes${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $PROFILE bv volume list -c $lcpid --region $lr --output table --all --availability-domain $ad --query "data[?\"lifecycle-state\"!='TERMINATED'].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}" 2>/dev/null
    # 2>/dev/null needed to remove message "Query returned empty result, no output to show." when only TERMINATED objects are returned
  done
}

list_block_storage_volume_backups()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Block volume backups${COLOR_NORMAL}"
  oci --profile $PROFILE bv backup list -c $lcpid --region $lr --output table --all --query "data[?\"lifecycle-state\"!='TERMINATED'].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}" 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show." when only TERMINATED objects are returned
}

list_block_storage_volume_groups()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Volumes groups${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $PROFILE bv volume-group list -c $lcpid --region $lr --output table --all --availability-domain $ad --query "data[?\"lifecycle-state\"!='TERMINATED'].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}" 2>/dev/null
    # 2>/dev/null needed to remove message "Query returned empty result, no output to show." when only TERMINATED objects are returned
  done
}

list_block_storage_volume_group_backups()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== BLOCK STORAGE: Volumes group backups${COLOR_NORMAL}"
  oci --profile $PROFILE bv volume-group-backup list -c $lcpid --region $lr --output table --all --query "data[?\"lifecycle-state\"!='TERMINATED'].{Name:\"display-name\", OCID:id, Status:\"lifecycle-state\"}" 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show." when only TERMINATED objects are returned
}

list_object_storage_buckets()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== OBJECT STORAGE: Buckets${COLOR_NORMAL}"
  oci --profile $PROFILE os bucket list -c $lcpid --region $lr --output table --all --query 'data[].{Name:name}'
}

list_file_storage_filesystems()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== FILE STORAGE: Filesystems ${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $PROFILE fs file-system list -c $lcpid --region $lr --output table --all --availability-domain $ad --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
  done
}

list_file_storage_mount_targets()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== FILE STORAGE: Mount targets ${COLOR_NORMAL}"
  for ad in $ADS
  do
    echo -e "${COLOR_AD}== Availability-domain $ad${COLOR_NORMAL}"
    oci --profile $PROFILE fs mount-target list -c $lcpid --region $lr --output table --all --availability-domain $ad --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
  done
}

list_networking_vcns()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== NETWORKING: Virtal Cloud Networks (VCNs)${COLOR_NORMAL}"
  oci --profile $PROFILE network vcn list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_drgs()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== NETWORKING: Dynamic Routing Gateways (DRGs)${COLOR_NORMAL}"
  oci --profile $PROFILE network drg list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_cpes()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== NETWORKING: Customer Premises Equipments (CPEs)${COLOR_NORMAL}"
  oci --profile $PROFILE network cpe list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id}'
}

list_networking_ipsecs()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== NETWORKING: IPsec connections${COLOR_NORMAL}"
  oci --profile $PROFILE network ip-sec-connection list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_lbs()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== NETWORKING: Load balancers${COLOR_NORMAL}"
  oci --profile $PROFILE lb load-balancer list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_networking_public_ips()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== NETWORKING: Public IPs${COLOR_NORMAL}"
  oci --profile $PROFILE network public-ip list -c $lcpid --region $lr --scope region --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_db_systems()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== DATABASE: DB Systems${COLOR_NORMAL}"
  oci --profile $PROFILE db system list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_db_systems_backups()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== DATABASE: DB Systems backups${COLOR_NORMAL}"
  oci --profile $PROFILE db backup list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_autonomous_db()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== DATABASE: Autonomous databases (ATP/ADW)${COLOR_NORMAL}"
  oci --profile $PROFILE db autonomous-database list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_database_autonomous_backups()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== DATABASE: Autonomous databases backups${COLOR_NORMAL}"
  oci --profile $PROFILE db autonomous-database-backup list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_resource_manager_stacks()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== RESOURCE MANAGER: Stacks${COLOR_NORMAL}"
  oci --profile $PROFILE resource-manager stack list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_email_delivery_approved_senders()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== EMAIL DELIVERY: Approved senders${COLOR_NORMAL}"
  oci --profile $PROFILE email sender list -c $lcpid --region $lr --output table --all --query 'data[].{Email:"email-address", Status:"lifecycle-state"}' 2>/dev/null
  # 2>/dev/null needed to remove message "Query returned empty result, no output to show."
}

list_application_integration_notifications_topics()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== APPLICATION INTEGRATION: Notifications topics${COLOR_NORMAL}"
  oci --profile $PROFILE ons topic list -c $lcpid --region $lr --output table --all --query 'data[].{Name:name, OCID:"topic-id", Status:"lifecycle-state"}'
}

list_application_integration_events_rules()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== APPLICATION INTEGRATION: Events rules${COLOR_NORMAL}"
  oci --profile $PROFILE events rule list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}'
}

list_application_integration_cec_instances()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== APPLICATION INTEGRATION: Content and Experience instances${COLOR_NORMAL}"
  oci --profile $PROFILE oce oce-instance list -c $lcpid --region $lr --output table --query 'data[].{Name:name, OCID:id, Status:"lifecycle-state"}'
  # --all option documented but not supported by OCI CLI 2.7.0
  # oci --profile $PROFILE oce oce-instance list -c $lcpid --region $lr --output table --all --query 'data[].{Name:name, OCID:id, Status:"lifecycle-state"}'
}

list_developer_services_oke()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== DEVELOPER SERVICES: Container clusters (OKE)${COLOR_NORMAL}"
  oci --profile $PROFILE ce cluster list -c $lcpid --region $lr --output table --all --query 'data[].{Name:name, OCID:id, Status:"lifecycle-state"}'
}

list_developer_services_functions()
{
  local lr=$1
  local lcpid=$2
  echo -e "${COLOR_TITLE2}========== DEVELOPER SERVICES: Functions applications${COLOR_NORMAL}"
  oci --profile $PROFILE fn application list -c $lcpid --region $lr --output table --all --query 'data[].{Name:"display-name", OCID:id, Status:"lifecycle-state"}' 2>/dev/null
  # 2>/dev/null needed to remove message "Authorization failed or requested resource not found" when no functions applications are present 
}

# -- list region specific objects
list_region_specific_objects()
{
  local lregion=$1
  local lcompid=$2

  # Get list of availability domains
  ADS=`oci --profile $PROFILE --region $lregion iam availability-domain list|jq '.data[].name'|sed 's#"##g'`

  echo -e "${COLOR_TITLE1}==================== BEGIN: objects specific to region ${COLOR_COMP}${lregion}${COLOR_NORMAL}"

  list_compute_instances $lregion $lcompid
  list_compute_custom_images $lregion $lcompid
  list_compute_boot_volumes $lregion $lcompid
  list_compute_boot_volume_backups $lregion $lcompid
  list_block_storage_volumes $lregion $lcompid
  list_block_storage_volume_backups $lregion $lcompid
  list_block_storage_volume_groups $lregion $lcompid
  list_block_storage_volume_group_backups $lregion $lcompid
  list_object_storage_buckets $lregion $lcompid
  list_file_storage_filesystems $lregion $lcompid
  list_file_storage_mount_targets $lregion $lcompid
  list_networking_vcns $lregion $lcompid
  list_networking_drgs $lregion $lcompid
  list_networking_cpes $lregion $lcompid
  list_networking_ipsecs $lregion $lcompid
  list_networking_lbs $lregion $lcompid
  list_networking_public_ips $lregion $lcompid
  list_database_db_systems $lregion $lcompid
  list_database_db_systems_backups $lregion $lcompid
  list_database_autonomous_db $lregion $lcompid
  list_database_autonomous_backups $lregion $lcompid
  list_resource_manager_stacks $lregion $lcompid
  list_email_delivery_approved_senders $lregion $lcompid
  list_application_integration_notifications_topics $lregion $lcompid
  list_application_integration_events_rules $lregion $lcompid
  list_application_integration_cec_instances $lregion $lcompid
  list_developer_services_oke $lregion $lcompid
  list_developer_services_functions $lregion $lcompid

  echo -e "${COLOR_TITLE1}==================== END: objects specific to region ${COLOR_COMP}${lregion}${COLOR_NORMAL}"
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

get_comp_full_name_from_comp_id()
{
  local id=$1
  echo $id | grep "ocid1.tenancy.oc1" > /dev/null 2>&1
  if [ $? -eq 0 ]
  then
    echo root
  else
    short_name=`oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --query "data [?\"id\" == '$id'].{name:name}" |jq -r '.[].name'`
    parent_id=`oci --profile $PROFILE iam compartment list --compartment-id-in-subtree true --all --query "data [?\"id\" == '$id'].{parentid:\"compartment-id\"}" |jq -r '.[].parentid'`
    parent_full_name=`get_comp_full_name_from_comp_id $parent_id`
    echo "${parent_full_name}/${short_name}"
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
  exit 99
}

do_it_in_sub_compt()
{
  local lregion_list=$1
  local lcompid=$2
  local lcptid
  local lcptid_list
  local lcptname
  local lregion

  # get the list of ACTIVE direct sub-compartments.
  lcptid_list=`oci --profile $PROFILE iam compartment list -c $lcompid --all --query "data [?\"lifecycle-state\" == 'ACTIVE'].{id:id}" |jq -r '.[].id'`
  if [ "$lcptid_list" == "" ]; then return; fi

  for lcptid in $lcptid_list
  do 
    lcptname=`get_comp_full_name_from_comp_id $lcptid`
    echo
    list_objects_common_to_all_regions $lcptname $lcptid
    for lregion in $lregion_list
    do
      list_region_specific_objects $lregion $lcptid
    done 
    do_it_in_sub_compt "$lregion_list" $lcptid
  done
}  

# ---------------- main

OCI_CONFIG_FILE=~/.oci/config
TMP_FILE=/tmp/tmp_$$
TMP_FILE_COMPID_LIST=${TMP_FILE}_compid_list
TMP_FILE_COMPNAME_LIST=${TMP_FILE}_compname_list
TMP_PROFILE=/tmp/tmp_$$_profile

# -- Check usage

ALL_REGIONS=false
INCLUDE_SUB_CPT=false

if [ $# -ne 2 ] && [ $# -ne 3 ] && [ $# -ne 4 ]; then usage; fi

if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then usage; fi
if [ "$2" == "-h" ] || [ "$2" == "--help" ]; then usage; fi
if [ "$3" == "-h" ] || [ "$3" == "--help" ]; then usage; fi
if [ "$4" == "-h" ] || [ "$4" == "--help" ]; then usage; fi

case $# in
  2) PROFILE=$1;  COMP=$2;  
     ;;
  3) PROFILE=$2;  COMP=$3;  
     if [ "$1" == "-a" ]; then ALL_REGIONS=true;
       elif [ "$1" == "-r" ]; then INCLUDE_SUB_CPT=true; 
       else usage; fi
     ;;
  4) PROFILE=$3;  COMP=$4;  
     if [ "$1" == "-a" ]; then ALL_REGIONS=true; else usage; fi
     if [ "$2" == "-r" ]; then INCLUDE_SUB_CPT=true; else usage; fi
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
  COMPID=`get_comp_id_from_comp_name $COMP`
  COMPNAME=`get_comp_full_name_from_comp_id $COMPID`
else
  # -- if not, check if it is an existing compartment OCID
  grep "^$COMP" $TMP_FILE_COMPID_LIST > /dev/null 2>&1
  if [ $? -eq 0 ]
  then
    COMPID=$COMP
    COMPNAME=`get_comp_full_name_from_comp_id $COMPID`
  else
    echo "ERROR: $COMP is not an existing compartment name or compartment id in this tenancy !"
    cleanup; exit 4
  fi
fi

# -- list objects in compartment
if [ $ALL_REGIONS == false ]
then
  # Get the current region from the profile
  egrep "^\[|^region" ${OCI_CONFIG_FILE} | fgrep -A 1 "[${PROFILE}]" |grep "^region" > $TMP_FILE 2>&1
  if [ $? -ne 0 ]; then echo "ERROR: region not found in OCI config file $OCI_CONFIG_FILE for profile $PROFILE !"; cleanup; exit 5; fi
  CURRENT_REGION=`awk -F'=' '{ print $2 }' $TMP_FILE | sed 's# ##g'`

  list_objects_common_to_all_regions $COMPNAME $COMPID
  list_region_specific_objects $CURRENT_REGION $COMPID

  if [ $INCLUDE_SUB_CPT == true ]; then do_it_in_sub_compt $CURRENT_REGION $COMPID; fi
else
  REGIONS_LIST=`get_all_active_regions`

  echo -e "${COLOR_TITLE1}==================== List of active regions in tenancy${COLOR_NORMAL}"
  for region in $REGIONS_LIST; do echo $region; done

  list_objects_common_to_all_regions $COMPNAME $COMPID

  for region in $REGIONS_LIST
  do
    list_region_specific_objects $region $COMPID
  done

  if [ $INCLUDE_SUB_CPT == true ]; then do_it_in_sub_compt "$REGIONS_LIST" $COMPID; fi
fi

# -- Normal completion of script without errors
cleanup
exit 0