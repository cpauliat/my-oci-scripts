#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------
# This script adds a defined tag key and value (using tag namespace) to an OCI resource/object
#
# Supported resource types:
# - COMPUTE: instance
# - DATABASE: dbsystem, autonomous database
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
    print ("Usage: {} OCI_PROFILE object_ocid tag_namespace tag_key tag_value".format(sys.argv[0]))
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

# ---- specific functions to add tag to objects

def add_tag_compute_instance(inst_id, ltag_ns, ltag_key, ltag_value):
    global config

    # Get Defined-tags for the compute instance
    ComputeClient = oci.core.ComputeClient(config)
    try:
        response = ComputeClient.get_instance(inst_id)
        instance = response.data
    except:
        print ("ERROR 03: instance with OCID '{}' not found !".format(inst_id))
        exit (3)

    # Add tag key to tag namespace and update compute instance
    tags = instance.defined_tags
    try:
        tags[ltag_ns][ltag_key] = ltag_value
        ComputeClient.update_instance(inst_id, oci.core.models.UpdateInstanceDetails(defined_tags=tags))
    except:
        print ("ERROR 05: cannot add this tag key with this tag value !")
        print (sys.exc_info()[1].message)
        exit (5)

def add_tag_db_system(dbs_id, ltag_ns, ltag_key, ltag_value):
    global config

    # Get Defined-tags for the db system
    DatabaseClient = oci.database.DatabaseClient(config)

    try:
        response = DatabaseClient.get_db_system(dbs_id)
        dbs = response.data
    except:
        print ("ERROR 03: db system with OCID '{}' not found !".format(dbs_id))
        exit (3)

    # Add tag key to tag namespace and update compute instance
    tags = dbs.defined_tags
    try:
        tags[ltag_ns][ltag_key] = ltag_value
        DatabaseClient.update_db_system(dbs_id, oci.database.models.UpdateDbSystemDetails(defined_tags=tags))
    except:
        print ("ERROR 05: cannot add this tag key with this tag value !")
        print (sys.exc_info()[1].message)
        exit (5)

def add_tag_autonomous_db(adb_id, ltag_ns, ltag_key, ltag_value):
    global config

    # Get Defined-tags for the autonomous DB
    DatabaseClient = oci.database.DatabaseClient(config)

    try:
        response = DatabaseClient.get_autonomous_database(adb_id)
        adb = response.data
    except:
        print ("ERROR 03: Autonomous DB with OCID '{}' not found !".format(adb_id))
        exit (3)

    # Add tag key to tag namespace and update autonomous DB
    tags = adb.defined_tags
    try:
        tags[ltag_ns][ltag_key] = ltag_value
        DatabaseClient.update_autonomous_database(adb_id, oci.database.models.UpdateAutonomousDatabaseDetails(defined_tags=tags))
    except:
        print ("ERROR 05: cannot add this tag key with this tag value !")
        print (sys.exc_info()[1].message)
        exit (5)

# ------------ main

# -- parse arguments
if len(sys.argv) == 6:
    profile  = sys.argv[1]
    obj_id   = sys.argv[2] 
    tag_ns   = sys.argv[3]
    tag_key  = sys.argv[4]
    tag_value= sys.argv[5]
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

if   obj_type == "instance":           add_tag_compute_instance(obj_id, tag_ns, tag_key, tag_value)
elif obj_type == "dbsystem":           add_tag_db_system(obj_id, tag_ns, tag_key, tag_value)
elif obj_type == "autonomousdatabase": add_tag_autonomous_db(obj_id, tag_ns, tag_key, tag_value)
else: print ("SORRY: resource type {:s} is not yet supported by this script !".format(obj_type)) 

# -- the end
exit (0)
