#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script saves the detailed configuration of a Cloud Guard target a JSON backup file 
# in a OCI tenant using OCI Python SDK.
# 
# This backup includes:
# - display name
# - description
# - defined and freeform tags 
# - detector recipes if they exist ("child recipe")
# - responder reciper if it exists ("child" recipe)
#
# This backup file can then be used to update or restore configuration of a target 
# using script OCI_cloud_guard_update_target.py
#
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-19: Initial Version
# --------------------------------------------------------------------------------------------------------------


# ---------- import
import oci
import sys
from pathlib import Path
from operator import itemgetter

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---------- functions
def usage():
    print (f"Usage: {sys.argv[0]} OCI_PROFILE target_ocid output_file.json")
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

# ---- Get the full name of compartment from its id
def get_cpt_parent(cpt):
    if (cpt.id == RootCompartmentID):
        return "root"
    else:
        for c in compartments:
            if c.id == cpt.compartment_id:
                break
        return (c)

def cpt_full_name(cpt):
    if cpt.id == RootCompartmentID:
        return ""
    else:
        # if direct child of root compartment
        if cpt.compartment_id == RootCompartmentID:
            return cpt.name
        else:
            parent_cpt = get_cpt_parent(cpt)
            return cpt_full_name(parent_cpt)+":"+cpt.name

def get_cpt_full_name_from_id(cpt_id):
    if cpt_id == RootCompartmentID:
        return "root"
    else:
        for c in compartments:
            if (c.id == cpt_id):
                return cpt_full_name(c)
    return

# ---------- main

# -- parse arguments
if (len(sys.argv) == 4):
    profile     = sys.argv[1]
    target_ocid = sys.argv[2]
    output_file = sys.argv[3]
else:
    usage()

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

# -- get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Get the target
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)
try:
    response = CloudGuardClient.get_target(target_id=target_ocid)
    target   = response.data
except oci.exceptions.ServiceError as err:
    print (f"ERROR: {err.message}")
    exit (4) 
    
# --  Remove detector_rules to reduce backup size (we will use effective_detector_rules)
for detector_recipe in target.target_detector_recipes:      
    detector_recipe.detector_rules = []

# --  Remove responder_rules to reduce backup size (we will use effective_responder_rules)
for responder_recipe in target.target_responder_recipes:      
    responder_recipe.responder_rules = []

# -- Display main characteristics of the target
print (f"target name          : {target.display_name}")
print (f"target ocid          : {target.id}")
print (f"target resource id   : {target.target_resource_id}")
print (f"target resource name : {get_cpt_full_name_from_id(target.target_resource_id)}")
print (f"compartment          : {get_cpt_full_name_from_id(target.compartment_id)}")
print (f"recipe count         : {target.recipe_count}")

if target.recipe_count > 0:
    print("")

if len(target.target_detector_recipes) > 0:
    for detector_recipe in target.target_detector_recipes:
        print (f"detector recipe {detector_recipe.detector}")
        print (f"- name                                 : {detector_recipe.display_name}")
        print (f"- child recipe ocid (in target)        : {detector_recipe.id}")
        print (f"- parent recipe ocid (in recipes list) : {detector_recipe.detector_recipe_id}")
        print ("")

if len(target.target_responder_recipes) > 0:
    for responder_recipe in target.target_responder_recipes:
        print (f"responder recipe")
        print (f"- name                                 : {responder_recipe.display_name}")
        print (f"- child recipe ocid (in target)        : {responder_recipe.id}")
        print (f"- parent recipe ocid (in recipes list) : {responder_recipe.responder_recipe_id}")
        print ("")    

# -- Save this detailed configuration (JSON formatted) in the output file
try:
    with open(output_file, 'w') as fileout:
        print (target, file=fileout)
        print (f"Target configuration successfully saved to JSON file {output_file} !")
except OSError as err:
    print (f"ERROR: {err.strerror}")

# -- the end
exit (0)
