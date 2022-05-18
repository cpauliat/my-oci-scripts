#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------
# This script lists all Exadata Infrastructure for Exadata Cloud at Customer in a OCI tenant using OCI Python SDK 
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-01-12: Initial Version
#    2022-01-03: use argparse to parse arguments
#    2022-01-04: add --no_color option
#    2022-05-18: add --show_ocids option
#    2022-05-18: display vm clusters, db homes and databases in a tree format
# ---------------------------------------------------------------------------------------------------------------


# -------- import
import oci
import sys
import argparse
import json

# -------- colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLOR_YELLOW  = "\033[93m"
COLOR_RED     = "\033[91m"
COLOR_GREEN   = "\033[32m"
COLOR_NORMAL  = "\033[39m"
COLOR_CYAN    = "\033[96m"
COLOR_BLUE    = "\033[94m"
COLOR_GREY    = "\033[90m"
COLOR_MAGENTA = "\033[35m"

# -------- global variables
configfile      = "~/.oci/config"    # Define config file to be used.
SearchClient    = ""
DatabaseClient  = ""
last_vm_cluster = False
last_db_home    = False
last_database   = False

# -------- functions

# ---- Disable colored output
def disable_colored_output():
    global COLOR_YELLOW
    global COLOR_RED
    global COLOR_GREEN
    global COLOR_NORMAL
    global COLOR_CYAN
    global COLOR_BLUE
    global COLOR_GREY
    global COLOR_MAGENTA

    COLOR_YELLOW  = ""
    COLOR_RED     = ""
    COLOR_GREEN   = ""
    COLOR_NORMAL  = ""
    COLOR_CYAN    = ""
    COLOR_BLUE    = ""
    COLOR_GREY    = ""
    COLOR_MAGENTA = ""


# ---- Get the complete name of a compartment from its id
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

# ---- Display details about an Exadata infrastructure (VM clusters, DB homes and CDBs)
# def display_pdbs(pdbs):
#     global last_pdb

#     for index in range(len(pdbs)):
#         pdb = pdbs[index]
#         last_pdb = (index == len(pdbs)-1)

#         if last_vm_cluster:
#             if last_db_home:
#                 if last_database:
#                     if last_pdb:
#                         print (COLOR_CYAN+"               └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"               ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                 else:
#                     if last_pdb:
#                         print (COLOR_CYAN+"          │    └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"          │    ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#             else:
#                 if last_database:
#                     if last_pdb:
#                         print (COLOR_CYAN+"     │         └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"     │         ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                 else:
#                     if last_pdb:
#                         print (COLOR_CYAN+"     │    │    └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"     │    │    ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#         else:
#             if last_db_home:
#                 if last_database:
#                     if last_pdb:
#                         print (COLOR_CYAN+"│              └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"│              ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                 else:
#                     if last_pdb:
#                         print (COLOR_CYAN+"│         │    └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"│         │    ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#             else:
#                 if last_database:
#                     if last_pdb:
#                         print (COLOR_CYAN+"│    │         └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"│    │         ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                 else:
#                     if last_pdb:
#                         print (COLOR_CYAN+"│    │    │    └─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")
#                     else:
#                         print (COLOR_CYAN+"│    │    │    ├─── "+COLOR_NORMAL+"PDB: "+COLOR_BLUE+f"{pdb['pdb_name']:20s} "+COLOR_NORMAL+f"{pdb['open_mode']:20s}", end="")


#         if pdb['lifecycle_state'] == "AVAILABLE":
#             print (COLOR_GREEN, end="")
#         else:
#             print (COLOR_RED, end="")
#         print (f"{pdb['lifecycle_state']:45s} "+COLOR_NORMAL, end="")
#         if show_ocids:
#             print (f"{pdb['id']} ")
#         else:
#             print ("")

def display_databases(databases):
    global last_database

    for index in range(len(databases)):
        db = databases[index]
        last_database = (index == len(databases)-1)

        if last_vm_cluster:
            if last_db_home:
                if last_database:
                    print (COLOR_CYAN+"          └─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")
                else:
                    print (COLOR_CYAN+"          ├─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")
            else:
                if last_database:
                    print (COLOR_CYAN+"     │    └─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")
                else:
                    print (COLOR_CYAN+"     │    ├─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")
        else:
            if last_db_home:
                if last_database:
                    print (COLOR_CYAN+"│         └─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")
                else:
                    print (COLOR_CYAN+"│         ├─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")
            else:
                if last_database:
                    print (COLOR_CYAN+"│    │    └─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")
                else:
                    print (COLOR_CYAN+"│    │    ├─── "+COLOR_NORMAL+"CDB     : "+COLOR_MAGENTA+f"{db['db_name']:20s} "+COLOR_NORMAL+f"{db['db_workload']:20s}", end="")

        if db['lifecycle_state'] == "AVAILABLE":
            print (COLOR_GREEN, end="")
        else:
            print (COLOR_RED, end="")
        print (f"{db['lifecycle_state']:45s} "+COLOR_NORMAL, end="")
        if show_ocids:
            print (f"{db['id']} ")
        else:
            print ("")
        
        # display_pdbs (db["pdbs"])

