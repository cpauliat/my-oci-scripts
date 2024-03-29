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
#    2022-01-03: use argparse to parse arguments
#    2022-01-04: add --no_color option
# --------------------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import datetime
import argparse

# -------- colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLOR_TITLE = "\033[93m"            # light yellow
COLOR_EXPIRED = "\033[91m"          # light red
COLOR_ACTIVE = "\033[32m"           # green
COLOR_BUCKET = "\033[96m"           # light cyan
COLOR_NORMAL = "\033[39m"

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-nc] -p OCI_PROFILE -b bucket_name".format(sys.argv[0]))
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

# ---- Disable colored output
def disable_colored_output():
    global COLOR_TITLE   
    global COLOR_EXPIRED 
    global COLOR_ACTIVE  
    global COLOR_BUCKET  
    global COLOR_NORMAL 

    COLOR_TITLE   = ""
    COLOR_EXPIRED = ""
    COLOR_ACTIVE  = ""
    COLOR_BUCKET  = ""
    COLOR_NORMAL  = ""

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List PARs in a bucket")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-b", "--bucket", help="Bucket name", required=True)
parser.add_argument("-nc", "--no_color", help="Disable colored output", action="store_true")
args = parser.parse_args()

profile = args.profile
bucket  = args.bucket
if args.no_color:
  disable_colored_output()

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
