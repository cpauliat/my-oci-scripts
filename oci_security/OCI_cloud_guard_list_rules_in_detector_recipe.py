#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists the rules in an Cloud Guard DETECTOR RECIPE 
# (ACTIVITY or CONFIGURATION) in a OCI tenant using OCI Python SDK 
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-05: Initial Version
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------


# ---------- import
import oci
import sys
import argparse
from operator import itemgetter

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# ---------- functions
def usage():
    print (f"Usage: {sys.argv[0]} -p OCI_PROFILE -r detector_recipe_ocid")
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

def display_rule(r):
    print (f"{r['id']:{width_id}s} {r['risk_level']:^10s} {r['is_enabled']:6s}")
  
def display_rules_sorted_by_id(rules):
    for r in rules:
        display_rule(r)

def display_rules_sorted_by_risk_level(rules):
    # display CRITICAL detector rules first
    for r in rules:
        if r['risk_level'] == "CRITICAL":
            display_rule(r)
        
    # then HIGH detector rules
    for r in rules:
        if r['risk_level'] == "HIGH":
            display_rule(r)

    # then MEDIUM detector rules
    for r in rules:
        if r['risk_level'] == "MEDIUM":
            display_rule(r)

    # then LOW detector rules
    for r in rules:
        if r['risk_level'] == "LOW":
            display_rule(r)

    # and finally MINOR detector rules
    for r in rules:
        if r['risk_level'] == "MINOR":
            display_rule(r)

# ---------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List rules in a Cloud Guard detector recipe")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-r", "--recipe_ocid", help="Detector recipe OCID", required=True)
args = parser.parse_args()
    
profile     = args.profile
recipe_ocid = args.recipe_ocid

# -- get info from profile    
try:
    config = oci.config.from_file(configfile,profile)
except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get the list of Cloud Guard detector rules in a detector recipe
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)
response = oci.pagination.list_call_get_all_results(
    CloudGuardClient.list_detector_recipe_detector_rules, detector_recipe_id=recipe_ocid, compartment_id=RootCompartmentID)

print (f"Number of detector rules in this detector recipe: {len(response.data)}")
print ("")

if len(response.data) > 0:
    width_id = 0
    rules = []
    for rule in response.data:
        if len(rule.id) > width_id:
            width_id = len(rule.id)
        new_rule = {}
        new_rule['id']         = rule.id
        new_rule['risk_level'] = rule.detector_details.risk_level
        new_rule['is_enabled'] = str(rule.detector_details.is_enabled)
        rules.append(new_rule)

    header_id = "---- DETECTOR RULE ID ----"
    header_rl = "RISK-LEVEL"
    header_status = "ENABLED"
    print (f"{header_id:{width_id}s} {header_rl:10s} {header_status:6s}")

    # -- sort rules by ID
    sorted_rules = sorted(rules, key=itemgetter('id'))

    # -- list rules sorted by ID or RISK_LEVEL then ID
    display_rules_sorted_by_risk_level(sorted_rules)
    #display_rules_sorted_by_id(sorted_rules)

# -- the end
exit (0)
