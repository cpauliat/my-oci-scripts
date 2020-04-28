#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------
# This script removes a defined tag key (using tag namespace) from an OCI resource/object
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
#    2020-04-27: Initial Version
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
    print ("Usage: {} OCI_PROFILE object_ocid tag_namespace tag_key".format(sys.argv[0]))
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

# ---- specific functions to remove tag keys from objects

# -- compute
def remove_tag_from_compute_instance(inst_id, ltag_ns, ltag_key):
    global config

    ComputeClient = oci.core.ComputeClient(config)

    # Get Defined-tags for the compute instance
    try:
        response = ComputeClient.get_instance(inst_id)
        instance = response.data
    except:
        print ("ERROR 03: instance with OCID '{}' not found !".format(inst_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = instance.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this compute instance !")
        exit (5)

    # Update compute instance
    try:
        ComputeClient.update_instance(inst_id, oci.core.models.UpdateInstanceDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this compute instance !")
        print (sys.exc_info()[1].message)
        exit (6)

def remove_tag_from_custom_image(image_id, ltag_ns, ltag_key):
    global config

    ComputeClient = oci.core.ComputeClient(config)

    # Get Defined-tags for the custom image
    try:
        response = ComputeClient.get_image(image_id)
        image = response.data
    except:
        print ("ERROR 03: custom image with OCID '{}' not found !".format(image_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = image.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this custom image !")
        exit (5)

    # Update custom image
    try:
        ComputeClient.update_image(image_id, oci.core.models.UpdateImageDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this custom image !")
        print (sys.exc_info()[1].message)
        exit (6)

def remove_tag_from_boot_volume(bootvol_id, ltag_ns, ltag_key):
    global config

    BlockstorageClient = oci.core.BlockstorageClient(config)

    # Get Defined-tags for the boot volume
    try:
        response = BlockstorageClient.get_boot_volume(bootvol_id)
        bootvol = response.data
    except:
        print ("ERROR 03: boot volume with OCID '{}' not found !".format(bootvol_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = bootvol.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this boot volume !")
        exit (5)

    # Update boot volume
    try:
        BlockstorageClient.update_boot_volume(bootvol_id, oci.core.models.UpdateBootVolumeDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this boot volume !")
        print (sys.exc_info()[1].message)
        exit (6)

# -- block storage
def remove_tag_from_block_volume(bkvol_id, ltag_ns, ltag_key):
    global config

    BlockstorageClient = oci.core.BlockstorageClient(config)

    # Get Defined-tags for the boot volume
    try:
        response = BlockstorageClient.get_volume(bkvol_id)
        bkvol = response.data
    except:
        print ("ERROR 03: block volume with OCID '{}' not found !".format(bkvol_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = bkvol.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this block volume !")
        exit (5)

    # Update boot volume
    try:
        BlockstorageClient.update_volume(bkvol_id, oci.core.models.UpdateVolumeDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this block volume !")
        print (sys.exc_info()[1].message)
        exit (6)

# -- database
def remove_tag_from_db_system(dbs_id, ltag_ns, ltag_key):
    global config

    DatabaseClient = oci.database.DatabaseClient(config)

    # Get Defined-tags for the db system
    try:
        response = DatabaseClient.get_db_system(dbs_id)
        dbs = response.data
    except:
        print ("ERROR 03: db system with OCID '{}' not found !".format(dbs_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = dbs.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this db system !")
        exit (5)

    # Update db system
    try:
        DatabaseClient.update_db_system(dbs_id, oci.database.models.UpdateDbSystemDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this db system !")
        print (sys.exc_info()[1].message)
        exit (6)

def remove_tag_from_autonomous_db(abd_id, ltag_ns, ltag_key):
    global config

    DatabaseClient = oci.database.DatabaseClient(config)

    # Get Defined-tags for the autonomous DB
    try:
        response = DatabaseClient.get_autonomous_database(adb_id)
        adb = response.data
    except:
        print ("ERROR 03: Autonomous DB with OCID '{}' not found !".format(adb_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = adb.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this autonomous database !")
        exit (5)

    # Update autonomous DB
    try:
        DatabaseClient.update_autonomous_database(adb_id, oci.database.models.UpdateAutonomousDatabaseDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this autonomous DB !")
        print (sys.exc_info()[1].message)
        exit (6)

# -- object storage
def remove_tag_from_bucket(bucket_id, ltag_ns, ltag_key):
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
    except:
        print ("ERROR 03: Bucket with OCID '{}' not found !".format(bucket_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = bucket.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this bucket !")
        exit (5)

    # Update bucket
    try:
        ObjectStorageClient.update_bucket(namespace, bucket_id, oci.object_storage.models.UpdateBucketDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this bucket !")
        print (sys.exc_info()[1].message)
        exit (6)

# -- networking
def remove_tag_from_vcn(vcn_id, ltag_ns, ltag_key):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    # Get Defined-tags for the VCN
    try:
        response = VirtualNetworkClient.get_vcn(vcn_id)
        vcn = response.data
    except:
        print ("ERROR 03: VCN with OCID '{}' not found !".format(vcn_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = vcn.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this VCN !")
        exit (5)

    # Update VCN
    try:
        VirtualNetworkClient.update_vcn(vcn_id, oci.core.models.UpdateVcnDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this VCN !")
        print (sys.exc_info()[1].message)
        exit (6)

def remove_tag_from_subnet(subnet_id, ltag_ns, ltag_key):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    # Get Defined-tags for the subnet
    try:
        response = VirtualNetworkClient.get_subnet(subnet_id)
        subnet = response.data
    except:
        print ("ERROR 03: Subnet with OCID '{}' not found !".format(subnet_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = subnet.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this subnet !")
        exit (5)

    # Update subnet
    try:
        VirtualNetworkClient.update_subnet(subnet_id, oci.core.models.UpdateSubnetDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this subnet !")
        print (sys.exc_info()[1].message)
        exit (6)

def remove_tag_from_security_list(seclist_id, ltag_ns, ltag_key):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    # Get Defined-tags for the security list
    try:
        response = VirtualNetworkClient.get_security_list(seclist_id)
        seclist = response.data
    except:
        print ("ERROR 03: Security list with OCID '{}' not found !".format(seclist_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = seclist.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this security list !")
        exit (5)

    # Update security list
    try:
        VirtualNetworkClient.update_security_list(seclist_id, oci.core.models.UpdateSecurityListDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this security list !")
        print (sys.exc_info()[1].message)
        exit (6)

def remove_tag_from_route_table(rt_id, ltag_ns, ltag_key):
    global config

    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

    # Get Defined-tags for the route table
    try:
        response = VirtualNetworkClient.get_route_table(rt_id)
        rt = response.data
    except:
        print ("ERROR 03: Route table with OCID '{}' not found !".format(rt_id))
        exit (3)

    # Remove tag key from tag namespace
    tags = rt.defined_tags
    try:
        del tags[ltag_ns][ltag_key]
    except:
        print ("ERROR 05: this tag key does not exist for this route table !")
        exit (5)

    # Update route table
    try:
        VirtualNetworkClient.update_route_table(rt_id, oci.core.models.UpdateRouteTableDetails(defined_tags=tags))
    except:
        print ("ERROR 06: cannot remove this tag from this route table !")
        print (sys.exc_info()[1].message)
        exit (6)


# ------------ main

# -- parse arguments
if len(sys.argv) == 5:
    profile  = sys.argv[1]
    obj_id   = sys.argv[2] 
    tag_ns   = sys.argv[3]
    tag_key  = sys.argv[4]
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
if   obj_type == "instance":           remove_tag_from_compute_instance(obj_id, tag_ns, tag_key)
if   obj_type == "image":              remove_tag_from_custom_image(obj_id, tag_ns, tag_key)
elif obj_type == "bootvolume":         remove_tag_from_boot_volume(obj_id, tag_ns, tag_key)
# block storage
elif obj_type == "volume":             remove_tag_from_block_volume(obj_id, tag_ns, tag_key)
# database
elif obj_type == "dbsystem":           remove_tag_from_db_system(obj_id, tag_ns, tag_key)
elif obj_type == "autonomousdatabase": remove_tag_from_autonomous_db(obj_id, tag_ns, tag_key)
# object storage
elif obj_type == "bucket":             remove_tag_from_bucket(obj_id, tag_ns, tag_key)
# networking
elif obj_type == "vcn":                remove_tag_from_vcn(obj_id, tag_ns, tag_key)
elif obj_type == "subnet":             remove_tag_from_subnet(obj_id, tag_ns, tag_key)
elif obj_type == "securitylist":       remove_tag_from_security_list(obj_id, tag_ns, tag_key)
elif obj_type == "routetable":         remove_tag_from_route_table(obj_id, tag_ns, tag_key)
else: print ("SORRY: resource type {:s} is not yet supported by this script !".format(obj_type)) 

# -- the end
exit (0)
