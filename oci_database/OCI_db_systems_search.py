#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists all database systems in a OCI tenant using OCI Python SDK and search queries
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-09-18: Initial Version
# --------------------------------------------------------------------------------------------------------------


# -- import
import oci
import sys

# -- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -- functions
def usage():
    print ("Usage: {} [-a] OCI_PROFILE".format(sys.argv[0]))
    print ("")
    print ("    If -a is provided, the script search in all active regions instead of single region provided in profile")
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

# -- Get the complete name of a compartment from its id, including parent and grand-parent..
def get_cpt_name_from_id(cpt_id):
    global compartments

    if cpt_id == RootCompartmentID:
        return "root"

    name=""
    for c in compartments:
        if (c.id == cpt_id):
            name=c.name
    
            # if the cpt is a direct child of root compartment, return name
            if c.compartment_id == RootCompartmentID:
                return name
            # otherwise, find name of parent and add it as a prefix to name
            else:
                name = get_cpt_name_from_id(c.compartment_id)+":"+name
                return name


# ---------- main

# -- parse arguments
all_regions=False

if (len(sys.argv) != 2) and (len(sys.argv) != 3):
    usage()

if (len(sys.argv) == 2):
    profile = sys.argv[1] 
elif (len(sys.argv) == 3):
    profile = sys.argv[2]
    if (sys.argv[1] == "-a"):
        all_regions=True
    else:
        usage()
    
#print ("profile = {}".format(profile))

# -- get info from profile
try:
    config = oci.config.from_file(configfile,profile)

except:
    print ("ERROR: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- Get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Columns title
print ("Region, Compartment, Name, OCID, Status")

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query dbsystem resources"

# -- Run the search query/queries
if not(all_regions):
    #response = oci.pagination.list_call_get_all_results(SearchClient.search_resources, oci.resource_search.models.StructuredSearchDetails(query))
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        print ("{:s}, {:s}, {:s}, {:s}, {:s}".format(config["region"], cpt_name, item.display_name, item.identifier, item.lifecycle_state))
else:
    for region in regions:
        config["region"]=region.region_name
        SearchClient = oci.resource_search.ResourceSearchClient(config)
        response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
        for item in response.data.items:
            cpt_name = get_cpt_name_from_id(item.compartment_id)
            print ("{:s}, {:s}, {:s}, {:s}, {:s}".format(config["region"], cpt_name, item.display_name, item.identifier, item.lifecycle_state))


# -- the end
exit (0)
