#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script looks for ExaCC VM clusters with specific tags in a OCI tenant using OCI Python SDK 
# and scales up or down the number of OCPUs depending on tags values.
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-01-06: Initial Version
#    2021-01-07: Add support for all subscribed regions
#    2021-01-28: Display a message about ignored VM clusters (not in AVAILABLE status)
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------


# -------- import
import oci
import sys
import os
import argparse
from datetime import datetime

# -------- variables
configfile       = "~/.oci/config"    # Define config file to be used.
tag_ns           = "osc_exacc"
tag_key_dn_time  = "scale_down_time"
tag_key_up_time  = "scale_up_time"
tag_key_dn_ocpus = "scale_down_ocpus"
tag_key_up_ocpus = "scale_up_ocpus"

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] [--confirm] -p OCI_PROFILE ".format(sys.argv[0]))
    print ("")
    print ("Notes:")
    print ("- If -a is provided, the script processes all active regions instead of single region provided in profile")
    print ("- If --confirm is not provided, the VM clusters to scale down (ou up) are listed but not actually scaled down (or up)")
    print ("- OCI_PROFILE must exist in ~/.oci/config file (see example below)")
    print ("")
    print ("[OSCEMEA001]")
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

# ---- If needed, scale up or scale down the number of OCPUs in a VM cluster
def process_vmcluster (vmcluster_id, lcpt_name):

    # get details about vmcluster from regular API 
    DatabaseClient = oci.database.DatabaseClient(config)
    response = DatabaseClient.get_vm_cluster (vm_cluster_id = vmcluster_id)
    vmcluster = response.data

    # if vmcluster is busy (not AVAILABLE), then exit this function
    if vmcluster.lifecycle_state != "AVAILABLE":
        print (f"IGNORING VM cluster {vmcluster.display_name} as NOT AVAILABLE !")
        return

    # common variables for scale up and scale down
    now     = datetime.utcnow().strftime("%T")
    region  = config["region"] 
    ocpus   = vmcluster.cpus_enabled    # current number of OCPUs

    # get the tags of the VM cluster
    try:
        tag_value_dn_time  = vmcluster.defined_tags[tag_ns][tag_key_dn_time]
        tag_value_up_time  = vmcluster.defined_tags[tag_ns][tag_key_up_time]
        tag_value_dn_ocpus = vmcluster.defined_tags[tag_ns][tag_key_dn_ocpus]
        tag_value_up_ocpus = vmcluster.defined_tags[tag_ns][tag_key_up_ocpus]
    except:
        # if one of the tags is not found, then ignore this VM cluster
        if verbose:
            print (f"IGNORING VM cluster {vmcluster.display_name} in region {region} and compartment {lcpt_name} as some tags are missing !")
        return

    # Is it time to scale down this VM cluster ?
    if tag_value_dn_time == current_utc_time:
        print (f"{now}, {region}, {lcpt_name}: ", end='')
        if ocpus == int(tag_value_dn_ocpus):
            print (f"It's time to SCALE DOWN VM cluster {vmcluster.display_name} to {tag_value_dn_ocpus} OCPUs but IGNORED as already {tag_value_dn_ocpus} OCPUs enabled !")
        elif confirm:
            print (f"SCALE DOWN operation submitted for VM cluster {vmcluster.display_name} from {ocpus} to {tag_value_dn_ocpus} OCPUs")
            details = oci.database.models.UpdateVmClusterDetails(cpu_core_count = int(tag_value_dn_ocpus))
            DatabaseClient.update_vm_cluster (vmcluster.id, details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        else:
            print (f"VM cluster {vmcluster.display_name} should be SCALED DOWN from {ocpus} to {tag_value_dn_ocpus} OCPUs --> re-run script with --confirm to actually scale down VM cluster")

    # Otherwise, is it time to scale up this VM cluster ?
    elif tag_value_up_time == current_utc_time: 
        print (f"{now}, {region}, {lcpt_name}: ", end='')
        if ocpus == int(tag_value_up_ocpus):
            print (f"It's time to SCALE UP VM cluster {vmcluster.display_name} to {tag_value_up_ocpus} OCPUs but IGNORED as already {tag_value_up_ocpus} OCPUs enabled !")
        elif confirm:
            print (f"SCALE UP operation submitted for VM cluster {vmcluster.display_name} from {ocpus} to {tag_value_up_ocpus} OCPUs")
            details = oci.database.models.UpdateVmClusterDetails(cpu_core_count = int(tag_value_up_ocpus))
            DatabaseClient.update_vm_cluster (vmcluster.id, details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        else:
            print (f"VM cluster {vmcluster.display_name} should be SCALED UP from {ocpus} to {tag_value_up_ocpus} OCPUs --> re-run script with --confirm to actually scale up VM cluster")


# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Scale up/down ExaCC VM clusters")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
parser.add_argument("-v", "--verbose", help="Verbose mode", action="store_true")
parser.add_argument("-c", "--confirm", help="Confirm action", action="store_true")
args = parser.parse_args()

profile     = args.profile
all_regions = args.all_regions
confirm     = args.confirm
verbose     = args.verbose

# -- get UTC time (format 10:00_UTC, 11:00_UTC ...)
current_utc_time = datetime.utcnow().strftime("%H")+":00_UTC"

# -- starting
pid=os.getpid()
print ("{:s}: BEGIN SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))

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

# -- Query (see https://docs.cloud.oracle.com/en-us/iaas/Content/Search/Concepts/querysyntax.htm)
query = "query vmcluster resources"

# -- Run the search query/queries to find all ExaCC VM cluster in the region
if not(all_regions):
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
    for item in response.data.items:
        cpt_name = get_cpt_name_from_id(item.compartment_id)
        process_vmcluster (item.identifier, cpt_name)
else:
    for region in regions:
        config["region"]=region.region_name
        SearchClient = oci.resource_search.ResourceSearchClient(config)
        response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))
        for item in response.data.items:
            cpt_name = get_cpt_name_from_id(item.compartment_id)
            process_vmcluster (item.identifier, cpt_name)

# -- the end
print ("{:s}: END SCRIPT PID={:d}".format(datetime.utcnow().strftime("%Y/%m/%d %T"),pid))
exit (0)
