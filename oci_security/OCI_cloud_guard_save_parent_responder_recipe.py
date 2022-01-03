#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script saves the detailed configuration of a Cloud Guard "parent" (not attached to a target) 
# RESPONDER RECIPE to a JSON backup file in a OCI tenant using OCI Python SDK.
# 
# This backup file can then be used to update or restore configuration of a "parent" responder recipe 
# using script OCI_cloud_guard_update_parent_responder_recipe.py
# 
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-16: Initial Version
#    2021-11-19: Remove responder_rules[] from backup and use effective_responder_rules[]
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------


# ---------- import
import oci
import sys
import argparse
from pathlib import Path
from operator import itemgetter

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---------- functions
def usage():
    print (f"Usage: {sys.argv[0]} OCI_PROFILE responder_recipe_ocid output_file.json")
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

# ---------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Save configuration of a Cloud Guard responder recipe")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-r", "--recipe_ocid", help="Responder recipe OCID", required=True)
parser.add_argument("-f", "--file", help="Backup file (.json)", required=True)
args = parser.parse_args()
    
profile     = args.profile
recipe_ocid = args.recipe_ocid
output_file = args.file

# -- If the output file already exists, exit in error 
my_file = Path(output_file)
if my_file.exists():
    print (f"ERROR: a file or directory already exists with name {output_file} !")
    exit (3)

# -- get info from profile    
try:
    config = oci.config.from_file(configfile,profile)
except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)

# -- Get the detailed responder recipe including rules
try:
    response = CloudGuardClient.get_responder_recipe(responder_recipe_id=recipe_ocid)
except oci.exceptions.ServiceError as err:
    print (f"ERROR: {err.message}")
    exit (4)    

# -- No need to save responder_rules (reduce size of backup file)
response.data.responder_rules = []

# -- Display main characteristics of the responder recipe
print (f"Responder recipe name               : {response.data.display_name}")
print (f"Responder recipe owner              : {response.data.owner}")
print (f"Number of effective responder rules : {len(response.data.effective_responder_rules)}")
print ("")

# -- Save this detailed configuration (JSON formatted) in the output file
try:
    with open(output_file, 'w') as fileout:
        print (response.data, file=fileout)
        print (f"Responder recipe configuration successfully saved to JSON file {output_file} !")
except OSError as err:
    print (f"ERROR: {err.strerror}")

# -- the end
exit (0)
