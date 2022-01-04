#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script lists all objects (detailed list below) in a given compartment in a region or all active regions using OCI Python SDK
#
# Supported objects:
# - COMPUTE                : compute instances, dedicated virtual machines hosts, instance configurations, instance pools
#                            custom images, boot volumes, boot volumes backups
# - BLOCK STORAGE          : block volumes, block volumes backups, volume groups, volume groups backups
# - OBJECT STORAGE         : buckets
# - FILE STORAGE           : file systems, mount targets
# - NETWORKING             : VCN, DRG, CPE, IPsec connection, LB, public IPs, DNS zones (common to all regions)
# - DATABASE               : DB Systems, DB Systems backups, Autonomous DB, Autonomous DB backups, NoSQL DB tables
# - DATA SAFE              : Private endpoints
# - RESOURCE MANAGER       : Stacks
# - EMAIL DELIVERY         : Approved senders, Suppressions list (list can only exists in root compartment)
# - APPLICATION INTEGRATION: Notifications, Events, Content and Experience
# - DEVELOPER SERVICES     : Container clusters (OKE), Functions applications
# - IDENTITY               : Policies (common to all regions)
# - SECURITY               : Vaults
# - GOVERNANCE             : Tags namespaces (common to all regions)
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-01-02: Initial Version
#    2020-03-24: add support for email approved senders, email suppressions list
#    2020-03-24: add support for compute instance configurations, compute instance pools, compute dedicated vm hosts
#    2020-03-24: fix bug for root compartment
#    2020-03-25: add support for NoSQL database tables
#    2020-06-22: add support for Data Safe private endpoints
#    2020-07-07: fix minor bug for functions applications
#    2020-08-10: add support for Security Vaults
#    2022-01-03: use argparse to parse arguments
#    2022-01-04: add --no_color option
# ---------------------------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse

