#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists the  rules in an Cloud Guard RESPONDER RECIPE 
# in a OCI tenant using OCI Python SDK 
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-09: Initial Version
# --------------------------------------------------------------------------------------------------------------


# ---------- import
import oci
import sys
from operator import itemgetter

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---------- functions
def usage():
    print (f"Usage: {sys.argv[0]} OCI_PROFILE responder_recipe_ocid")
    print ("")
    print (f"note: OCI_PROFILE must exist in {configfile} file (see example below)")
    print ("")
    print ("[EMEAOSC]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

def display_rules_sorted_by_id(rules):
    for r in rules:
        print (f"{r['id']:{width_id}s} {r['mode']:^10s} {r['is_enabled']:6s}")
        # CSV
        #print (f"{r['id']},{r['mode']},{r['is_enabled']}")



# ---------- main

# -- parse arguments
if (len(sys.argv) == 3):
    profile     = sys.argv[1]
    recipe_ocid = sys.argv[2]
else:
    usage()

# -- get info from profile    
try:
    config = oci.config.from_file(configfile,profile)
except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get the list of Cloud Guard rules in a responder recipe
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)
response = oci.pagination.list_call_get_all_results(
    CloudGuardClient.list_responder_recipe_responder_rules, responder_recipe_id=recipe_ocid, compartment_id=RootCompartmentID)

print (f"Number of responder rules in this responder recipe: {len(response.data)}")
print ("")

if len(response.data) > 0:
    width_id = 0
    rules = []
    #print(response.data[0])

    for rule in response.data:
        if len(rule.id) > width_id:
            width_id = len(rule.id)
        new_rule = {}
        new_rule['id']         = rule.id
        new_rule['mode']       = rule.details.mode
        new_rule['is_enabled'] = str(rule.details.is_enabled)
        rules.append(new_rule)

    header_id     = "RESPONDER RULE ID"
    header_mode   = "MODE"
    header_status = "ENABLED"
    print (f"{header_id:{width_id}s} {header_mode:10s} {header_status:6s}")
    # CSV
    #print (f"{header_id},{header_mode},{header_status}")

    sorted_rules = sorted(rules, key=itemgetter('id'))
    display_rules_sorted_by_id(sorted_rules)

# -- the end
exit (0)
