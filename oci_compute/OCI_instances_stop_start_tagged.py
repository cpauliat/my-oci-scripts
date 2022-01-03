#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script looks for compute instances with a specific tag key and stop (or start) them if the 
#     tag value for the tag key matches the current UTC time.
# You can use it to automatically stop some compute instances during non working hours
#     and start them again at the beginning of working hours to save cloud credits
# This script needs to be executed every hour during working days by an external scheduler (cron table on Linux for example)
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
#                 - OCI user with enough privileges to be able to read, stop and start compute instances (policy example below)
#                       allow group osc_stop_and_start to read instances in tenancy
#                       allow group osc_stop_and_start to manage instances in tenancy where request.operation = 'InstanceAction'
# Versions
#    2020-04-22: Initial Version
#    2020-09-17: bug fix (root compartment was ignored)
#    2020-09-18: Add a retry strategy for ComputeClient.instance_action to avoid errors "TooManyRequest HTTP 429"
#    2022-01-03: use argparse to parse arguments
# ---------------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import os
import argparse
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
    print ("Usage: {} [-a] [--confirm_stop] [--confirm_start] -p OCI_PROFILE".format(sys.argv[0]))
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

# ---- Check compute instances in a compartment
def process_compartment(lcpt):
    
    # exit function if compartent is deleted
    if lcpt.lifecycle_state == "DELETED": return

    # region 
    region = config["region"]

    # find compute instances in this compartment
    response = oci.pagination.list_call_get_all_results(ComputeClient.list_instances,compartment_id=lcpt.id)

    # for each instance, check if it needs to be stopped or started 
    if len(response.data) > 0:
        for instance in response.data:
            if instance.lifecycle_state != "TERMINED":
                # get the tags
                try:
                    tag_value_stop  = instance.defined_tags[tag_ns][tag_key_stop]
                    tag_value_start = instance.defined_tags[tag_ns][tag_key_start]
                except:
                    tag_value_stop  = "none"
                    tag_value_start = "none"
                
                # Is it time to start this instance ?
                if instance.lifecycle_state == "STOPPED" and tag_value_start == current_utc_time:
                    print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt.name),end='')
                    if confirm_start:
                        print ("STARTING instance {:s} ({:s})".format(instance.display_name, instance.id))
                        ComputeClient.instance_action(instance.id, "START", retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
                    else:
                        print ("Instance {:s} ({:s}) SHOULD BE STARTED --> re-run script with --confirm_start to actually start instances".format(instance.display_name, instance.id))

                # Is it time to stop this instance ?
                elif instance.lifecycle_state == "RUNNING" and tag_value_stop == current_utc_time:
                    print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt.name),end='')
                    if confirm_stop:
                        print ("STOPPING instance {:s} ({:s})".format(instance.display_name, instance.id))
                        ComputeClient.instance_action(instance.id, "SOFTSTOP", retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
                    else:
                        print ("Instance {:s} ({:s}) SHOULD BE STOPPED --> re-run script with --confirm_stop to actually stop instances".format(instance.display_name, instance.id))

  
# ------------ main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Stop or start tagged compute instances")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-off", "--confirm_stop", help="Confirm shutdown", action="store_true")
parser.add_argument("-on", "--confirm_start", help="Confirm startup", action="store_true")
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
args = parser.parse_args()
    
profile       = args.profile
confirm_stop  = args.confirm_stop
confirm_start = args.confirm_start
all_regions   = args.all_regions

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

# -- do the job
class root_cpt:
    name="root"
    id=RootCompartmentID
    lifecycle_state="AVAILABLE"

if not(all_regions):
    ComputeClient = oci.core.ComputeClient(config)
    process_compartment(root_cpt)
    for cpt in compartments:
        process_compartment(cpt)
else:
    for region in regions:
        config["region"]=region.region_name
        ComputeClient = oci.core.ComputeClient(config)
        process_compartment(root_cpt)
        for cpt in compartments:
            process_compartment(cpt)

# -- the end
print ("{:s}: END SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))
exit (0)
