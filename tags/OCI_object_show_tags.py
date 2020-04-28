#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------
# This script show defined tags for an OCI resource/object
#
# Supported resource types:
# - COMPUTE            : instance, custom image, boot volume
# - BLOCK STORAGE      : block volume
# - DATABASE           : dbsystem, autonomous database
# - OBJECT STORAGE     : bucket
# - NETWORKING         : vcn, subnet, security list
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
# --------------------------------------------------------------------------------------------

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

    # Get Defined-tags for the compute instance
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

    # Get Defined-tags for the custom image
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

    # Get Defined-tags for the boot volume
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

    # Get Defined-tags for the boot volume
    try:
        response = BlockstorageClient.get_volume(bkvol_id)
        bkvol = response.data
        print (bkvol.defined_tags)
    except:
        print ("ERROR 03: block volume with OCID '{}' not found !".format(bkvol_id))
        exit (3)

# -- database
def show_tags_from_db_system(dbs_id):
    global config

    DatabaseClient = oci.database.DatabaseClient(config)

    # Get Defined-tags for the db system
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

    # Get Defined-tags for the autonomous DB
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

    # Get Defined-tags for the bucket
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

    # Get Defined-tags for the VCN
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

    # Get Defined-tags for the subnet
    try:
        response = VirtualNetworkClient.get_subnet(subnet_id)
        subnet = response.data
        print (subnet.defined_tags)
    except:
        print ("ERROR 03: Subnet with OCID '{}' not found !".format(subnet_id))
        exit (3)

def show_tags_from_security_list(seclist_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    # Get Defined-tags for the security list
    try:
        response = VirtualNetworkClient.get_security_list(seclist_id)
        seclist = response.data
        print (seclist.defined_tags)
    except:
        print ("ERROR 03: Security list with OCID '{}' not found !".format(seclist_id))
        exit (3)

def show_tags_from_route_table(rt_id):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    # Get Defined-tags for the route table
    try:
        response = VirtualNetworkClient.get_route_table(rt_id)
        rt = response.data
        print (rt.defined_tags)
    except:
        print ("ERROR 03: Route table with OCID '{}' not found !".format(rt_id))
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
if   obj_type == "instance":           show_tags_from_compute_instance(obj_id)
elif obj_type == "image":              show_tags_from_custom_image(obj_id)
elif obj_type == "bootvolume":         show_tags_from_boot_volume(obj_id)
# block storage
elif obj_type == "volume":             show_tags_from_block_volume(obj_id)
# database
elif obj_type == "dbsystem":           show_tags_from_db_system(obj_id)
elif obj_type == "autonomousdatabase": show_tags_from_autonomous_db(obj_id)
# object storage
elif obj_type == "bucket":             show_tags_from_bucket(obj_id)
# networking
elif obj_type == "vcn":                show_tags_from_vcn(obj_id)
elif obj_type == "subnet":             show_tags_from_subnet(obj_id)
elif obj_type == "securitylist":       show_tags_from_security_list(obj_id)
elif obj_type == "routetable":         show_tags_from_route_table(obj_id)
else: print ("SORRY: resource type {:s} is not yet supported by this script !".format(obj_type)) 

# -- the end
exit (0)