# -------- colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLOR_TITLE0="\033[95m"             # light magenta
COLOR_TITLE1="\033[91m"             # light red
COLOR_TITLE2="\033[32m"             # green
COLOR_AD="\033[94m"                 # light blue
COLOR_COMP="\033[93m"               # light yellow
COLOR_BREAK="\033[91m"              # light red
COLOR_NORMAL="\033[39m"

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-nc] [-a] [-r] -p OCI_PROFILE -c compartment_ocid".format(sys.argv[0]))
    print ("    or {} [-nc] [-a] [-r] -p OCI_PROFILE -c compartment_name".format(sys.argv[0]))
    print ("")
    print ("    By default, only the objects in the region provided in the profile are listed")
    print ("    If -a is provided, the objects from all subscribed regions are listed")
    print ("    If -r is provided (recursive option), objects in active sub-compartments will also be listed")
    print ("")
    print ("note: OCI_PROFILE must exist in {} file (see example below)".format(configfile))
    print ("")
    print ("[EMEAOSCf]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# ---- Disable colored output
def disable_colored_output():
    global COLOR_TITLE0
    global COLOR_TITLE1
    global COLOR_TITLE2
    global COLOR_AD
    global COLOR_COMP
    global COLOR_BREAK
    global COLOR_NORMAL

    COLOR_TITLE0 = ""
    COLOR_TITLE1 = ""
    COLOR_TITLE2 = ""
    COLOR_AD     = ""
    COLOR_COMP   = ""
    COLOR_BREAK  = ""
    COLOR_NORMAL = ""

# ---- List objects common to all regions
def list_networking_dns_zones(lcpt_ocid):
    print (COLOR_TITLE2+"========== NETWORKING: DNS zones "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(DnsClient.list_zones,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for zone in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(zone.id, zone.name, zone.lifecycle_state))

def list_identity_policies(lcpt_ocid):
    print (COLOR_TITLE2+"========== IDENTITY: Policies "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(IdentityClient.list_policies,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for policy in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(policy.id, policy.name, policy.lifecycle_state))

def list_governance_tag_namespaces(lcpt_ocid):
    print (COLOR_TITLE2+"========== GOVERNANCE: Tag Namespaces "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(IdentityClient.list_tag_namespaces,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for tag_namespace in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(tag_namespace.id, tag_namespace.name, tag_namespace.lifecycle_state))

def list_objects_common_to_all_regions(cpt_ocid,cpt_name):
    global DnsClient

    print (COLOR_TITLE1+"==================== BEGIN: objects common to all regions in compartment "+COLOR_COMP+"{} ".format(cpt_name)+COLOR_NORMAL)
    
    # DNS
    DnsClient = oci.dns.DnsClient(config)
    list_networking_dns_zones (cpt_ocid)

    # Identity
    list_identity_policies (cpt_ocid)
    list_governance_tag_namespaces (cpt_ocid)

    print (COLOR_TITLE1+"==================== END: objects common to all regions in compartment "+COLOR_COMP+"{} ".format(cpt_name)+COLOR_NORMAL)

    # if requested, also process active sub-compartments
    if (include_sub_cpt):
        response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, cpt_ocid)
        sub_compartments = response.data
        for sub_compartment in sub_compartments:
            if (sub_compartment.lifecycle_state == "ACTIVE"):
                list_objects_common_to_all_regions(sub_compartment.id,sub_compartment.name)

# ---- List objects specific to a region

# -- Compute
def list_compute_instances (lcpt_ocid):
    print (COLOR_TITLE2+"========== COMPUTE: Instances "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ComputeClient.list_instances,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for instance in response.data:
            print ('{0:100s} {1:20s} {2:20s} {3:10s}'.format(instance.id, instance.display_name, instance.shape,  instance.lifecycle_state))

def list_compute_dedicated_vm_hosts (lcpt_ocid):
    print (COLOR_TITLE2+"========== COMPUTE: Dedicated virtual machines hosts "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ComputeClient.list_dedicated_vm_hosts,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for host in response.data:
            print ('{0:100s} {1:20s} {2:20s} {3:10s}'.format(host.id, host.display_name, host.dedicated_vm_host_shape, host.lifecycle_state))

def list_compute_instance_configurations (lcpt_ocid):
    print (COLOR_TITLE2+"========== COMPUTE: Instance Configurations "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ComputeManagementClient.list_instance_configurations,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for configuration in response.data:
            print ('{0:100s} {1:20s}'.format(configuration.id, configuration.display_name))

def list_compute_instance_pools (lcpt_ocid):
    print (COLOR_TITLE2+"========== COMPUTE: Instance Pools "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ComputeManagementClient.list_instance_pools,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for pool in response.data:
            print ('{0:100s} {1:20s} {2:10s}'.format(pool.id, pool.display_name, pool.lifecycle_state))

def list_compute_custom_images(lcpt_ocid):
    print (COLOR_TITLE2+"========== COMPUTE: Images "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ComputeClient.list_images,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for image in response.data:
            print ('{0:100s} {1:s}'.format(image.id, image.display_name))

def list_compute_boot_volumes(lcpt_ocid):
    print (COLOR_TITLE2+"========== COMPUTE: Boot Volumes "+COLOR_NORMAL)
    for ad in ads:
        print (COLOR_AD+"== Availability-domain {:s}".format(ad.name)+COLOR_NORMAL)

        response = oci.pagination.list_call_get_all_results(BlockstorageClient.list_boot_volumes,availability_domain=ad.name,compartment_id=lcpt_ocid)
        if len(response.data) > 0:
            for bootvol in response.data:
                print ('{0:100s} {1:30s} {2:10s}'.format(bootvol.id, bootvol.display_name, bootvol.lifecycle_state))


def list_compute_boot_volume_backups(lcpt_ocid):
    print (COLOR_TITLE2+"========== COMPUTE: Boot Volume Backups "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(BlockstorageClient.list_boot_volume_backups,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for bootvol_backup in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(bootvol_backup.id, bootvol_backup.display_name, bootvol_backup.lifecycle_state))

# -- Block Storage
def list_block_storage_volumes(lcpt_ocid):
    print (COLOR_TITLE2+"========== BLOCK STORAGE: Block volumes "+COLOR_NORMAL)
    for ad in ads:
        print (COLOR_AD+"== Availability-domain {:s}".format(ad.name)+COLOR_NORMAL)

        response = oci.pagination.list_call_get_all_results(BlockstorageClient.list_volumes,availability_domain=ad.name,compartment_id=lcpt_ocid)
        if len(response.data) > 0:
            for bkvol in response.data:
                print ('{0:100s} {1:30s} {2:10s}'.format(bkvol.id, bkvol.display_name, bkvol.lifecycle_state))

def list_block_storage_volume_backups(lcpt_ocid):
    print (COLOR_TITLE2+"========== BLOCK STORAGE: Block volume backups "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(BlockstorageClient.list_volume_backups,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for bkvol_backup in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(bkvol_backup.id, bkvol_backup.display_name, bkvol_backup.lifecycle_state))

def list_block_storage_volume_groups(lcpt_ocid):
    print (COLOR_TITLE2+"========== BLOCK STORAGE: Volumes groups "+COLOR_NORMAL)
    for ad in ads:
        print (COLOR_AD+"== Availability-domain {:s}".format(ad.name)+COLOR_NORMAL)

        response = oci.pagination.list_call_get_all_results(BlockstorageClient.list_volume_groups,availability_domain=ad.name,compartment_id=lcpt_ocid)
        if len(response.data) > 0:
            for vg in response.data:
                print ('{0:100s} {1:30s} {2:10s}'.format(vg.id, vg.display_name, vg.lifecycle_state))

def list_block_storage_volume_group_backups(lcpt_ocid):
    print (COLOR_TITLE2+"========== BLOCK STORAGE: Volumes group backups "+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(BlockstorageClient.list_volume_group_backups,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for vg_backup in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(vg_backup.id, vg_backup.display_name, vg_backup.lifecycle_state))

# -- Object Storage
def list_object_storage_buckets(lcpt_ocid):
    namespace = ObjectStorageClient.get_namespace().data
    print (COLOR_TITLE2+"========== OBJECT STORAGE: Buckets (namespace {})".format(namespace)+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ObjectStorageClient.list_buckets,namespace_name=namespace,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for bucket in response.data:
            print ('{0:s}'.format(bucket.name))

# -- File Storage
def list_file_storage_filesystems(lcpt_ocid):
    print (COLOR_TITLE2+"========== FILE STORAGE: Filesystems "+COLOR_NORMAL)
    for ad in ads:
        print (COLOR_AD+"== Availability-domain {:s}".format(ad.name)+COLOR_NORMAL)

        response = oci.pagination.list_call_get_all_results(FileStorageClient.list_file_systems,availability_domain=ad.name,compartment_id=lcpt_ocid)
        if len(response.data) > 0:
            for fs in response.data:
                print ('{0:100s} {1:30s} {2:10s}'.format(fs.id, fs.display_name, fs.lifecycle_state))

def list_file_storage_mount_targets(lcpt_ocid):
    print (COLOR_TITLE2+"========== FILE STORAGE: Mount targets "+COLOR_NORMAL)
    for ad in ads:
        print (COLOR_AD+"== Availability-domain {:s}".format(ad.name)+COLOR_NORMAL)

        response = oci.pagination.list_call_get_all_results(FileStorageClient.list_mount_targets,availability_domain=ad.name,compartment_id=lcpt_ocid)
        if len(response.data) > 0:
            for mt in response.data:
                print ('{0:100s} {1:30s} {2:10s}'.format(mt.id, mt.display_name, mt.lifecycle_state))

# -- Networking
def list_networking_vcns(lcpt_ocid):
    print (COLOR_TITLE2+"========== NETWORKING: Virtal Cloud Networks (VCNs)"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(VirtualNetworkClient.list_vcns,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for vcn in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(vcn.id, vcn.display_name, vcn.lifecycle_state))

def list_networking_drgs(lcpt_ocid):
    print (COLOR_TITLE2+"========== NETWORKING: Dynamic Routing Gateways (DRGs)"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(VirtualNetworkClient.list_drgs,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for drg in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(drg.id, drg.display_name, drg.lifecycle_state))

def list_networking_cpes(lcpt_ocid):
    print (COLOR_TITLE2+"========== NETWORKING: Customer Premises Equipments (CPEs)"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(VirtualNetworkClient.list_cpes,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for cpe in response.data:
            print ('{0:100s} {1:30s}'.format(cpe.id, cpe.display_name))

def list_networking_ipsecs(lcpt_ocid):
    print (COLOR_TITLE2+"========== NETWORKING: IPsec connections"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(VirtualNetworkClient.list_ip_sec_connections,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for ipsec in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(ipsec.id, ipsec.display_name, ipsec.lifecycle_state))

def list_networking_lbs(lcpt_ocid):
    print (COLOR_TITLE2+"========== NETWORKING: Load balancers"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(LoadBalancerClient.list_load_balancers,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for lb in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(lb.id, lb.display_name, lb.lifecycle_state))

def list_networking_public_ips(lcpt_ocid):
    print (COLOR_TITLE2+"========== NETWORKING: Reserved Public IPs"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(VirtualNetworkClient.list_public_ips,scope="REGION",lifetime="RESERVED",compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for ip in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(ip.id, ip.display_name, ip.lifecycle_state))

# -- Database
def list_database_db_systems(lcpt_ocid):
    print (COLOR_TITLE2+"========== DATABASE: DB Systems"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(DatabaseClient.list_db_systems,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for dbs in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(dbs.id, dbs.display_name, dbs.lifecycle_state))

def list_database_db_systems_backups(lcpt_ocid):
    print (COLOR_TITLE2+"========== DATABASE: DB Systems backups"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(DatabaseClient.list_backups,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for dbs_backup in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(dbs_backup.id, dbs_backup.display_name, dbs_backup.lifecycle_state))

def list_database_autonomous_db(lcpt_ocid):
    print (COLOR_TITLE2+"========== DATABASE: Autonomous databases (ATP/ADW)"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(DatabaseClient.list_autonomous_databases,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for adb in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(adb.id, adb.display_name, adb.lifecycle_state))

def list_database_autonomous_backups(lcpt_ocid):
    print (COLOR_TITLE2+"========== DATABASE: Autonomous databases backups"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(DatabaseClient.list_autonomous_database_backups,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for adb_backup in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(adb_backup.id, adb_backup.display_name, adb_backup.lifecycle_state))

def list_database_nosql_database_tables(lcpt_ocid):
    print (COLOR_TITLE2+"========== DATABASE: NoSQL database tables"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(NoSQLClient.list_tables,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for table in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(table.id, table.name, table.lifecycle_state))

# -- Data Safe
def list_data_safe_private_endpoints(lcpt_ocid):
    print (COLOR_TITLE2+"========== DATA SAFE: Private endpoints"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(DataSafeClient.list_data_safe_private_endpoints,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for endpt in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(endpt.id, endpt.display_name, endpt.lifecycle_state))

# -- Resource manager
def list_resource_manager_stacks(lcpt_ocid):
    print (COLOR_TITLE2+"========== RESOURCE MANAGER: Stacks"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ResourceManagerClient.list_stacks,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for stack in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(stack.id, stack.display_name, stack.lifecycle_state))

# -- Email delivery
def list_email_delivery_approved_senders(lcpt_ocid):
    print (COLOR_TITLE2+"========== EMAIL DELIVERY: Approved senders"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(EmailClient.list_senders,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for sender in response.data:
            print ('{0:30s} {1:10s}'.format(sender.email_address, sender.lifecycle_state))

def list_email_delivery_suppressions_list(lcpt_ocid):
    # Suppressions list can only exists in the root compartment
    if lcpt_ocid == RootCompartmentID:
        print (COLOR_TITLE2+"========== EMAIL DELIVERY: Suppressions list"+COLOR_NORMAL)
        response = oci.pagination.list_call_get_all_results(EmailClient.list_suppressions,compartment_id=lcpt_ocid)
        if len(response.data) > 0:
            for suppression in response.data:
                print ('{0:30s}'.format(suppression.email_address))

# -- Application integration
def list_application_integration_notifications_topics (lcpt_ocid):
    print (COLOR_TITLE2+"========== APPLICATION INTEGRATION: Notifications topics"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(NotificationControlPlaneClient.list_topics,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for topic in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(topic.topic_id, topic.name, topic.lifecycle_state))

def list_application_integration_events_rules (lcpt_ocid):
    print (COLOR_TITLE2+"========== APPLICATION INTEGRATION: Events rules"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(EventsClient.list_rules,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for rule in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(rule.id, rule.display_name, rule.lifecycle_state))

def list_application_integration_cec_instances (lcpt_ocid):
    print (COLOR_TITLE2+"========== APPLICATION INTEGRATION: Content and Experience instances"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(OceInstanceClient.list_oce_instances,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for instance in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(instance.id, instance.name, instance.lifecycle_state))

# -- Developer services
def list_developer_services_oke(lcpt_ocid):
    print (COLOR_TITLE2+"========== DEVELOPER SERVICES: Container clusters (OKE)"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(ContainerEngineClient.list_clusters,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for cluster in response.data:
            print ('{0:100s} {1:30s} {2:10s}'.format(cluster.id, cluster.name, cluster.lifecycle_state))

def list_developer_services_functions(lcpt_ocid):
    print (COLOR_TITLE2+"========== DEVELOPER SERVICES: Functions applications"+COLOR_NORMAL)
    #  Error "Authorization failed or requested resource not found" when no functions applications are present 
    try:
        response = oci.pagination.list_call_get_all_results(FunctionsManagementClient.list_applications,compartment_id=lcpt_ocid)
        if len(response.data) > 0:
            for app in response.data:
                print ('{0:100s} {1:30s} {2:10s}'.format(app.id, app.display_name, app.lifecycle_state))
    except:
        pass

# -- Security
def list_security_vaults(lcpt_ocid):
    print (COLOR_TITLE2+"========== SECURITY: Vaults"+COLOR_NORMAL)
    response = oci.pagination.list_call_get_all_results(VaultsClient.list_secrets,compartment_id=lcpt_ocid)
    if len(response.data) > 0:
        for secret in response.data:
            print ('{0:100s} {1:100s} {2:30s} {3:10s}'.format(secret.vault_id, secret.id, secret.secret_name, secret.lifecycle_state))

# -- List region specific objects
def list_region_specific_objects (cpt_ocid,cpt_name):
    global ComputeClient
    global ComputeManagementClient
    global BlockstorageClient
    global ObjectStorageClient
    global FileStorageClient
    global VirtualNetworkClient
    global LoadBalancerClient
    global DatabaseClient
    global NoSQLClient
    global DataSafeClient
    global ResourceManagerClient
    global EmailClient
    global NotificationControlPlaneClient
    global EventsClient
    global OceInstanceClient
    global ContainerEngineClient
    global FunctionsManagementClient
    global VaultsClient

    print (COLOR_TITLE1+"==================== BEGIN: objects specific to region "+COLOR_COMP+config["region"]+COLOR_TITLE1+" in compartment "+COLOR_COMP+"{} ".format(cpt_name)+COLOR_NORMAL)

    # Compute
    ComputeClient = oci.core.ComputeClient(config)
    ComputeManagementClient = oci.core.ComputeManagementClient(config)
    list_compute_instances (cpt_ocid)
    list_compute_dedicated_vm_hosts (cpt_ocid)
    list_compute_instance_configurations (cpt_ocid)
    list_compute_instance_pools (cpt_ocid)
    list_compute_custom_images (cpt_ocid)
 
    # Block Storage
    BlockstorageClient = oci.core.BlockstorageClient(config)
    list_compute_boot_volumes (cpt_ocid)
    list_compute_boot_volume_backups (cpt_ocid)
    list_block_storage_volumes (cpt_ocid)
    list_block_storage_volume_backups (cpt_ocid)
    list_block_storage_volume_groups (cpt_ocid)
    list_block_storage_volume_group_backups (cpt_ocid)

    # Object Storage
    ObjectStorageClient = oci.object_storage.ObjectStorageClient(config)
    list_object_storage_buckets (cpt_ocid)

    # File Storage
    FileStorageClient = oci.file_storage.FileStorageClient(config)
    list_file_storage_filesystems (cpt_ocid)
    list_file_storage_mount_targets (cpt_ocid)

    # Networking
    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)
    LoadBalancerClient = oci.load_balancer.LoadBalancerClient(config)
    list_networking_vcns (cpt_ocid)
    list_networking_drgs (cpt_ocid)
    list_networking_cpes (cpt_ocid)
    list_networking_ipsecs (cpt_ocid)
    list_networking_lbs (cpt_ocid)
    list_networking_public_ips (cpt_ocid)

    # Database
    DatabaseClient = oci.database.DatabaseClient(config)
    list_database_db_systems (cpt_ocid)
    list_database_db_systems_backups (cpt_ocid)
    list_database_autonomous_db (cpt_ocid)
    list_database_autonomous_backups (cpt_ocid)
    NoSQLClient = oci.nosql.NosqlClient(config)
    list_database_nosql_database_tables (cpt_ocid)

    # Data Safe
    DataSafeClient = oci.data_safe.DataSafeClient(config)
    list_data_safe_private_endpoints (cpt_ocid)

    # Resource Manager
    ResourceManagerClient = oci.resource_manager.ResourceManagerClient(config)
    list_resource_manager_stacks (cpt_ocid)
    
    # Email delivery
    EmailClient = oci.email.EmailClient(config)
    list_email_delivery_approved_senders (cpt_ocid)
    list_email_delivery_suppressions_list (cpt_ocid)

    # Application integration
    NotificationControlPlaneClient = oci.ons.NotificationControlPlaneClient(config)
    list_application_integration_notifications_topics (cpt_ocid)
    EventsClient = oci.events.EventsClient(config)
    list_application_integration_events_rules (cpt_ocid) 
    OceInstanceClient = oci.oce.OceInstanceClient(config)
    list_application_integration_cec_instances (cpt_ocid)

    # Developer Services
    ContainerEngineClient = oci.container_engine.ContainerEngineClient(config)
    list_developer_services_oke (cpt_ocid)
    FunctionsManagementClient = oci.functions.FunctionsManagementClient(config)
    list_developer_services_functions (cpt_ocid)

    # Security
    VaultsClient = oci.vault.VaultsClient(config)  
    list_security_vaults (cpt_ocid)

    print (COLOR_TITLE1+"==================== END: objects specific to region "+COLOR_COMP+config["region"]+COLOR_TITLE1+" in compartment "+COLOR_COMP+"{} ".format(cpt_name)+COLOR_NORMAL)

    # if requested, also process active sub-compartments
    if (include_sub_cpt):
        response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, cpt_ocid)
        sub_compartments = response.data
        for sub_compartment in sub_compartments:
            if (sub_compartment.lifecycle_state == "ACTIVE"):
                list_region_specific_objects(sub_compartment.id,sub_compartment.name)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List resources in an OCI compartment")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-c", "--compartment", help="Compartment name or compartment OCID", required=True)
parser.add_argument("-r", "--recursive", help="Include sub-compartments", action="store_true")
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
parser.add_argument("-nc", "--no_color", help="Disable colored output", action="store_true")
args = parser.parse_args()

profile         = args.profile
cpt             = args.compartment
include_sub_cpt = args.recursive
all_regions     = args.all_regions
if args.nocolor:
  disable_colored_output()

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- find compartment name and compartment id
if (cpt == "root") or (cpt == RootCompartmentID):
    initial_cpt_name = "root"
    initial_cpt_ocid = RootCompartmentID
else:
    response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
    compartments = response.data
    cpt_exist = False
    for compartment in compartments:  
        if (cpt == compartment.id) or (cpt == compartment.name):
            initial_cpt_ocid = compartment.id
            initial_cpt_name = compartment.name
            cpt_exist = True
    if not(cpt_exist):
        print ("ERROR 03: compartment '{}' does not exist !".format(cpt))
        exit (3) 

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- get list of ADs
response = oci.pagination.list_call_get_all_results(IdentityClient.list_availability_domains, RootCompartmentID)
ads = response.data

# -- list objects
if (all_regions):
    print (COLOR_TITLE1+"==================== List of subscribed regions in tenancy "+COLOR_NORMAL)
    for region in regions:
        print (region.region_name)

list_objects_common_to_all_regions(initial_cpt_ocid,initial_cpt_name)

if not(all_regions):
    list_region_specific_objects(initial_cpt_ocid,initial_cpt_name)
else:
    for region in regions:
        config["region"]=region.region_name
        list_region_specific_objects(initial_cpt_ocid,initial_cpt_name)

# -- the end
exit (0)
