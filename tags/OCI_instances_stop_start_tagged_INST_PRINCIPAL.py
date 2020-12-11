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
#
# THIS SCRIPT MUST BE EXECUTED FROM AN OCI COMPUTE INSTANCE WITH INSTANCE PRINCIPAL PERMISSIONS
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#
# Versions
#    2020-09-09: Initial Version
#    2020-09-14: Add a retry strategy for ComputeClient.instance_action to avoid errors "TooManyRequest HTTP 429"
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

# ---------- Functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] [--confirm_stop] [--confirm_start]".format(sys.argv[0]))
    print ("")
    print ("Notes:")
    print ("    If -a is provided, the script processes all active regions instead of singe region provided in profile")
    print ("    If --confirm_stop  is not provided, the instances to stop are listed but not actually stopped")
    print ("    If --confirm_start is not provided, the instances to start are listed but not actually started")
    print ("")
    exit (1)

# ---- Check compute instances in a compartment
def process_compartment(lcpt):
    global signer
    global current_utc_time
    global ComputeClient

    # exit function if compartent is deleted
    if lcpt.lifecycle_state == "DELETED": return

    # region 
    region = signer.region

    # find compute instances in this compartment
    #print ("TEMPO: cpt="+lcpt.name)
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
global signer
global ads
global IdentityClient
global RootCompartmentID

# -- parse arguments
all_regions   = False
confirm_stop  = False
confirm_start = False

if len(sys.argv) == 1:
    pass

elif len(sys.argv) == 2:
    if sys.argv[1] == "-a": all_regions = True
    elif sys.argv[1] == "--confirm_stop":  confirm_stop  = True
    elif sys.argv[1] == "--confirm_start": confirm_start = True
    else: usage ()

elif len(sys.argv) == 3:
    if   sys.argv[1] == "-a": all_regions = True
    elif sys.argv[1] == "--confirm_stop":  confirm_stop  = True
    elif sys.argv[1] == "--confirm_start": confirm_start = True
    else: usage ()
    if   sys.argv[2] == "--confirm_stop":  confirm_stop  = True 
    elif sys.argv[2] == "--confirm_start": confirm_start = True 
    else: usage ()

elif len(sys.argv) == 4:
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

# -- authentication using instance principal
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
IdentityClient = oci.identity.IdentityClient(config={}, signer=signer)
RootCompartmentID = signer.tenancy_id

# -- get list of compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions = response.data

# -- do the job
if not(all_regions):
    ComputeClient = oci.core.ComputeClient(config={}, signer=signer)
    for cpt in compartments:
        process_compartment(cpt)
else:
    for region in regions:
        signer.region=region.region_name
        ComputeClient = oci.core.ComputeClient(config={}, signer=signer)
        for cpt in compartments:
            process_compartment(cpt)

# -- the end
print ("{:s}: END SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))
exit (0)
