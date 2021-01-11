#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script lists ContainerEngine(aka OKE) clusters in a region or all active regions using OCI Python SDK
#
# Note: OCI tenant and region given retrieved automatically by CloudShell
#
# Note: There is no query search for OKE clusters at this point, so workaround is to look to compute instance "oke-"
# then for each compartment containing such instance, look for OKE clusters
#
# Author        : Christophe Pauliat
# Platforms     : OCI CloudShell
#
# prerequisites : - Python 3 with OCI Python SDK installed
#
# # Versions
#    2021-01-11: Initial Version
# ---------------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys

# ---------- Functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-a]".format(sys.argv[0]))
    print ("")
    print ("    If -a is provided, the OKE containers from all subscribed regions are listed")
    print ("")
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

# ---- Look for OKE clusters in the given compartment ID
def process_compartment (lcpt_id):
    global clusters_ids

    region  = config["region"]

    # look for OKE clusters
    ContainerEngineClient = oci.container_engine.ContainerEngineClient(config)
    response = oci.pagination.list_call_get_all_results(ContainerEngineClient.list_clusters,compartment_id=lcpt_id)
    if len(response.data) > 0:
        for cluster in response.data:
            if not(cluster.id in clusters_ids):
                clusters_ids.append(cluster.id)
                cpt_name = get_cpt_name_from_id(lcpt_id)
                print (f"{region}, {cpt_name}, {cluster.id}, {cluster.name}, {cluster.lifecycle_state}")

# ------------ main

# -- parse arguments
all_regions = False


if len(sys.argv) == 2:
    if sys.argv[1] == "-a":
        all_regions = True
    else:
        usage ()
elif len(sys.argv) != 1:
    usage()

# -- get config from CloudShell
try:
    config = oci.config.from_file()
except:
    print ("ERROR 02: cannot get config")
    exit (2)

# -- get list of compartments
RootCompartmentID = config.tenancy
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- list of clusters IDs already found
clusters_ids = []

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query instance resources where displayName =~ 'oke'"

# -- Run the search query/queries to find all OKE compute instances in the region/regions
# -- then get details about OKE clusters
if not(all_regions):
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        process_compartment (item.compartment_id)
else:
    for region in regions:
        config["region"]=region.region_name
        SearchClient = oci.resource_search.ResourceSearchClient(config)
        response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
        for item in response.data.items:
            cpt_name = get_cpt_name_from_id(item.compartment_id)
            process_compartment (item.compartment_id)

# -- the end
exit (0)
