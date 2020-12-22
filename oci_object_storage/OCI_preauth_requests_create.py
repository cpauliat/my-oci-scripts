#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script creates a preauth requests for an object in an object storage bucket using OCI Python SDK
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-15-12: Initial Version
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
    print ("Usage: {} OCI_PROFILE bucket_name object_name par_name type days_from_now".format(sys.argv[0]))
    print ("")
    print ("Notes:")
    print ("- type values: R for Read or RW for ReadWrite")
    print ("- expiry date/time is now + <days_from_now> days. ")
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
if len(sys.argv) != 7: 
    usage()

profile  = sys.argv[1] 
bucket   = sys.argv[2]
object   = sys.argv[3]
par_name = sys.argv[4]
type     = sys.argv[5]
days_fnow= sys.argv[6]

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

# -- Create a PAR
if type.upper() == "R":
    access_type = "ObjectRead"
elif type.upper() == "RW":
    access_type = "ObjectRead"
else:
    usage()

now = datetime.datetime.now(datetime.timezone.utc)
exp_time = now + datetime.timedelta(days=int(days_fnow))
details = oci.object_storage.models.PreauthenticatedRequest(access_type=access_type , name = par_name, object_name = object,  time_expires = exp_time)
response = ObjectStorageClient.create_preauthenticated_request (namespace, bucket, details)
par = response.data
uri = f"https://objectstorage.{config['region']}.oraclecloud.com{par.access_uri}"
print (f"Preauthenticated requests for object {object} created !")
print ("- URI         = ",uri)
print ("- access type = ",par.access_type)
print ("- expiration  = ",par.time_expires)

# -- the end
exit (0)
