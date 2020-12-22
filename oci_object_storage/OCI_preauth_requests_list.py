#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script lists the preauth requests for an object storage bucket using OCI Python SDK
# and sorts them by expired and actives requests
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

# ---------- Colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
colored_output=True
if (colored_output):
  COLOR_TITLE = "\033[93m"            # light yellow
  COLOR_EXPIRED = "\033[91m"          # light red
  COLOR_ACTIVE = "\033[32m"           # green
  COLOR_BUCKET = "\033[96m"           # light cyan
  COLOR_NORMAL = "\033[39m"
else:
  COLOR_TITLE = ""
  COLOR_EXPIRED = ""
  COLOR_ACTIVE = ""
  COLOR_BUCKET = ""
  COLOR_NORMAL = ""

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
global config
global ads
global IdentityClient
global initial_cpt_ocid
global initial_cpt_name
global RootCompartmentID

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

# -- List active requests
print (COLOR_TITLE + "List of ACTIVE pre-authenticated requests for bucket ",end='')
print (COLOR_BUCKET + bucket + COLOR_TITLE + ": (name, object-name, time-expires)" + COLOR_ACTIVE)
for auth in response.data:
    if auth.time_expires > now:
        print ('- {:50s} {:55s} {}'.format(auth.name, auth.object_name, auth.time_expires))

print ("")

# -- List expired requests
print (COLOR_TITLE + "List of EXPIRED pre-authenticated requests for bucket ",end='')
print (COLOR_BUCKET + bucket + COLOR_TITLE + ": (name, object-name, time-expires)" + COLOR_EXPIRED)
for auth in response.data:
    if auth.time_expires <= now:
        print ('- {:50s} {:55s} {}'.format(auth.name, auth.object_name, auth.time_expires))

print (COLOR_NORMAL)

# -- the end
exit (0)
