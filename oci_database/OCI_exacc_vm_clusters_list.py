#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists all ExaCC VM clusters in a OCI tenant using OCI Python SDK 
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK (version 2.48 or later) installed
#                 - OCI config file configured with profiles
# Versions
#    2020-09-21: Initial Version
#    2021-11-30: Display number of db nodes in VM clusters
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------


# -------- import
import oci
import sys
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- usage syntax
def usage():
    print (f"Usage: {sys.argv[0]} [-a] -p OCI_PROFILE")
    print ( "")
    print ( "    If -a is provided, the script search in all active regions instead of single region provided in profile")
    print ( "")
    print (f"note: OCI_PROFILE must exist in {configfile} file (see example below)")
    print ( "")
    print ( "[EMEAOSC]")
    print ( "tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ( "user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ( "fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ( "key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ( "region      = eu-frankfurt-1")
    exit (1)

# ---- Get the complete name of a compartment from its id, including parent and grand-parent..
def get_cpt_name_from_id(cpt_id):

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

# ---- Print details for a VM cluster
def vmcluster_print_details (vmcluster_id, lcpt_name):

    # get details about vmcluster from regular API 
    DatabaseClient = oci.database.DatabaseClient(config)
    response = DatabaseClient.get_vm_cluster (vm_cluster_id = vmcluster_id)
    vmcluster = response.data

    # print details
    print (f"{config['region']}, {lcpt_name}, {vmcluster.display_name}, {vmcluster.id}, {vmcluster.lifecycle_state}, {len(vmcluster.db_servers)}, {vmcluster.cpus_enabled}")

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List ExaCC VM clusters in text format")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
args = parser.parse_args()

profile     = args.profile
all_regions = args.all_regions

# -- get info from profile    
try:
    config = oci.config.from_file(configfile,profile)

except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
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
print ("Region, Compartment, Name, OCID, Status, Number of DB nodes, OCPUs enabled")

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query vmcluster resources"

# -- Run the search query/queries
if not(all_regions):
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        vmcluster_print_details (item.identifier, cpt_name)
else:
    for region in regions:
        config["region"]=region.region_name
        SearchClient = oci.resource_search.ResourceSearchClient(config)
        response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
        for item in response.data.items:
            cpt_name = get_cpt_name_from_id(item.compartment_id)
            vmcluster_print_details (item.identifier, cpt_name)

# -- the end
exit (0)
