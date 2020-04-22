#!/usr/bin/env python3

# ----------------------------------------------------------------------------------------
# This script adds a defined tag key and value (using tag namespace) to an autonomous DB
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-22: Initial Version
# ----------------------------------------------------------------------------------------

# TO DO: add the tag namespace to autonomous DB if not already added

# -- import
import oci
import sys

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} OCI_PROFILE autonomous_db_ocid tag_namespace tag_key tag_value".format(sys.argv[0]))
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

# ------------ main
global config

# -- parse arguments
if len(sys.argv) == 6:
    profile  = sys.argv[1]
    adb_id   = sys.argv[2] 
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

# -- Get Defined-tags for the autonomous DB
DatabaseClient = oci.database.DatabaseClient(config)

try:
    response = DatabaseClient.get_autonomous_database(adb_id)
    adb = response.data
except:
    print ("ERROR 03: Autonomous DB with OCID '{}' not found !".format(adb_id))
    exit (3)

# -- If the ADB status is TERMINATED or TERMINATING, stop here
if adb.lifecycle_state == "TERMINATED" or adb.lifecycle_state == "TERMINATING":
    print ("ERROR 04: Autonomous DB status is TERMINATED or TERMINATING, so cannot update tags !")
    exit (4)

# -- Add tag key to tag namespace and update autonomous DB
tags = adb.defined_tags
try:
    tags[tag_ns][tag_key] = tag_value
    DatabaseClient.update_autonomous_database(adb_id, oci.database.models.UpdateAutonomousDatabaseDetails(defined_tags=tags))
except:
    print ("ERROR 05: cannot add this tag key with this tag value !")
    print ("          Make sure the tag namespace, tag key and tag value are correct.")
    print ("          Make sure the autonomous DB status is correct")
    exit (5)

# -- the end
exit (0)