def display_db_homes(db_homes):
    global last_db_home

    for index in range(len(db_homes)):
        db_home = db_homes[index]
        last_db_home = (index == len(db_homes)-1)

        # db home location may be None if db home is provisioning
        db_home_location = db_home['db_home_location']
        if db_home_location == None:
            db_home_location = "<db home location not yet known>"

        try:
            if last_vm_cluster:
                if last_db_home:
                    print (COLOR_CYAN+"     └─── "+COLOR_NORMAL+"DB home      : "+COLOR_CYAN+f"{db_home['display_name']:20s} "+COLOR_YELLOW+f"{db_home['db_version']:20s}"+COLOR_NORMAL+f"{db_home_location:45s} ",end="")
                else:
                    print (COLOR_CYAN+"     ├─── "+COLOR_NORMAL+"DB home      : "+COLOR_CYAN+f"{db_home['display_name']:20s} "+COLOR_YELLOW+f"{db_home['db_version']:20s}"+COLOR_NORMAL+f"{db_home_location:45s} ",end="")
            else:
                if last_db_home:
                    print (COLOR_CYAN+"│    └─── "+COLOR_NORMAL+"DB home      : "+COLOR_CYAN+f"{db_home['display_name']:20s} "+COLOR_YELLOW+f"{db_home['db_version']:20s}"+COLOR_NORMAL+f"{db_home_location:45s} ",end="")
                else:
                    print (COLOR_CYAN+"│    ├─── "+COLOR_NORMAL+"DB home      : "+COLOR_CYAN+f"{db_home['display_name']:20s} "+COLOR_YELLOW+f"{db_home['db_version']:20s}"+COLOR_NORMAL+f"{db_home_location:45s} ",end="")
        except Exception as err:
            print ("DEBUG: ERROR: display_db_homes(), err=",err)
            print ("DEBUG: db_home['display_name']     = ",db_home['display_name'])
            print ("DEBUG: db_home['db_version']       = ",db_home['db_version'])
            print ("DEBUG: db_home['db_home_location'] = ",db_home['db_home_location'])

        if show_ocids:
            print (f"{db_home['id']} ")
        else:
            print ("")

        display_databases (db_home["databases"])

def display_vm_clusters(vm_clusters):
    global last_vm_cluster

    for index in range(len(vm_clusters)):
        vm_cluster = vm_clusters[index]
        last_vm_cluster = (index == len(vm_clusters)-1)

        if last_vm_cluster:
            print (COLOR_CYAN+"└─── "+COLOR_NORMAL+"VM cluster        : "+COLOR_RED+f"{vm_cluster['display_name']:40s} ",end="")
        else:
            print (COLOR_CYAN+"├─── "+COLOR_NORMAL+"VM cluster        : "+COLOR_RED+f"{vm_cluster['display_name']:40s} ",end="")

        if vm_cluster['lifecycle_state']  == "AVAILABLE":
            print (COLOR_GREEN, end="")
        else:
            print (COLOR_RED, end="")

        print (f"{vm_cluster['lifecycle_state']:45s} "+COLOR_NORMAL, end="")

        if show_ocids:
            print (COLOR_NORMAL+f"{vm_cluster['id']} ")
        else:
            print ("")

        display_db_homes (vm_cluster["db_homes"])

# ---- Get details about an Exadata infrastructure (VM clusters, DB homes, CDBs and PDBs)
# def get_pdbs(ldb_id):
#     pdbs = []

#     # response = DatabaseClient.list_pluggable_databases(database_id=ldb_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
#     # for pdb in response.data:
#     #     pdb_light = {}
#     #     pdb_light["pdb_name"]        = pdb.pdb_name
#     #     pdb_light["open_mode"]       = pdb.open_mode
#     #     pdb_light["lifecycle_state"] = pdb.lifecycle_state
#     #     pdb_light["id"]              = pdb.id
#     #     pdbs.append(pdb_light)

#     # - TEST
#     # pdb_light = {}
#     # pdb_light["pdb_name"]        = "PDB1"
#     # pdb_light["open_mode"]       = "READ/WRITE"
#     # pdb_light["lifecycle_state"] = "AVAILABLE"
#     # pdb_light["id"]              = "ocid.pdb1.xxxx"
#     # pdbs.append(pdb_light)
#     # pdbs.append(pdb_light)

#     # returned value
#     return pdbs

