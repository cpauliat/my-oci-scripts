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
#
# THIS SCRIPT MUST BE EXECUTED FROM AN OCI COMPUTE INSTANCE WITH INSTANCE PRINCIPAL PERMISSIONS
#
# IMPORTANT: DOES NOT SUPPORT RAC VM DB SYSTEMS
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
# 
# Versions
#    2020-09-09: Initial Version
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

# ---------- Functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] [--confirm_stop] [--confirm_start]".format(sys.argv[0]))
    print ("")
    print ("Notes:")
    print ("    If -a is provided, the script processes all active regions instead of singe region provided in profile")
    print ("    If --confirm_stop  is not provided, the VM database systems to stop are listed but not actually stopped")
    print ("    If --confirm_start is not provided, the VM database systems to start are listed but not actually started")
    print ("")
    exit (1)

# ---- Check VM database systems in a compartment
def process_compartment(lcpt):

    # exit function if compartent is deleted
    if lcpt.lifecycle_state == "DELETED": return

    # region 
    region = signer.region

    # find VM database systems in this compartment
    response = oci.pagination.list_call_get_all_results(DatabaseClient.list_db_systems,compartment_id=lcpt.id)
 
    # for each instance, check if it needs to be stopped or started 
    if len(response.data) > 0:
        for dbs in response.data:
            if dbs.lifecycle_state != "TERMINED":
                # get the tags
                try:
                    tag_value_stop  = dbs.defined_tags[tag_ns][tag_key_stop]
                    tag_value_start = dbs.defined_tags[tag_ns][tag_key_start]
                except:
                    tag_value_stop  = "none"
                    tag_value_start = "none"
                
                # get the DB node 
                response = DatabaseClient.list_db_nodes(compartment_id=lcpt.id, db_system_id=dbs.id)
                dbnode = response.data[0]

                # Is it time to start this autonomous db ?
                if dbnode.lifecycle_state == "STOPPED" and tag_value_start == current_utc_time:
                    print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt.name),end='')
                    if confirm_start:
                        print ("STARTING DB node for {:s} ({:s})".format(dbs.display_name, dbs.id))
                        DatabaseClient.db_node_action(dbnode.id, "START")
                    else:
                        print ("DB node for DB system {:s} ({:s}) SHOULD BE STARTED --> re-run script with --confirm_start to actually start databases".format(dbs.display_name, dbs.id))

                # Is it time to stop this autonomous db ?
                elif dbnode.lifecycle_state == "AVAILABLE" and tag_value_stop == current_utc_time:
                    print ("{:s}, {:s}, {:s}: ".format(datetime.utcnow().strftime("%T"), region, lcpt.name),end='')
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
    DatabaseClient = oci.database.DatabaseClient(config={}, signer=signer)
    for cpt in compartments:
        process_compartment(cpt)
else:
    for region in regions:
        signer.region=region.region_name
        DatabaseClient = oci.database.DatabaseClient(config={}, signer=signer)
        for cpt in compartments:
            process_compartment(cpt)

# -- the end
print ("{:s}: END SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))
exit (0)
