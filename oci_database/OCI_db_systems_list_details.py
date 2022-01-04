#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script looks for database systems in all compartments in an OCI tenant in one region 
# and lists db homes, databases and managed pluggables databases in those database systems
# 
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-09-24: Initial Version
#    2022-01-03: use argparse to parse arguments
#    2022-01-04: add --no_color option
# --------------------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse

# -------- colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLOR_YELLOW  = "\033[93m"
COLOR_RED     = "\033[91m"
COLOR_GREEN   = "\033[32m"
COLOR_CYAN    = "\033[96m"
COLOR_BLUE    = "\033[94m"
COLOR_GREY    = "\033[90m"
COLOR_DEFAULT = "\033[39m"
    
COLOR_DBS     = COLOR_YELLOW
COLOR_DB_HOME = COLOR_RED
COLOR_DB      = COLOR_CYAN
COLOR_PDB     = COLOR_GREEN
COLOR_CPT     = COLOR_CYAN
COLOR_NORMAL  = COLOR_DEFAULT

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-nc] -p OCI_PROFILE".format(sys.argv[0]))
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

# ---- Disable colored output
def disable_colored_output():
    global COLOR_DBS    
    global COLOR_DB_HOME 
    global COLOR_DB      
    global COLOR_PDB     
    global COLOR_CPT     
    global COLOR_NORMAL  

    COLOR_DBS     = ""
    COLOR_DB_HOME = ""
    COLOR_DB      = ""
    COLOR_PDB     = ""
    COLOR_CPT     = ""
    COLOR_NORMAL  = ""

# ---- Get the complete name of compartment from its id
def get_cpt_parent(cpt):
    if (cpt.id == RootCompartmentID):
        return "root"
    else:
        for c in compartments:
            if c.id == cpt.compartment_id:
                break
        return (c)

def cpt_full_name(cpt):
    if cpt.id == RootCompartmentID:
        return ""
    else:
        # if direct child of root compartment
        if cpt.compartment_id == RootCompartmentID:
            return cpt.name
        else:
            parent_cpt = get_cpt_parent(cpt)
            return cpt_full_name(parent_cpt)+":"+cpt.name

def get_cpt_full_name_from_id(cpt_id):
    if cpt_id == RootCompartmentID:
        return "root"
    else:
        for c in compartments:
            if (c.id == cpt_id):
                return cpt_full_name(c)
    return

# ---- Search resources in all compartments in a region
def search_resources():
    SearchClient   = oci.resource_search.ResourceSearchClient(config)
    DatabaseClient = oci.database.DatabaseClient (config)

    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for dbs in response.data.items:
        cpt_name = get_cpt_full_name_from_id(dbs.compartment_id)
        print ("")
        print ("---------- DB System "+COLOR_DBS+f"{dbs.display_name:20s}"+COLOR_NORMAL+f" (compartment "+COLOR_CPT+f"{cpt_name}"+COLOR_NORMAL+")")
        response2 = DatabaseClient.list_db_homes(compartment_id=dbs.compartment_id, db_system_id=dbs.identifier)
        for dbhome in response2.data:
            print ("- DB Home "+COLOR_DB_HOME+f"{dbhome.display_name:20s}"+COLOR_NORMAL+" ("+COLOR_DB_HOME+f"{dbhome.db_version}"+COLOR_NORMAL+")")
            response3 = DatabaseClient.list_databases(compartment_id=dbs.compartment_id, db_home_id=dbhome.id, system_id=dbs.identifier)
            for db in response3.data:
                print ("    - database "+COLOR_DB+f"{db.db_name:10s} "+COLOR_NORMAL,end="")
                try:
                    response4 = DatabaseClient.list_pluggable_databases(database_id=db.id)
                    print (COLOR_PDB+f" {len(response4.data)}"+COLOR_NORMAL+" pdb(s): "+COLOR_PDB,end='')
                    for pdb in response4.data:
                        print (f"{pdb.pdb_name} ",end="")
                    print (COLOR_NORMAL)
                except:
                    print ("")
                
# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List database systems details")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-nc", "--no_color", help="Disable colored output", action="store_true")
args = parser.parse_args()
    
profile = args.profile
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

# -- get compartments list
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query dbsystem resources"

# -- Search the resources
search_resources()

# -- the end
exit (0)
