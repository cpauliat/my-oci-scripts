#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script restores all the archived objects in a bucket
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-04-28: Initial Version
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import argparse

# ---------- Colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
colored_output=True
if (colored_output):
  COLOR_TITLE   = "\033[93m"          # light yellow
  COLOR_RESTORE = "\033[91m"          # light red
  COLOR_ACTIVE  = "\033[32m"           # green
  COLOR_BUCKET  = "\033[96m"           # light cyan
  COLOR_NORMAL  = "\033[39m"
else:
  COLOR_TITLE   = ""
  COLOR_RESTORE = ""
  COLOR_ACTIVE  = ""
  COLOR_BUCKET  = ""
  COLOR_NORMAL  = ""

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} -p OCI_PROFILE -b bucket_name".format(sys.argv[0]))
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

# -- parse arguments
parser = argparse.ArgumentParser(description = "Restore archived objects in a bucket")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-b", "--bucket", help="Bucket name", required=True)
args = parser.parse_args()

profile = args.profile
bucket  = args.bucket

# -- load profile from config file and exists if profile does not exist
try:
    config = oci.config.from_file(configfile, profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get the list of objects stored in the bucket
ObjectStorageClient = oci.object_storage.ObjectStorageClient(config)
namespace = ObjectStorageClient.get_namespace().data
try:
    response = oci.pagination.list_call_get_all_results(ObjectStorageClient.list_objects, namespace_name=namespace, bucket_name=bucket)
except:
    print ("ERROR 04: bucket {} not found !".format(bucket))
    exit (4)

# -- Exit script if no preauth requests found
if len(response.data.objects) == 0:
    print ("No object found in this bucket !")
    exit (0)

# -- List expired requests
print (COLOR_TITLE + "Restoring archived objects in bucket ",end='')
print (COLOR_BUCKET + bucket)
for object in response.data.objects:
    print (COLOR_ACTIVE + object.name + " : ", end='')
    try:
        rod = oci.object_storage.models.RestoreObjectsDetails(object_name = object.name)
        response = ObjectStorageClient.restore_objects(namespace_name=namespace, bucket_name=bucket, restore_objects_details=rod)
        print (COLOR_RESTORE + " restoring object !")
    except:
        print (COLOR_NORMAL + " object not in archive mode !")

print (COLOR_NORMAL)

# -- the end
exit (0)
