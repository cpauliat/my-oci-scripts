#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script lists all preauthenticated requests (PARs) for an object storage bucket using OCI Python SDK
# Then for each request, it asks if it must be deleted then deletes it if confirmed
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-15-12: Initial Version
#    2021-10-27: Add the possibility to delete all PARs in a single operation
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

def delete_par(l_os, l_ns, l_bucket, l_auth_id):
    oci.object_storage.ObjectStorageClient.delete_preauthenticated_request(l_os, namespace_name=l_ns, bucket_name=l_bucket, par_id=l_auth_id)

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

# -- List requests
print ("List of pre-authenticated requests for bucket {:s}:".format(bucket))
nb = 1
for auth in response.data:
    print ('{:2d}) {:50s} {:50s} {}'.format(nb, auth.name, auth.object_name, auth.time_expires))
    nb += 1

# -- Do you want to delete all PARs in a single operation ?
print ("")
answer = input ("Do you want to delete all PARs in a single operation ? (y/n): ")
if answer == "y":
    for auth in response.data:
        delete_par(ObjectStorageClient, namespace, bucket, auth.id)
    print ("")
    print (f"All pre-authenticated requests deleted !")

# -- If not, you can delete each PAR individually 
else:
    print ("")
    nb = 1
    for auth in response.data:
        answer2 = input (f"Do you want to delete request {nb} ? (y/n): ")
        if answer2 == "y":
            delete_par(ObjectStorageClient, namespace, bucket, auth.id)
            print (f"    Pre-authenticated request {nb} deleted !")
            print ("")
        nb += 1
    
# -- the end
exit (0)
