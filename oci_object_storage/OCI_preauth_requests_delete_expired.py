#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script lists then deletes expired preauth requests for an object storage bucket using OCI Python SDK
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-03-25: Initial Version
# --------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import datetime

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} OCI_PROFILE bucket_name".format(sys.argv[0]))
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
if len(sys.argv) != 3: 
    usage()

profile  = sys.argv[1] 
bucket   = sys.argv[2]

# -- load profile from config file and exists if profile does not exist
try:
    config = oci.config.from_file(configfile, profile)

except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get the preauth requests for the bucket
ObjectStorageClient = oci.object_storage.ObjectStorageClient(config)
namespace = ObjectStorageClient.get_namespace().data
try:
    response = oci.pagination.list_call_get_all_results(ObjectStorageClient.list_preauthenticated_requests, namespace_name=namespace, bucket_name=bucket)
except:
    print ("ERROR 04: bucket {} not found !".format(bucket))
    exit (4)

# -- Exit script if no preauth requests found
if len(response.data) == 0:
    print ("No pre-authenticated requests found for this bucket !")
    exit (0)

# -- Get current date and time
now = datetime.datetime.now(datetime.timezone.utc)

# -- List expired requests
print ("List of expired pre-authenticated requests for bucket {:s}:".format(bucket))
for auth in response.data:
    if auth.time_expires < now:
        print ('- {:50s} {:50s} {}'.format(auth.name, auth.object_name, auth.time_expires))

# -- Ask to confirm deletion
print ("")
answer = input ("Do you confirm deletion of those requests ? (y/n): ")
if answer != "y":
    print ("Deletion not confirmed. Exiting !")
    exit (5)

# -- Delete the requests
for auth in response.data:
    if auth.time_expires < now:
        oci.object_storage.ObjectStorageClient.delete_preauthenticated_request(ObjectStorageClient, namespace_name=namespace, bucket_name=bucket, par_id=auth.id)
    
print ("Pre-authenticated requests deleted !")

# -- the end
exit (0)
