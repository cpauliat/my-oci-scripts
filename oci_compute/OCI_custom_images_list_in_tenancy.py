#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script lists custom images in all compartments in all active regions using OCI Python SDK
# 
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-09-08: Initial Version
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import argparse

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} -p OCI_PROFILE".format(sys.argv[0]))
    print ("")
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

# -- Get the name of of compartment from its id
def get_cpt_name_from_id(cpt_id):
    for c in compartments:
        if (c.id == cpt_id):
            return c.name
    return "root"

# ------------ main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List all custom images in an OCI tenant")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
args = parser.parse_args()
    
profile     = args.profile

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- headers
print ("Region, Compartment, Custom image name, OCID, Time created, Created by")

# -- Get the list of custom images using OSC specific tags and a query
# -- see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm
tag_ns  = "osc"
tag_key = "created-by"
query   = "query all resources where (definedTags.namespace = '{:s}' && definedTags.key = '{:s}' )".format(tag_ns, tag_key)

for region in regions:
    config["region"]=region.region_name

    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))

    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        if item.resource_type == "Image" and item.lifecycle_state == "Available":
            print ("{:s}, {:s}, {:s}, {:s}, {:s}, {:s}".format(config["region"], cpt_name, item.display_name, item.identifier, item.time_created.strftime("%Y-%m-%d"), item.defined_tags["osc"]["created-by"]))
#        if item.resource_type == "Image":
#            print ("{:s}, {:s}, {:s}, {:s}, {:s}, {:s}, {:s}".format(config["region"], cpt_name, item.display_name, item.identifier, item.time_created.strftime("%Y-%m-%d"), item.defined_tags["osc"]["created-by"], item.lifecycle_state))

# -- the end
exit (0)
