#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script looks for VM database systems with a specific tag key and stop (or start) them if the 
#     tag value for the tag key matches the current time.
# You can use it to automatically stop some VM database systems during non working hours
#     and start them again at the beginning of working hours to save cloud credits
# This script needs to be executed every hour during working days by an external scheduler 
#     (cron table on Linux for example)
# You can add the 2 tag keys to the default tags for root compartment so that every new VM database system 
#     get those 2 tag keys with default value ("off" or a specific UTC time)
#
# This script looks in all compartments in a OCI tenant in a region using OCI Python SDK
# Note: OCI tenant and region given by an OCI CLI PROFILE
#
# IMPORTANT: DOES NOT SUPPORT RAC VM DB SYSTEMS
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
#                 - OCI user with enough privileges to be able to read, stop and start compute instances (policy example below)
#                       allow group osc_stop_and_start to inspect db-systems in tenancy
#                       allow group osc_stop_and_start to manage db-nodes in tenancy
# Versions
#    2020-04-23: Initial Version
#    2020-09-17: bug fix (root compartment was ignored)
#    2021-01-08: Use a search query to accelerate the script
# ---------------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import os
from datetime import datetime

# ---------- Tag names, key and value to look for
# VM DB systems tagged using this will be stopped/started.
# Update these to match your tags.
tag_ns        = "osc"
tag_key_stop  = "automatic_shutdown"
tag_key_start = "automatic_startup"

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---------- Functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] [--confirm_stop] [--confirm_start] OCI_PROFILE".format(sys.argv[0]))
    print ("")
    print ("Notes:")
    print ("    If -a is provided, the script processes all active regions instead of singe region provided in profile")
    print ("    If --confirm_stop  is not provided, the VM database systems to stop are listed but not actually stopped")
    print ("    If --confirm_start is not provided, the VM database systems to start are listed but not actually started")
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

# ---- If needed, stop or start the autonomous database
def process_dbs (dbs_id, lcpt_name, lcpt_id):

    region  = config["region"] 

    # get details about database system from regular API 
    DatabaseClient = oci.database.DatabaseClient(config)
    response = DatabaseClient.get_db_system (dbs_id)
    dbs = response.data

    # we only care about VM (Virtual Machine) DB systems because stopping BM (Bare Metal) DB systems does not stop billing
    # so ignoring BM DB systems
    if dbs.shape[:2] != "VM":
        return

    # process VM DB system only if available (DBS is AVAILABLE even if DB nodes are stopped)
    if dbs.lifecycle_state == "AVAILABLE":
        # get the tags
        try:
            tag_value_stop  = dbs.defined_tags[tag_ns][tag_key_stop]
            tag_value_start = dbs.defined_tags[tag_ns][tag_key_start]
        except:
            tag_value_stop  = "none"
            tag_value_start = "none"
        
        # get the DB node 
        response = DatabaseClient.list_db_nodes(compartment_id=lcpt_id, db_system_id=dbs.id)
        dbnode = response.data[0]

        # Is it time to start this autonomous db ?
        if dbnode.lifecycle_state == "STOPPED" and tag_value_start == current_utc_time:
            print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt_name),end='')
            if confirm_start:
                print ("STARTING DB node for {:s} ({:s})".format(dbs.display_name, dbs.id))
                DatabaseClient.db_node_action(dbnode.id, "START")
            else:
                print ("DB node for DB system {:s} ({:s}) SHOULD BE STARTED --> re-run script with --confirm_start to actually start databases".format(dbs.display_name, dbs.id))

        # Is it time to stop this autonomous db ?
        elif dbnode.lifecycle_state == "AVAILABLE" and tag_value_stop == current_utc_time:
            print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt_name),end='')
            if confirm_stop:
                print ("STOPPING DB node for {:s} ({:s})".format(dbs.display_name, dbs.id))
                DatabaseClient.db_node_action(dbnode.id, "STOP")
            else:
                print ("DB node for DB system {:s} ({:s}) SHOULD BE STOPPED --> re-run script with --confirm_start to actually stop databases".format(dbs.display_name, dbs.id))

  
# ------------ main

# -- parse arguments
all_regions   = False
confirm_stop  = False
confirm_start = False

if len(sys.argv) == 2:
    profile  = sys.argv[1] 

elif len(sys.argv) == 3:
    profile  = sys.argv[2] 
    if sys.argv[1] == "-a": all_regions = True
    elif sys.argv[1] == "--confirm_stop":  confirm_stop  = True
    elif sys.argv[1] == "--confirm_start": confirm_start = True
    else: usage ()

elif len(sys.argv) == 4:
    profile  = sys.argv[3] 
    if   sys.argv[1] == "-a": all_regions = True
    elif sys.argv[1] == "--confirm_stop":  confirm_stop  = True
    elif sys.argv[1] == "--confirm_start": confirm_start = True
    else: usage ()
    if   sys.argv[2] == "--confirm_stop":  confirm_stop  = True 
    elif sys.argv[2] == "--confirm_start": confirm_start = True 
    else: usage ()

elif len(sys.argv) == 5:
    profile  = sys.argv[4] 
    if   sys.argv[1] == "-a": all_regions = True
    elif sys.argv[1] == "--confirm_stop":  confirm_stop  = True
    elif sys.argv[1] == "--confirm_start": confirm_start = True
    else: usage ()
    if   sys.argv[2] == "--confirm_stop":  confirm_stop  = True 
    elif sys.argv[2] == "--confirm_start": confirm_start = True 
    else: usage ()
    if   sys.argv[3] == "--confirm_stop":  confirm_stop  = True 
    elif sys.argv[3] == "--confirm_start": confirm_start = True 
    else: usage ()

else:
    usage()

# -- get UTC time (format 10:00_UTC, 11:00_UTC ...)
current_utc_time = datetime.utcnow().strftime("%H")+":00_UTC"

# -- starting
pid=os.getpid()
print ("{:s}: BEGIN SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)

except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- get list of compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query dbsystem resources"

# -- Run the search query/queries to find all DB systems in the region/regions
if not(all_regions):
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        process_dbs (item.identifier, cpt_name, item.compartment_id)
else:
    for region in regions:
        #print (f"DEBUG: testing region {region.region_name}")
        config["region"]=region.region_name
        SearchClient = oci.resource_search.ResourceSearchClient(config)
        response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
        for item in response.data.items:
            cpt_name = get_cpt_name_from_id(item.compartment_id)
            process_dbs (item.identifier, cpt_name, item.compartment_id)

# -- the end
print ("{:s}: END SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))
exit (0)
