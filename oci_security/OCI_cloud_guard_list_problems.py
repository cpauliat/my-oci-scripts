#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists Cloud Guard problems in a OCI tenant using OCI Python SDK 
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2022-01-03: Initial Version
# --------------------------------------------------------------------------------------------------------------


# -------- import
import oci
import sys
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions
def usage():
    print (f"Usage: {sys.argv[0]} OCI_PROFILE")
    print ("")
    print (f"note: OCI_PROFILE must exist in {configfile} file (see example below)")
    print ("")
    print ("[EMEAOSC]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List Cloud Guard problems in an OCI tenant")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
args = parser.parse_args()
    
profile = args.profile

# -- get info from profile    
try:
    config = oci.config.from_file(configfile,profile)
except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# # -- Get list of compartments with all sub-compartments
# response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
# compartments = response.data

# -- Get the list of Cloud Guard problems ids
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)
response = oci.pagination.list_call_get_all_results(CloudGuardClient.list_problems,compartment_id=RootCompartmentID)
if len(response.data) > 0:
    for pb in response.data:
        print (f"{pb.region:15s} {pb.id} {pb.resource_id}")

# -- the end
exit (0)
