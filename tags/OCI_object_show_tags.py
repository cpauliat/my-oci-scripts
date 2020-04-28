#!/usr/bin/env python3

# ----------------------------------------------------------------------------------------------------------
# This script show defined tags for an OCI resource/object
#
# Supported resource types:
# - COMPUTE            : instance, custom image, boot volume
# - BLOCK STORAGE      : block volume, block volume backup
# - DATABASE           : dbsystem, autonomous database
# - OBJECT STORAGE     : bucket
# - NETWORKING         : vcn, subnet, route table, Internet gateway, DRG, network security group
#                        security list, DHCP options, LPG, NAT gateway, service gateway
# 
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-28: Initial Version
#
# TO DO: add support for more resource types
# ----------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} OCI_PROFILE object_ocid".format(sys.argv[0]))
    print ("")
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

# ---- specific functions to show tags for objects

# -- compute
def show_tags_from_compute_instance(inst_id):
    global config

    ComputeClient = oci.core.ComputeClient(config)

    try:
        response = ComputeClient.get_instance(inst_id)
        instance = response.data
        print (instance.defined_tags)
    except:
        print ("ERROR 03: instance with OCID '{}' not found !".format(inst_id))
        exit (3)

def show_tags_from_custom_image(image_id):
    global config

    ComputeClient = oci.core.ComputeClient(config)

    try:
        response = ComputeClient.get_image(image_id)
        image = response.data
        print (image.defined_tags)
    except:
        print ("ERROR 03: custom image with OCID '{}' not found !".format(image_id))
        exit (3)

def show_tags_from_boot_volume(bootvol_id):
    global config

    BlockstorageClient = oci.core.BlockstorageClient(config)

    try:
        response = BlockstorageClient.get_boot_volume(bootvol_id)
        bootvol = response.data
        print (bootvol.defined_tags)
    except:
        print ("ERROR 03: boot volume with OCID '{}' not found !".format(bootvol_id))
        exit (3)

# -- block storage
def show_tags_from_block_volume(bkvol_id):
    global config

    BlockstorageClient = oci.core.BlockstorageClient(config)

    try:
        response = BlockstorageClient.get_volume(bkvol_id)
        bkvol = response.data
        print (bkvol.defined_tags)
    except:
        print ("ERROR 03: block volume with OCID '{}' not found !".format(bkvol_id))
        exit (3)

def show_tags_from_block_volume_backup(bkvolbkup_id):
    global config

    BlockstorageClient = oci.core.BlockstorageClient(config)

    try:
        response = BlockstorageClient.get_volume_backup(bkvolbkup_id)
        bkvol_bkup = response.data
        print (bkvol_bkup.defined_tags)
    except:
        print ("ERROR 03: block volume backup with OCID '{}' not found !".format(bkvolbkup_id))
        exit (3)

# -- database
def show_tags_from_db_system(dbs_id):
    global config

    DatabaseClient = oci.database.DatabaseClient(config)

    try:
        response = DatabaseClient.get_db_system(dbs_id)
        dbs = response.data
        print (dbs.defined_tags)
    except:
        print ("ERROR 03: db system with OCID '{}' not found !".format(dbs_id))
        exit (3)

def show_tags_from_autonomous_db(adb_id):
    global config

    DatabaseClient = oci.database.DatabaseClient(config)

    try:
        response = DatabaseClient.get_autonomous_database(adb_id)
        adb = response.data
        print (adb.defined_tags)
    except:
        print ("ERROR 03: Autonomous DB with OCID '{}' not found !".format(adb_id))
        exit (3)

# -- object storage     # DOES NOT WORK
def show_tags_from_bucket(bucket_id):
    global config
    bucket_name = "HOW-TO-GET-IT-FROM-BUCKET-ID-?"

    ObjectStorageClient = oci.object_storage.ObjectStorageClient(config)

    # Get namespace
    response = ObjectStorageClient.get_namespace()
    namespace = response.data

    try:
        response = ObjectStorageClient.get_bucket(namespace, bucket_name)
        bucket = response.data
        print (bucket.defined_tags)
    except:
        print ("ERROR 03: Bucket with OCID '{}' not found !".format(bucket_id))
        exit (3)

