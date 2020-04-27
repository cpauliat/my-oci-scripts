#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script looks for compute instances with a specific tag key and stop (or start) them if the 
#     tag value for the tag key matches the current time.
# You can use it to automatically stop some compute instances during non working hours
#     and start them again at the beginning of working hours to save cloud credits
# This script needs to be executed every hour during working days by an external scheduler 
#     (cron table on Linux for example)
# You can add the 2 tag keys to the default tags for root compartment so that every new compute 
#     instance get those 2 tag keys with default value ("off" or a specific UTC time)
#
# This script looks in all compartments in a OCI tenant in a region using OCI Python SDK
# Note: OCI tenant and region given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-22: Initial Version
#    2020-04-27: rewrite of the script using OCI search (much faster)
# ---------------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import os
from datetime import datetime

# ---------- Tag names, key and value to look for
# Instances tagged using this will be stopped/started.
# Update these to match your tags.
tag_ns        = "osc"
tag_key_stop  = "automatic_shutdown"
tag_key_start = "automatic_startup"

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---------- Functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] [--confirm_stop] [--confirm_start] OCI_FILE".format(sys.argv[0]))
    print ("")
    print ("Notes:")
    print ("    If -a is provided, the script processes all active regions instead of singe region provided in profile")
    print ("    If --confirm_stop  is not provided, the instances to stop are listed but not actually stopped")
    print ("    If --confirm_start is not provided, the instances to start are listed but not actually started")
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

# ---- Get the name of compartment from its id
def get_cpt_name_from_id(cpt_id):
    global compartments
    for c in compartments:
        if (c.id == cpt_id):
            return c.name
    return "root"

# ---- Search compute instances to be stopped in a region, then display or stop them depending on --confirm_stop presence
def search_and_stop_resources_in_region(lquery, lregion):
    global config
    global confirm_stop

    config["region"] = lregion
    ComputeClient = oci.core.ComputeClient(config)
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=lquery))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), lregion, cpt_name), end='')
        if confirm_stop:
            print ("STOPPING instance {:s} ({:s})".format(item.display_name, item.identifier))
            ComputeClient.instance_action(item.identifier, "SOFTSTOP")
        else:
            print ("Instance {:s} ({:s}) SHOULD BE STOPPED --> re-run script with --confirm_stop to actually stop instances".format(item.display_name, item.identifier))

# ---- Search compute instances to be started in a region, then display or start them depending on --confirm_start presence
def search_and_start_resources_in_region(lquery, lregion):
    global config
    global confirm_start

    config["region"] = lregion
    ComputeClient = oci.core.ComputeClient(config)
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=lquery))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), lregion, cpt_name), end='')
        if confirm_start:
            print ("STARTING instance {:s} ({:s})".format(item.display_name, item.identifier))
            ComputeClient.instance_action(item.identifier, "START")
        else:
            print ("Instance {:s} ({:s}) SHOULD BE STARTED --> re-run script with --confirm_start to actually start instances".format(item.display_name, item.identifier))
  
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

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data
config_region = config['region']

# -- get compartments list
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Search compute instances to be stopped with a search query
# -- (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query_stop = "query instance resources where (lifeCycleState = 'RUNNING' && definedTags.namespace = '{:s}' && definedTags.key = '{:s}' && definedTags.value = '{:s}')".format(tag_ns, tag_key_stop, current_utc_time)
print ("DEbUG", query_stop)
# For each region, get the list of compute instances to be stopped, then display them or stop them depending on --confirm_stop presence
if all_regions:
    for region in regions:
        search_and_stop_resources_in_region(query_stop, region.region_name)
else:
    search_and_stop_resources_in_region(query_stop, config_region)

# -- Search compute instances to be started with a search query
# -- (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query_start = "query instance resources where (lifeCycleState = 'STOPPED' && definedTags.namespace = '{:s}' && definedTags.key = '{:s}' && definedTags.value = '{:s}')".format(tag_ns, tag_key_start, current_utc_time)

# For each region, get the list of compute instances to be started, then display them or start them depending on --confirm_start presence
if all_regions:
    for region in regions:
        search_and_start_resources_in_region(query_start, region.region_name)
else:
    search_and_start_resources_in_region(query_start, config_region)

# -- the end
print ("{:s}: END SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))
exit (0)
