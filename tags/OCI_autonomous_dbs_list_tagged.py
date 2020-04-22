#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script looks for all autonomous databases in a tenant and region (all compartments)
# and list the tag values for the ones having specific tag namespace and tag key
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-04-22: Initial Version
# --------------------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys

# ---------- Functions

# ---- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---- usage syntax
def usage():
    print ("Usage: {} [-a] OCI_PROFILE tag_namespace tag_key".format(sys.argv[0]))
    print ("")
    print ("    By default, only the autonomous databases in the region provided in the profile are listed")
    print ("    If -a is provided, the autonomous databases from all subscribed regions are listed")
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

# -- Autonomous DB
def list_tagged_autonomous_databases_in_compartment (lcpt):
    if lcpt.lifecycle_state == "DELETED": return

    response = oci.pagination.list_call_get_all_results(DatabaseClient.list_autonomous_databases,compartment_id=lcpt.id)
    if len(response.data) > 0:
        for adb in response.data:
            if adb.lifecycle_state != "TERMINED":
                try:
                    tag_value = adb.defined_tags[tag_ns][tag_key]
                    print ('{:s}, {:s}, {:s}, {:s}, {:s}.{:s} = {:s}'.format(config["region"], lcpt.name, adb.display_name, adb.id, tag_ns, tag_key, tag_value))
                except:
                    pass


# ------------ main
global config

# -- parse arguments
all_regions = False

if len(sys.argv) == 4:
    profile  = sys.argv[1] 
    tag_ns   = sys.argv[2]
    tag_key  = sys.argv[3]
elif len(sys.argv) == 5:
    if sys.argv[1] == "-a":
        all_regions = True
    else:
        usage()
    profile  = sys.argv[2] 
    tag_ns   = sys.argv[3]
    tag_key  = sys.argv[4]
else:
    usage()

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

# -- get compartments list
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- list objects
if all_regions:
    for region in regions:
        config["region"]=region.region_name
        DatabaseClient = oci.database.DatabaseClient(config)
        for cpt in compartments:
            list_tagged_autonomous_databases_in_compartment (cpt)
else:
    DatabaseClient = oci.database.DatabaseClient(config)
    for cpt in compartments:
        list_tagged_autonomous_databases_in_compartment (cpt)

# -- the end
exit (0)