# -- networking
def show_tags_from_vcn(vcn_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_vcn(vcn_id)
        vcn = response.data
        print (vcn.defined_tags)
    except:
        print ("ERROR 03: VCN with OCID '{}' not found !".format(vcn_id))
        exit (3)

def show_tags_from_subnet(subnet_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_subnet(subnet_id)
        subnet = response.data
        print (subnet.defined_tags)
    except:
        print ("ERROR 03: Subnet with OCID '{}' not found !".format(subnet_id))
        exit (3)

def show_tags_from_route_table(rt_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_route_table(rt_id)
        rt = response.data
        print (rt.defined_tags)
    except:
        print ("ERROR 03: Route table with OCID '{}' not found !".format(rt_id))
        exit (3)

def show_tags_from_internet_gateway(ig_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_internet_gateway(ig_id)
        ig = response.data
        print (ig.defined_tags)
    except:
        print ("ERROR 03: Internet gateway with OCID '{}' not found !".format(ig_id))
        exit (3)

def show_tags_from_dynamic_routing_gateway(drg_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_drg(drg_id)
        drg = response.data
        print (drg.defined_tags)
    except:
        print ("ERROR 03: Dynamic routing gateway with OCID '{}' not found !".format(drg_id))
        exit (3)

def show_tags_from_network_security_group(nsg_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_network_security_group(nsg_id)
        nsg = response.data
        print (nsg.defined_tags)
    except:
        print ("ERROR 03: Network security group with OCID '{}' not found !".format(nsg_id))
        exit (3)

def show_tags_from_security_list(seclist_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_security_list(seclist_id)
        seclist = response.data
        print (seclist.defined_tags)
    except:
        print ("ERROR 03: Security list with OCID '{}' not found !".format(seclist_id))
        exit (3)

def show_tags_from_dhcp_options(do_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_dhcp_options(do_id)
        do = response.data
        print (do.defined_tags)
    except:
        print ("ERROR 03: DHCP options with OCID '{}' not found !".format(do_id))
        exit (3)

def show_tags_from_local_peering_gateway(lpg_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_local_peering_gateway(lpg_id)
        lpg = response.data
        print (lpg.defined_tags)
    except:
        print ("ERROR 03: Local peering gateway with OCID '{}' not found !".format(lpg_id))
        exit (3)

def show_tags_from_nat_gateway(ng_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_nat_gateway(ng_id)
        ng = response.data
        print (ng.defined_tags)
    except:
        print ("ERROR 03: NAT gateway with OCID '{}' not found !".format(ng_id))
        exit (3)

def show_tags_from_service_gateway(sg_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    try:
        response = VirtualNetworkClient.get_service_gateway(sg_id)
        sg = response.data
        print (sg.defined_tags)
    except:
        print ("ERROR 03: Service gateway with OCID '{}' not found !".format(sg_id))
        exit (3)

# ------------ main

# -- parse arguments
if len(sys.argv) == 3:
    profile = sys.argv[1]
    obj_id  = sys.argv[2] 
else:
    usage()

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)

except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get the resource type from OCID
obj_type = obj_id.split(".")[1].lower()

# compute
if   obj_type == "instance":             show_tags_from_compute_instance(obj_id)
elif obj_type == "image":                show_tags_from_custom_image(obj_id)
elif obj_type == "bootvolume":           show_tags_from_boot_volume(obj_id)
# block storage
elif obj_type == "volume":               show_tags_from_block_volume(obj_id)
elif obj_type == "volumebackup":         show_tags_from_block_volume_backup(obj_id)
# database
elif obj_type == "dbsystem":             show_tags_from_db_system(obj_id)
elif obj_type == "autonomousdatabase":   show_tags_from_autonomous_db(obj_id)
# object storage
elif obj_type == "bucket":               show_tags_from_bucket(obj_id)
# networking
elif obj_type == "vcn":                  show_tags_from_vcn(obj_id)
elif obj_type == "subnet":               show_tags_from_subnet(obj_id)
elif obj_type == "routetable":           show_tags_from_route_table(obj_id)
elif obj_type == "internetgateway":      show_tags_from_internet_gateway(obj_id)
elif obj_type == "drg":                  show_tags_from_dynamic_routing_gateway(obj_id)
elif obj_type == "networksecuritygroup": show_tags_from_network_security_group(obj_id)
elif obj_type == "securitylist":         show_tags_from_security_list(obj_id)
elif obj_type == "dhcpoptions":          show_tags_from_dhcp_options(obj_id)
elif obj_type == "localpeeringgateway":  show_tags_from_local_peering_gateway(obj_id)
elif obj_type == "natgateway":           show_tags_from_nat_gateway(obj_id)
elif obj_type == "servicegateway":       show_tags_from_service_gateway(obj_id)
else: print ("SORRY: resource type {:s} is not yet supported by this script !".format(obj_type)) 

# -- the end
exit (0)
