#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script looks for autonomous databases with a specific tag key and stop (or start) them if the 
#     tag value for the tag key matches the current time.
# You can use it to automatically stop some autonomous databases during non working hours
#     and start them again at the beginning of working hours to save cloud credits
# This script needs to be executed every hour during working days by an external scheduler 
#     (cron table on Linux for example)
# You can add the 2 tag keys to the default tags for root compartment so that every new autonomous 
#     database get those 2 tag keys with default value ("off" or a specific UTC time)
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
#    2020-04-23: Initial Version
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
    print ("    If --confirm_stop  is not provided, the autonomous databases to stop are listed but not actually stopped")
    print ("    If --confirm_start is not provided, the autonomous databases to start are listed but not actually started")
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

# ---- Check autonomous databases in a compartment
def process_compartment(lcpt):
    global config
    global current_utc_time
    global DatabaseClient

    # exit function if compartent is deleted
    if lcpt.lifecycle_state == "DELETED": return

    # region 
    region = config["region"]

    # find autonomous databases in this compartment
    response = oci.pagination.list_call_get_all_results(DatabaseClient.list_autonomous_databases,compartment_id=lcpt.id)
 
    # for each instance, check if it needs to be stopped or started 
    if len(response.data) > 0:
        for adb in response.data:
            if adb.lifecycle_state != "TERMINED":
                # get the tags
                try:
                    tag_value_stop  = adb.defined_tags[tag_ns][tag_key_stop]
                    tag_value_start = adb.defined_tags[tag_ns][tag_key_start]
                except:
                    tag_value_stop  = "none"
                    tag_value_start = "none"
                
                # Is it time to start this autonomous db ?
                if adb.lifecycle_state == "STOPPED" and tag_value_start == current_utc_time:
                    print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt.name),end='')
                    if confirm_start:
                        print ("STARTING autonomous db {:s} ({:s})".format(adb.display_name, adb.id))
                        DatabaseClient.start_autonomous_database(adb.id)
                    else:
                        print ("Autonomous DB {:s} ({:s}) SHOULD BE STARTED --> re-run script with --confirm_start to actually start databases".format(adb.display_name, adb.id))

                # Is it time to stop this autonomous db ?
                elif adb.lifecycle_state == "RUNNING" and tag_value_stop == current_utc_time:
                    print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt.name),end='')
                    if confirm_stop:
                        print ("STOPPING autonomous db {:s} ({:s})".format(adb.display_name, adb.id))
                        DatabaseClient.stop_autonomous_database(adb.id)
                    else:
                        print ("Autonomous DB {:s} ({:s}) SHOULD BE STOPPED --> re-run script with --confirm_start to actually stop databases".format(adb.display_name, adb.id))

  
# ------------ main
global config
global ads
global IdentityClient
global RootCompartmentID

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

# -- do the job
if not(all_regions):
    DatabaseClient = oci.database.DatabaseClient(config)
    for cpt in compartments:
        process_compartment(cpt)
else:
    for region in regions:
        config["region"]=region.region_name
        DatabaseClient = oci.database.DatabaseClient(config)
        for cpt in compartments:
            process_compartment(cpt)

# -- the end
print ("{:s}: END SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))
exit (0)
