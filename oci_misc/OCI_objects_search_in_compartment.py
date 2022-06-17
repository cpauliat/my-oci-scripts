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

# -------- global variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLOR_TITLE0="\033[95m"             # light magenta
COLOR_TITLE1="\033[91m"             # light red
COLOR_TITLE2="\033[32m"             # green
COLOR_AD="\033[94m"                 # light blue
COLOR_COMP="\033[93m"               # light yellow
COLOR_BREAK="\033[91m"              # light red
COLOR_NORMAL="\033[39m"

# -------- functions

# ---- Disable colored output
def disable_colored_output():
    global COLOR_TITLE0
    global COLOR_TITLE1
    global COLOR_TITLE2
    global COLOR_AD
    global COLOR_COMP
    global COLOR_BREAK
    global COLOR_NORMAL

    COLOR_TITLE0 = ""
    COLOR_TITLE1 = ""
    COLOR_TITLE2 = ""
    COLOR_AD     = ""
    COLOR_COMP   = ""
    COLOR_BREAK  = ""
    COLOR_NORMAL = ""

# -- Get the name of a compartment from its id
def get_cpt_name_from_id(cpt_id):
    for c in compartments:
        if (c.id == cpt_id):
            return c.name
    return "root"

# ----
def search_objects():
    query = f"query all resources where compartmentId = '{initial_cpt_ocid}'"
    SearchClient = oci.resource_search.ResourceSearchClient(config)

    #response = oci.pagination.list_call_get_all_results(SearchClient.search_resources, oci.resource_search.models.StructuredSearchDetails(query))
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    if len(response.data.items) > 0:
        new_items = []
        for item in response.data.items:
            new_item = {}
            new_item["resource_type"]   = item.resource_type
            new_item["display_name"]    = item.display_name
            new_item["identifier"]      = item.identifier
            new_item["lifecycle_state"] = item.lifecycle_state
            new_items.append(new_item)

        sorted_items = sorted(new_items, key=lambda d: d['resource_type']) 

        for item in sorted_items:
            print (f"{item['resource_type']:30s}, {item['identifier']:110s}, {item['display_name']}, {item['lifecycle_state']}")

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Search resources in an OCI compartment")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-c", "--compartment", help="Compartment name or compartment OCID", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
parser.add_argument("-nc", "--no_color", help="Disable colored output", action="store_true")
args = parser.parse_args()

profile         = args.profile
cpt             = args.compartment
all_regions     = args.all_regions
if args.no_color:
  disable_colored_output()

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

# -- search objects
if not(all_regions):
    search_objects()
else:
    print (COLOR_TITLE1+"==================== List of subscribed regions in tenancy "+COLOR_NORMAL)
    for region in regions:
        print (region.region_name)

    for region in regions:
        config["region"] = region.region_name
        print (COLOR_TITLE1+"---------- region "+COLOR_COMP+config["region"]+COLOR_NORMAL)
        search_objects()

# -- the end
exit (0)
