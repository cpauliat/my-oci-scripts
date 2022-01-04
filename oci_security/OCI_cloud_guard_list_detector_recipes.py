#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists Cloud Guard detector recipes in a OCI tenant using OCI Python SDK 
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-05: Initial Version (only lists recipes in root compartment)
#    2021-11-17: Lists recipes in all compartments
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------


# -------- import
import oci
import sys
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions
def usage():
    print (f"Usage: {sys.argv[0]} -p OCI_PROFILE")
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

# -- get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Oracle managed recipes: get the list of Cloud Guard detector recipes in root compartment
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)
response = oci.pagination.list_call_get_all_results(CloudGuardClient.list_detector_recipes,compartment_id=RootCompartmentID)
if len(response.data) > 0:
    for recipe in response.data:
        if recipe.owner == "ORACLE":
            print ("---------- ")
            print (f"name        : {recipe.display_name}")
            print (f"type        : {recipe.detector}")
            print (f"owner       : {recipe.owner}")
            print (f"ocid        : {recipe.id}")
            print (f"compartment : root")

# -- User Managed recipes: search Cloud Guard detector recipes in all compartments
SearchClient = oci.resource_search.ResourceSearchClient(config)

query = "query cloudguarddetectorrecipe resources"
response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
for item in response.data.items:
    cpt_name  = get_cpt_full_name_from_id(item.compartment_id)
    response2 = CloudGuardClient.get_detector_recipe(detector_recipe_id=item.identifier) 
    recipe    = response2.data  
    print ("---------- ")
    print (f"name        : {recipe.display_name}")
    print (f"type        : {recipe.detector}")
    print (f"owner       : {recipe.owner}")
    print (f"ocid        : {recipe.id}")
    print (f"compartment : {cpt_name}")

# -- the end
exit (0)
