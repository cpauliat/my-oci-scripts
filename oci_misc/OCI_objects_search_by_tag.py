#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script looks for OCI resources having a specific defined tag key and value 
# it looks in all compartments in a OCI tenant in a region using OCI CLI
# 
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-24: Initial Version
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
    print ("Usage: {} -p OCI_PROFILE -n tag_namespace -k tag_key -vl tag_value".format(sys.argv[0]))
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

# -- Get the name of a compartment from its id
def get_cpt_name_from_id(cpt_id):
    for c in compartments:
        if (c.id == cpt_id):
            return c.name
    return "root"

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Search OCI resources by tag")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-n", "--tag_ns", help="Tag namespace", required=True)
parser.add_argument("-k", "--tag_key", help="Tag key", required=True)
parser.add_argument("-vl", "--tag_value", help="Tag value", required=True)
args = parser.parse_args()

profile     = args.profile
tag_ns      = args.tag_ns
tag_key     = args.tag_key
tag_value   = args.tag_value

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query all resources where (definedTags.namespace = '{:s}' && definedTags.key = '{:s}' && definedTags.value = '{:s}')".format(tag_ns, tag_key, tag_value)

# -- Get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Get the resources
SearchClient = oci.resource_search.ResourceSearchClient(config)

#response = oci.pagination.list_call_get_all_results(SearchClient.search_resources, oci.resource_search.models.StructuredSearchDetails(query))
response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
if len(response.data.items) > 0:
    print ("Resource Type, Compartment, Display Name, OCID")
for item in response.data.items:
    cpt_name = get_cpt_name_from_id(item.compartment_id)
    print ("{:s}, {:s}, {:s}, {:s}".format(item.resource_type, cpt_name, item.display_name, item.identifier))

# -- the end
exit (0)
