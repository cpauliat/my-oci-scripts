#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script saves the detailed configuration of a Cloud Guard "parent" (not attached to a target) 
# DETECTOR RECIPE (ACTIVITY or CONFIGURATION) to a JSON backup file in a OCI tenant using OCI Python SDK.
# 
# This backup file can then be used to update or restore configuration of a detector recipe using another script
#
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-16: Initial Version
#    2021-11-19: Remove detector_rules[] from backup and use effective_detector_rules[]
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------


# -------- import
import oci
import sys
import argparse
from pathlib import Path
from operator import itemgetter

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions
def usage():
    print (f"Usage: {sys.argv[0]} -p OCI_PROFILE -r detector_recipe_ocid -f output_file.json")
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
parser = argparse.ArgumentParser(description = "Save configuration of a Cloud Guard detector recipe")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-r", "--recipe_ocid", help="Detector recipe OCID", required=True)
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

# -- Get the detailed configuration of detector recipe including rules
try:
    response = CloudGuardClient.get_detector_recipe(detector_recipe_id=recipe_ocid)
except oci.exceptions.ServiceError as err:
    print (f"ERROR: {err.message}")
    exit (4)    

# -- No need to save detector_rules (reduce size of backup file)
response.data.detector_rules = []

# -- Display main characteristics of the detector recipe
print (f"Detector recipe name               : {response.data.display_name}")
print (f"Detector recipe type               : {response.data.detector}")
print (f"Detector recipe owner              : {response.data.owner}")
print (f"Number of effective detector rules : {len(response.data.effective_detector_rules)}")
print ("")

# -- Save this detailed configuration (JSON formatted) in the output file
try:
    with open(output_file, 'w') as fileout:
        print (response.data, file=fileout)
        print (f"Detector recipe configuration successfully saved to JSON file {output_file} !")
        print ("")
except OSError as err:
    print (f"ERROR: {err.strerror}")

# -- the end
exit (0)
