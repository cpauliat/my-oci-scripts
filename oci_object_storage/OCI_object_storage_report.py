#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script computes the total capacity of object storage used in buckets in each compartment in a region or all active regions
# using OCI Python SDK
# Note: it does not include object storage consumed by backups or custom images () 
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-21-12: Initial Version
#    2021-07-28: Fix usage() function, no compartment needed
#    2021-07-28: Add -a option for all regions
# ---------------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import operator

# ---------- Colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
colored_output=True
if (colored_output):
  COLOR_TITLE0="\033[95m"             # light magenta
  COLOR_TITLE1="\033[91m"             # light red
  COLOR_TITLE2="\033[32m"             # green
  COLOR_AD="\033[94m"                 # light blue
  COLOR_COMP="\033[93m"               # light yellow
  COLOR_BREAK="\033[91m"              # light red
  COLOR_NORMAL="\033[39m"
else:
  COLOR_TITLE0=""
  COLOR_TITLE1=""
  COLOR_TITLE2=""
  COLOR_AD=""
  COLOR_COMP=""
  COLOR_BREAK=""
  COLOR_NORMAL=""

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] OCI_PROFILE".format(sys.argv[0]))
    print ("")
    print ("    By default, only the region provided in the profile is processed")
    print ("    If -a is provided, all subscribed regions are processed (by default, only the region in the profile is processed)")
    print ("")
    print ("note: Only compartments with more than 100 MB are displayed")
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

# -- Build the block storage report for one region then display it
def get_report_for_region():
        
    print ("--------------------------------------------------------------------------------------------------------------")

    # Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
    query_bucket = "query bucket resources"

    # Clients
    mb_used = {}
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    OSClient = oci.object_storage.ObjectStorageClient(config)
    total_mb_used = 0
    namespace = OSClient.get_namespace().data

    # Run the search query to get list of BLOCK volumes then for each volume, use get_volume() to get size
    # Finally store the result in a dictionary
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query_bucket))
    for item in response.data.items:
        if item.lifecycle_state != "TERMINATED":
            # as size is not returned by the query search, we need to get the size (approximate) of each bucket.
            my_fields = [ 'approximateSize' ]
            response2 = OSClient.get_bucket(namespace, item.display_name, fields=my_fields)
            bucket = response2.data
            if bucket.approximate_size != None:
                if mb_used.get(item.compartment_id) == None:
                    mb_used[item.compartment_id] = int(bucket.approximate_size / 1024 / 1024)
                else:
                    mb_used[item.compartment_id] += int(bucket.approximate_size / 1024 / 1024)
                # if details:
                #     cpt_name = get_cpt_name_from_id(bucket.compartment_id)
                #     print (f"- {bucket.approximate_size / 1024 / 1024 / 1024:7.1f} GBs, {bucket.name:30s}, {cpt_name}")
                total_mb_used += int(bucket.approximate_size / 1024 / 1024)

    # sort the dictionary by descending total size 
    mb_used_sorted = dict(sorted(mb_used.items(), key=operator.itemgetter(1), reverse=True))
    
    # display the result
    print (f"REGION {config['region']}: OBJECT STORAGE CONSUMPTION (buckets only) PER COMPARTMENT ",end="")
    print (f"Total =  {total_mb_used/1024:.0f} GBs = {total_mb_used/1024/1024:.1f} TBs")
    for cpt_id in mb_used_sorted.keys():
        cpt_name = get_cpt_name_from_id(cpt_id)
        mb = mb_used_sorted[cpt_id]
        # compartments with less than 100 MB are not displayed
        if mb > 100:
            print (f"- {mb/1024:6.1f} GBs, {cpt_name} ")
    print ("")

# ------------ main

# -- parse arguments
all_regions = False

if len(sys.argv) == 2:
    profile  = sys.argv[1]
elif len(sys.argv) == 3:
    profile  = sys.argv[2]
    if sys.argv[1] == "-a":
        all_regions = True
    else:
        usage ()
else:
    usage()

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

# -- Build and print object storage reports for regions
if not(all_regions):
    get_report_for_region()
else:
    for region in regions:
        config["region"] = region.region_name
        get_report_for_region()

# -- the end
exit (0)

# ------------

# # -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
# query_bucket = "query bucket resources"
# query_boot_volume  = "query bootvolume resources"

# # -- Clients
# mb_used = {}
# SearchClient = oci.resource_search.ResourceSearchClient(config)
# OSClient = oci.object_storage.ObjectStorageClient(config)
# details = False
# total_mb_used = 0
# namespace = OSClient.get_namespace().data

# # -- Run the search query to get list of BUCKETS then for bucket, use get_bucket() to get approximate size
# # -- Finally store the result in a dictionary
# if details:
#     print ("LIST OF OBJECT STORAGE BUCKETS:")
#     print (f"- Approx Size, {'Bucket Name':30s}, Compartment")

# response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query_bucket))
# for item in response.data.items:
#     if item.lifecycle_state != "TERMINATED":
#         # as size is not returned by the query search, we need to get the size (approximate) of each bucket.
#         my_fields = [ 'approximateSize' ]
#         response2 = OSClient.get_bucket(namespace, item.display_name, fields=my_fields)
#         bucket = response2.data
#         if bucket.approximate_size != None:
#             if mb_used.get(item.compartment_id) == None:
#                 mb_used[item.compartment_id] = int(bucket.approximate_size / 1024 / 1024)
#             else:
#                 mb_used[item.compartment_id] += int(bucket.approximate_size / 1024 / 1024)
#             if details:
#                 cpt_name = get_cpt_name_from_id(bucket.compartment_id)
#                 print (f"- {bucket.approximate_size / 1024 / 1024 / 1024:7.1f} GBs, {bucket.name:30s}, {cpt_name}")
#             total_mb_used += int(bucket.approximate_size / 1024 / 1024)

# # -- sort the dictionary by descending total size 
# mb_used_sorted = dict(sorted(mb_used.items(), key=operator.itemgetter(1), reverse=True))

# # -- display the result
# if details:
#     print ("")

# print (f"OBJECT STORAGE CONSUMPTION PER COMPARTMENT IN REGION {config['region']}: ",end="")
# print (f"Total =  {total_mb_used/1024:.1f} GBs = {total_mb_used/1024/1024:.1f} TBs")
# for cpt_id in mb_used_sorted.keys():
#     cpt_name = get_cpt_name_from_id(cpt_id)
#     mb = mb_used_sorted[cpt_id]
#     if mb > 100:
#         print (f"- {mb/1024:6.1f} GBs, {cpt_name} ")

# # -- the end
# exit (0)