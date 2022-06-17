#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script looks for all OCI resources in a specific compartment in a OCI tenant 
# in a specific region or in all regions.
#  
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2022-06-17: Initial Version
# --------------------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# -- Get the name of a compartment from its id
def get_cpt_name_from_id(cpt_id):
    for c in compartments:
        if (c.id == cpt_id):
            return c.name
    return "root"

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Search resources in an OCI compartment")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-c", "--compartment", help="Compartment name or compartment OCID", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
args = parser.parse_args()

profile         = args.profile
cpt             = args.compartment
all_regions     = args.all_regions

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- find compartment name and compartment id
if (cpt == "root") or (cpt == RootCompartmentID):
    initial_cpt_name = "root"
    initial_cpt_ocid = RootCompartmentID
else:
    response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
    compartments = response.data
    cpt_exist = False
    for compartment in compartments:  
        if (cpt == compartment.id) or (cpt == compartment.name):
            initial_cpt_ocid = compartment.id
            initial_cpt_name = compartment.name
            cpt_exist = True
    if not(cpt_exist):
        print ("ERROR 03: compartment '{}' does not exist !".format(cpt))
        exit (3) 

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = f"query all resources where compartmentId = '{initial_cpt_ocid}'"

# -- Search the resources
SearchClient = oci.resource_search.ResourceSearchClient(config)

#response = oci.pagination.list_call_get_all_results(SearchClient.search_resources, oci.resource_search.models.StructuredSearchDetails(query))
response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
if len(response.data.items) > 0:
    print ("Resource Type, Compartment, Display Name, OCID")
    new_items = []
    for item in response.data.items:
        new_item = {}
        new_item["resource_type"] = item.resource_type
        new_item["display_name"]  = item.display_name
        new_item["identifier"]    = item.identifier
        new_items.append(new_item)

    sorted_items =  sorted(new_items, key=lambda d: d['resource_type']) 

    for item in sorted_items:
        print (f"{item['resource_type']}, {item['identifier']}, {item['display_name']}")

# -- the end
exit (0)
