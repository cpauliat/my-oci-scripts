#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists the compartment names and IDs in a OCI tenant using OCI Python SDK
# It will also list all subcompartments
# Note: OCI tenant given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2018-12-13: Initial Version
#    2019-10-18: change default behaviour (does not display deleted compartment)
#                and add option -d to list deleted compartments
# --------------------------------------------------------------------------------------------------------------


# -- import
import oci
import sys

# -- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -- functions
def usage():
    print ("Usage: {} [-d] OCI_PROFILE".format(sys.argv[0]))
    print ("")
    print ("    If -d is provided, deleted compartments are also listed.")
    print ("    If not, only active compartments are listed.")
    print 
    print ("note: OCI_PROFILE must exist in {} file (see example below)".format(configfile))
    print ("")
    print ("[EMEAOSCf]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# -- main
LIST_DELETED=False

if (len(sys.argv) != 2) and (len(sys.argv) != 3):
    usage()

if (len(sys.argv) == 2):
    profile = sys.argv[1] 
elif (len(sys.argv) == 3):
    profile = sys.argv[2]
    if (sys.argv[1] == "-d"):
        LIST_DELETED=True
    else:
        usage()
    
#print ("profile = {}".format(profile))

try:
    config = oci.config.from_file(configfile,profile)

except:
    print ("ERROR: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

identity = oci.identity.IdentityClient(config)
user = identity.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

response = oci.pagination.list_call_get_all_results(identity.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

#print ("Logged in as: {} in region {}".format(user.name, config["region"]))
#print ("")
print ("Compartment name               State    Compartment OCID")
print ("RootCompartment                ACTIVE   {}".format(RootCompartmentID))

for c in compartments:
    if LIST_DELETED or (c.lifecycle_state != "DELETED"):
        print ("{:30s} {:9s} {}".format(c.name,c.lifecycle_state,c.id))

exit (0)
