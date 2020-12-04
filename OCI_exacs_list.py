#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------
# This script lists all Exadata Infrastructure for Exadata DB systems in a OCI tenant using OCI Python SDK 
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-12: Initial Version
# ---------------------------------------------------------------------------------------------------------------


# -- import
import oci
import sys

# ---------- Colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
colored_output=True
if (colored_output):
    COLOR_YELLOW="\033[93m"
    COLOR_RED="\033[91m"
    COLOR_GREEN="\033[32m"
    COLOR_NORMAL="\033[39m"
    COLOR_CYAN="\033[96m"
    COLOR_BLUE="\033[94m"
    COLOR_GREY="\033[90m"
else:
    COLOR_YELLOW=""
    COLOR_RED=""
    COLOR_GREEN=""
    COLOR_NORMAL=""
    COLOR_CYAN=""
    COLOR_BLUE=""
    COLOR_GREY=""

# -- variables
configfile = "~/.oci/config"    # Define config file to be used.
show_ocids = False  # or True

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

def get_cpt_name_from_id(cpt_id):
    """
    Get the complete name of a compartment from its id, including parent and grand-parent..
    """
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

def list_databases(lconfig, ldbh_id, lcpt_id):
    """
    List Databases attached to a given DB home and given compartement
    """
    DatabaseClient = oci.database.DatabaseClient(lconfig)
    response = DatabaseClient.list_databases(compartment_id=lcpt_id, db_home_id=ldbh_id)
    for db in response.data:
        print ("                   DB : "+COLOR_BLUE+f"{db.db_name:20s} "+COLOR_NORMAL+f"{db.db_workload:20s}", end="")
        if db.lifecycle_state == "AVAILABLE":
            print (COLOR_GREEN, end="")
        else:
            print (COLOR_RED, end="")
        print (f"{db.lifecycle_state:45s} "+COLOR_NORMAL, end="")
        if show_ocids:
            print (f"{db.id} ")
        else:
            print ("")


def list_dbhomes(lconfig, lvm_cluster_id, lcpt_id):
    """
    List Oracle DB Homes in a given VM cluster and given compartement
    """
    DatabaseClient = oci.database.DatabaseClient(lconfig)
    response = DatabaseClient.list_db_homes(lcpt_id)
    for dbh in response.data:
        if dbh.vm_cluster_id == lvm_cluster_id:
            print ("              DB home : "+COLOR_CYAN+f"{dbh.display_name:20s} "+COLOR_YELLOW+f"{dbh.db_version:20s}"+COLOR_NORMAL+f"{dbh.db_home_location:45s} ",end="")
            if show_ocids:
                print (f"{dbh.id} ")
            else:
                print ("")
            list_databases (lconfig, dbh.id, lcpt_id)

def list_vm_clusters(lconfig, exa_infra_id):
    """
    List VM clusters in a given Exadata Infrastructure
    """
    # Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
    query = f"query vmcluster resources"

    DatabaseClient = oci.database.DatabaseClient(lconfig)

    SearchClient = oci.resource_search.ResourceSearchClient(lconfig)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        response2 = DatabaseClient.get_cloud_vm_cluster(item.identifier)
        vm_cluster = response2.data
        if vm_cluster.cloud_exadata_infrastructure_id == exa_infra_id:
            print ("          VM cluster  : "+COLOR_RED+f"{item.display_name:40s} ",end="")
            if item.lifecycle_state  == "AVAILABLE":
                print (COLOR_GREEN, end="")
            else:
                print (COLOR_RED, end="")
            print (f"{item.lifecycle_state:45s} "+COLOR_NORMAL, end="")
            if show_ocids:
                print (COLOR_NORMAL+f"{item.identifier} ")
            else:
                print ("")
            list_dbhomes (lconfig, vm_cluster.id, vm_cluster.compartment_id)


def search_exa_infra (lconfig):
    """
    Search Exadata Infrastructures in all compartments in a region 
    """
    # Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
    query = "query cloudexadatainfrastructure resources"

    region = config["region"]

    SearchClient = oci.resource_search.ResourceSearchClient(lconfig)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        if item.lifecycle_state != "TERMINATED":
            print ("")
            print ("EXADATA INFRASTRUCTURE: "+COLOR_RED+f"{item.display_name:40s} "+COLOR_YELLOW+f"{item.lifecycle_state:45s} "+COLOR_NORMAL,end="")
            if show_ocids:
                print (f"{item.identifier} ")
            else:
                print ("")
            print ("          region      : "+COLOR_CYAN+f"{region}"+COLOR_NORMAL)
            print ("          compartment : "+COLOR_GREEN+f"{cpt_name}"+COLOR_NORMAL)
            list_vm_clusters (lconfig, item.identifier)
        else:
            print ("")
            print (COLOR_GREY+"EXADATA INFRASTRUCTURE: "+COLOR_BLUE+f"{item.display_name:40s} "+COLOR_RED+f"{item.lifecycle_state:45s}"+COLOR_GREY,end="")
            if show_ocids:
                print (f"{item.identifier} ")
            else:
                print ("")
            print ("          region      : "+COLOR_BLUE+f"{region}"+COLOR_GREY)
            print ("          compartment : "+COLOR_BLUE+f"{cpt_name}"+COLOR_NORMAL)     

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

# -- Run the search query/queries
if not(all_regions):
    search_exa_infra (config)
else:
    for region in regions:
        config["region"]=region.region_name
        search_exa_infra (config)

# -- the end
exit (0)
