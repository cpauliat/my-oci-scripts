#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists Cloud Guard targets in a OCI tenant using OCI Python SDK 
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-18: Initial Version 
# --------------------------------------------------------------------------------------------------------------


# ---------- import
import oci
import sys

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---------- functions
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
if (len(sys.argv) == 2):
    profile = sys.argv[1]
else:
    usage()

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

# -- Search Cloud Guard targets in all compartments
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)
SearchClient     = oci.resource_search.ResourceSearchClient(config)

query = "query cloudguardtarget resources"
response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
print (f"Number of Cloud Guard targets : {len(response.data.items)}")
for item in response.data.items:
    response2 = CloudGuardClient.get_target(target_id=item.identifier) 
    target    = response2.data  
    print ("---------- ")
    print (f"target name          : {target.display_name}")
    print (f"target ocid          : {target.id}")
    print (f"target resource id   : {target.target_resource_id}")
    print (f"target resource name : {get_cpt_full_name_from_id(target.target_resource_id)}")
    print (f"compartment          : {get_cpt_full_name_from_id(item.compartment_id)}")
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

# -- the end
exit (0)