def get_databases(ldbh_id, lcpt_id):
    databases = []
    response = DatabaseClient.list_databases(compartment_id=lcpt_id, db_home_id=ldbh_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for db in response.data:
        database_light = {}
        database_light["db_name"]         = db.db_name
        database_light["db_workload"]     = db.db_workload
        database_light["lifecycle_state"] = db.lifecycle_state
        database_light["id"]              = db.id
        # database_light["pdbs"]            = get_pdbs (db.id)
        databases.append(database_light)
    # returned value
    return databases

def get_db_homes(lvm_cluster_id, lcpt_id):
    db_homes = []
    response = DatabaseClient.list_db_homes(lcpt_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for dbh in response.data:
        dh_home_light = {}
        if dbh.vm_cluster_id == lvm_cluster_id:
            dh_home_light["display_name"]     = dbh.display_name
            dh_home_light["db_version"]       = dbh.db_version
            dh_home_light["id"]               = dbh.id
            dh_home_light["db_home_location"] = dbh.db_home_location
            dh_home_light["databases"]        = get_databases (dbh.id, lcpt_id)
            db_homes.append(dh_home_light)
    # returned value
    return db_homes

def get_vm_clusters(exa_infra_id):
    vm_clusters = []

    # Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
    query = f"query vmcluster resources"

    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        response2 = DatabaseClient.get_vm_cluster(item.identifier,retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
        vm_cluster = response2.data
        vm_cluster_light = {}
        if vm_cluster.exadata_infrastructure_id == exa_infra_id:
            vm_cluster_light["display_name"]    = item.display_name
            vm_cluster_light["id"]              = item.identifier
            vm_cluster_light["lifecycle_state"] = item.lifecycle_state
            vm_cluster_light["compartment_id"]  = vm_cluster.compartment_id
            vm_cluster_light["db_homes"]        = get_db_homes (vm_cluster.id, vm_cluster.compartment_id)
            vm_clusters.append(vm_cluster_light)
    # returned value
    return vm_clusters

# ---- Get list of Exadata infrastructure, then get and display details for each Exadata Infrastructure
def search_exa_infra (lconfig):
    global SearchClient
    global DatabaseClient

    region = lconfig["region"]
    SearchClient = oci.resource_search.ResourceSearchClient(lconfig)
    DatabaseClient = oci.database.DatabaseClient(lconfig)

    # Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
    query = "query exadatainfrastructure resources"
    response = SearchClient.search_resources(
            oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
            retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for exainfra in response.data.items:
        cpt_name = get_cpt_name_from_id(exainfra.compartment_id)  
        if exainfra.lifecycle_state != "TERMINATED":
            vm_clusters = get_vm_clusters(exainfra.identifier)
            print ("")
            print ("EXADATA INFRASTRUCTURE : "+COLOR_RED+f"{exainfra.display_name:40s} "+COLOR_YELLOW+f"{exainfra.lifecycle_state:45s} "+COLOR_NORMAL,end="")
            if show_ocids:
                print (f"{exainfra.identifier} ")
            else:
                print ("")

            print (COLOR_CYAN+"├─── "+COLOR_NORMAL+"region            : "+COLOR_CYAN+f"{region}"+COLOR_NORMAL)
            if len(vm_clusters) > 0:
                print (COLOR_CYAN+"├─── "+COLOR_NORMAL+"compartment       : "+COLOR_GREEN+f"{cpt_name}"+COLOR_NORMAL)
                display_vm_clusters (vm_clusters)
            else:
                print (COLOR_CYAN+"└─── "+COLOR_NORMAL+"compartment       : "+COLOR_GREEN+f"{cpt_name}"+COLOR_NORMAL)
        else:
            print ("")
            print (COLOR_GREY+"EXADATA INFRASTRUCTURE: "+COLOR_BLUE+f"{exainfra.display_name:40s} "+COLOR_RED+f"{exainfra.lifecycle_state:45s}"+COLOR_GREY,end="")
            if show_ocids:
                print (f"{exainfra.identifier} ")
            else:
                print ("")
            print (COLOR_CYAN+"├─── "+COLOR_NORMAL+"region            : "+COLOR_BLUE+f"{region}"+COLOR_GREY)
            print (COLOR_CYAN+"└─── "+COLOR_NORMAL+"compartment       : "+COLOR_BLUE+f"{cpt_name}"+COLOR_NORMAL)     

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List Exadata Cloud at Customers machines")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
parser.add_argument("-i", "--show_ocids", help="Show OCIDs", action="store_true")
parser.add_argument("-nc", "--no_color", help="Disable colored output", action="store_true")
args = parser.parse_args()
    
profile       = args.profile
all_regions   = args.all_regions
show_ocids    = args.show_ocids
if args.no_color:
  disable_colored_output()

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
response = oci.pagination.list_call_get_all_results(
    IdentityClient.list_region_subscriptions, 
    RootCompartmentID,
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
regions = response.data

# -- Get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(
    IdentityClient.list_compartments,
    RootCompartmentID,
    compartment_id_in_subtree=True,
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
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
