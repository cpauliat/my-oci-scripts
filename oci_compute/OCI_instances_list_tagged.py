#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script looks for compute instances in all compartments in an OCI tenant in one region or all subscribed regions
# and lists the tag values for the ones having specific tag namespace and tag key
# 
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-16: Initial Version
#    2020-04-24: rewrite of the script using OCI search (much faster)
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] -p OCI_PROFILE -n tag_namespace -k tag_key".format(sys.argv[0]))
    print ("")
    print ("    By default, only the compute instances in the region provided in the profile are listed")
    print ("    If -a is provided, the compute instances from all subscribed regions are listed")
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

# ---- Get the name of compartment from its id
def get_cpt_name_from_id(cpt_id):
    for c in compartments:
        if (c.id == cpt_id):
            return c.name
    return "root"

# ---- Search resources in all compartments in a region
def search_resources():
    SearchClient = oci.resource_search.ResourceSearchClient(config)

    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        tag = tag_ns+"."+tag_key+" = "+item.defined_tags[tag_ns][tag_key]
        print ("{:s}, {:s}, {:s}, {:s}, {:s}".format(config['region'], cpt_name, item.display_name, item.identifier, tag))

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List compute instances tagged with a specific defined tag key")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-n", "--tag_ns", help="Tag namespace", required=True)
parser.add_argument("-k", "--tag_key", help="Tag key", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
args = parser.parse_args()
    
profile     = args.profile
tag_ns      = args.tag_ns
tag_key     = args.tag_key
all_regions = args.all_regions

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- get compartments list
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query instance resources where (definedTags.namespace = '{:s}' && definedTags.key = '{:s}')".format(tag_ns, tag_key)

# -- Get the resources
print ("Region, Compartment, Display Name, OCID, Tag")

if all_regions:
    for region in regions:
        config["region"]=region.region_name
        search_resources()
else:
    search_resources()

# -- the end
exit (0)
