#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------
# This script lists all Exadata Infrastructure for Exadata DB systems in a OCI tenant using OCI Python SDK 
# 
# THIS SCRIPT MUST BE EXECUTED FROM AN OCI COMPUTE INSTANCE WITH INSTANCE PRINCIPAL PERMISSIONS
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
# Versions
#    2020-12-11: Initial Version
#    2022-01-03: use argparse to parse arguments
#    2022-01-04: add --no_color option
# ---------------------------------------------------------------------------------------------------------------


# -------- import
import oci
import sys
import argparse

# -------- colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLOR_YELLOW="\033[93m"
COLOR_RED="\033[91m"
COLOR_GREEN="\033[32m"
COLOR_NORMAL="\033[39m"
COLOR_CYAN="\033[96m"
COLOR_BLUE="\033[94m"
COLOR_GREY="\033[90m"

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-nc] [-a] [-v]".format(sys.argv[0]))
    print ("")
    print ("    -v : also display OCIDs")
    print ("    -a : search in all active regions instead of single region provided in profile")
    print ("    -nc: disable colored output")
    print ("")
    exit (1)

# ---- Disable colored output
def disable_colored_output():
    global COLOR_YELLOW
    global COLOR_RED
    global COLOR_GREEN
    global COLOR_NORMAL
    global COLOR_CYAN
    global COLOR_BLUE
    global COLOR_GREY

    COLOR_YELLOW = ""
    COLOR_RED    = ""
    COLOR_GREEN  = ""
    COLOR_NORMAL = ""
    COLOR_CYAN   = ""
    COLOR_BLUE   = ""
    COLOR_GREY   = ""

# ---- Get the complete name of compartment from its id
def get_cpt_name_from_id(cpt_id):
    """
    Get the complete name of a compartment from its id, including parent and grand-parent..
    """

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

def list_databases(lsigner, ldbh_id, lcpt_id):
    """
    List Databases attached to a given DB home and given compartement
    """
    DatabaseClient = oci.database.DatabaseClient(config={}, signer=lsigner)
    response = DatabaseClient.list_databases(compartment_id=lcpt_id, db_home_id=ldbh_id)
    for db in response.data:
        print ("                   DB : "+COLOR_BLUE+f"{db.db_name:25s} "+COLOR_NORMAL+f"{db.db_workload:15s}", end="")
        if db.lifecycle_state == "AVAILABLE":
            print (COLOR_GREEN, end="")
        else:
            print (COLOR_RED, end="")
        print (f"{db.lifecycle_state:45s} "+COLOR_NORMAL, end="")
        if show_ocids:
            print (f"{db.id} ")
        else:
            print ("")


def list_dbhomes(lsigner, lvm_cluster_id, lcpt_id):
    """
    List Oracle DB Homes in a given VM cluster and given compartement
    """
    DatabaseClient = oci.database.DatabaseClient(config={}, signer=lsigner)
    response = DatabaseClient.list_db_homes(lcpt_id)
    for dbh in response.data:
        if dbh.vm_cluster_id == lvm_cluster_id:
            print ("              DB home : "+COLOR_CYAN+f"{dbh.display_name:25s} "+COLOR_YELLOW+f"{dbh.db_version:15s}"+COLOR_NORMAL+f"{dbh.db_home_location:45s} ",end="")
            if show_ocids:
                print (f"{dbh.id} ")
            else:
                print ("")
            list_databases (lsigner, dbh.id, lcpt_id)

def list_vm_clusters(lsigner, exa_infra_id):
    """
    List VM clusters in a given Exadata Infrastructure
    """
    # Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
    query = f"query vmcluster resources"

    DatabaseClient = oci.database.DatabaseClient(config={}, signer=lsigner)

    SearchClient = oci.resource_search.ResourceSearchClient(config={}, signer=lsigner)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        response2 = DatabaseClient.get_cloud_vm_cluster(item.identifier)
        vm_cluster = response2.data
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        if vm_cluster.cloud_exadata_infrastructure_id == exa_infra_id:
            if vm_cluster.lifecycle_state == "AVAILABLE":
                COLOR_STATUS = COLOR_GREEN
            else:
                COLOR_STATUS = COLOR_YELLOW
            print ("          VM cluster  : "+COLOR_RED+f"{vm_cluster.display_name:25s} "+COLOR_YELLOW+f"{vm_cluster.cpu_core_count:3} OCPUs      ",end="")
            print (COLOR_STATUS+f"{vm_cluster.lifecycle_state:45s} "+COLOR_NORMAL, end="")
            if show_ocids:
                print (COLOR_NORMAL+f"{vm_cluster.id} ")
            else:
                print ("")
            print ("                  cpt : "+COLOR_GREEN+f"{cpt_name} "+COLOR_NORMAL)
            list_dbhomes (lsigner, vm_cluster.id, vm_cluster.compartment_id)


def search_exa_infra (lsigner):
    """
    Search Exadata Infrastructures in all compartments in a region 
    """
    # Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
    query = "query cloudexadatainfrastructure resources"

    region = signer.region

    DatabaseClient = oci.database.DatabaseClient(config={}, signer=lsigner)

    SearchClient = oci.resource_search.ResourceSearchClient(config={}, signer=lsigner)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        if item.lifecycle_state != "TERMINATED":
            response2 = DatabaseClient.get_cloud_exadata_infrastructure(item.identifier)
            exa_infra = response2.data
            cpt_name = get_cpt_name_from_id(item.compartment_id)
            if exa_infra.lifecycle_state == "TERMINATED":
                continue
            elif exa_infra.lifecycle_state == "AVAILABLE":
                COLOR_STATUS = COLOR_GREEN
            else:
                COLOR_STATUS = COLOR_YELLOW
            print ("")
            print ("EXADATA INFRASTRUCTURE: "+COLOR_RED+f"{exa_infra.display_name:40s} "+COLOR_STATUS+f"{exa_infra.lifecycle_state:45s} "+COLOR_NORMAL,end="")
            if show_ocids:
                print (f"{exa_infra.id} ")
            else:
                print ("")
            print ("          region      : "+COLOR_CYAN+f"{region}"+COLOR_NORMAL)
            print ("          compartment : "+COLOR_GREEN+f"{cpt_name}"+COLOR_NORMAL)
            list_vm_clusters (lsigner, exa_infra.id)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List machines in Exadata Cloud Service")
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
parser.add_argument("-v", "--verbose", help="Verbose mode: display OCIDs", action="store_true")
parser.add_argument("-nc", "--no_color", help="Disable colored output", action="store_true")
args = parser.parse_args()
    
all_regions   = args.all_regions
show_ocids    = args.verbose
if args.nocolor:
  disable_colored_output()

# -- authentication using instance principal
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
IdentityClient = oci.identity.IdentityClient(config={}, signer=signer)
RootCompartmentID = signer.tenancy_id

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- Get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Run the search query/queries
if not(all_regions):
    search_exa_infra (signer)
else:
    for region in regions:
        signer.region=region.region_name
        search_exa_infra (signer)

# -- the end
exit (0)
