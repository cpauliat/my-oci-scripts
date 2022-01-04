#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------
# This script adds a defined tag key and value (using tag namespace) to an OCI resource/object
#
# Supported resource types:
# - COMPUTE: instance
# - DATABASE: dbsystem, autonomous database, database, database home
# 
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-27: Initial Version
#    2020-05-04: Fix bug if tag namespace not already used for this object
#    2020-05-04: Simplify code
#    2020-09-18: Fix bug for automous database
#    2021-12-08: Add support for database
#    2021-12-09: set OCI region according to the gived object ocid and not according to profile
#    2021-12-09: Add support for Database Home
#    2022-01-03: use argparse to parse arguments
#
# TO DO: add support for more resource types
# --------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} -p OCI_PROFILE -id object_ocid -n tag_namespace -k tag_key -vl tag_value".format(sys.argv[0]))
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

def update_tags(ltags):
    if tag_ns in ltags:     # tag namespace already used in this object
        ltags[tag_ns][tag_key] = tag_value        
    else:                   # tag namespace not yet used in this object
        ltags[tag_ns] = { tag_key : tag_value }   
    return (ltags)

def add_tag_compute_instance(inst_id):
    ComputeClient = oci.core.ComputeClient(config)
    try:
        response = ComputeClient.get_instance(inst_id)
        tags = update_tags(response.data.defined_tags)
        ComputeClient.update_instance(inst_id, oci.core.models.UpdateInstanceDetails(defined_tags=tags))
    except:
        print (sys.exc_info()[1].message)
        exit (3)

def add_tag_db_system(dbs_id):
    DatabaseClient = oci.database.DatabaseClient(config)
    try:
        response = DatabaseClient.get_db_system(dbs_id)
        tags = update_tags(response.data.defined_tags)
        DatabaseClient.update_db_system(dbs_id, oci.database.models.UpdateDbSystemDetails(defined_tags=tags))
    except:
        print (sys.exc_info()[1].message)
        exit (3)

def add_tag_autonomous_db(adb_id):
    DatabaseClient = oci.database.DatabaseClient(config)
    try:
        response = DatabaseClient.get_autonomous_database(adb_id)
        tags = update_tags(response.data.defined_tags)
        DatabaseClient.update_autonomous_database(adb_id, oci.database.models.UpdateAutonomousDatabaseDetails(defined_tags=tags))
    except:
        print (sys.exc_info()[1].message)
        exit (3)

def add_tag_db(db_id):
    DatabaseClient = oci.database.DatabaseClient(config)
    try:
        response = DatabaseClient.get_database(db_id)
        tags = update_tags(response.data.defined_tags)
        DatabaseClient.update_database(db_id, oci.database.models.UpdateDatabaseDetails(defined_tags=tags))
    except:
        print (sys.exc_info()[1].message)
        exit (3)

def add_tag_dbhome(dbh_id):
    DatabaseClient = oci.database.DatabaseClient(config)
    try:
        response = DatabaseClient.get_db_home(dbh_id)
        tags = update_tags(response.data.defined_tags)
        DatabaseClient.update_db_home(dbh_id, oci.database.models.UpdateDbHomeDetails(defined_tags=tags))
    except:
        print (sys.exc_info()[1].message)
        exit (3)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Add a defined tag to an OCI resource")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-id", "--resource_ocid", help="Resource OCID", required=True)
parser.add_argument("-n", "--tag_ns", help="Tag namespace", required=True)
parser.add_argument("-k", "--tag_key", help="Tag key", required=True)
parser.add_argument("-vl", "--tag_value", help="Tag value", required=True)
args = parser.parse_args()

profile     = args.profile
obj_id      = args.resource_ocid
tag_ns      = args.tag_ns
tag_key     = args.tag_key
tag_value   = args.tag_value

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
# Set the working region to the region extracted from the ocid
obj_region = obj_id.split(".")[3].lower()
config["region"] = obj_region

if   obj_type == "instance":           add_tag_compute_instance(obj_id)
elif obj_type == "dbsystem":           add_tag_db_system(obj_id)
elif obj_type == "autonomousdatabase": add_tag_autonomous_db(obj_id)
elif obj_type == "database":           add_tag_db(obj_id)
elif obj_type == "dbhome":             add_tag_dbhome(obj_id)
else: print ("SORRY: resource type {:s} is not yet supported by this script !".format(obj_type)) 

# -- the end
exit (0)
