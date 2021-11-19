#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script updates or restores the configuration of a Cloud Guard "parent" (not attached to a target)
# RESPONDER RECIPE from a JSON backup file created with the 
# "OCI_cloud_guard_save_parent_responder_recipe.py" script in a OCI tenant using OCI Python SDK 
#
# Restored/updated parameters include:
# - recipe name
# - description
# - defined and freeform tags
# - for each responder rule:
#       - status (enabled/disabled)
# 
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-19: Initial Version
# --------------------------------------------------------------------------------------------------------------

# ---------- import
import oci
import sys
import json
from pathlib import Path

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.
different  = False              # Is configuration in backup file different from current configuration

# ---------- functions
def usage():
    print (f"Usage: {sys.argv[0]} OCI_PROFILE input_backup_file.json")
    print ("")
    print ("notes: ")
    print ("- The OCID of the responder recipe to update is stored in the backup file")
    print (f"- OCI_PROFILE must exist in {configfile} file (see example below)")
    print ("")
    print ("[EMEAOSC]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# -- Build class oci.cloud_guard.models.UpdateResponderRecipeDetails from JSON content read in file
def build_update_responder_recipe_class():
    rules = []
    for rule in responder_recipe['effective_responder_rules']:
        new_rule_details = oci.cloud_guard.models.UpdateResponderRuleDetails(
            is_enabled = rule['details']['is_enabled'])
        new_rule = oci.cloud_guard.models.UpdateResponderRecipeResponderRule(
            responder_rule_id = rule['responder_rule_id'], 
            details = new_rule_details)
        rules.append(new_rule)

    details = oci.cloud_guard.models.UpdateResponderRecipeDetails(
        defined_tags    = responder_recipe['defined_tags'], 
        description     = responder_recipe['description'], 
        responder_rules = rules, 
        display_name    = responder_recipe['display_name'], 
        freeform_tags   = responder_recipe['freeform_tags'])   
    
    return details

# -- Check differences between current configuration and configuration in backup file
def check_differences():
    global different

    print ("DIFFERENCES between current configuration and configuration in file: ", end="")

    # get current configuration of the responder recipe
    response = CloudGuardClient.get_responder_recipe(responder_recipe_id=responder_recipe['id'])
    current_recipe = response.data

    # check differences in the display_name
    if responder_recipe['display_name'] != current_recipe.display_name:
        different = True
        print ("")
        print (f"- CURRENT display_name  : {current_recipe.display_name}")
        print (f"- NEW     display_name  : {responder_recipe['display_name']}")

    # check differences in the description
    if responder_recipe['description'] != current_recipe.description:
        different = True
        print ("")
        print (f"- CURRENT description   : {current_recipe.description}")
        print (f"- NEW     description   : {responder_recipe['description']}")

    # check differences in the defined_tags
    if responder_recipe['defined_tags'] != current_recipe.defined_tags:
        different = True
        print ("")
        print (f"- CURRENT defined_tags  : {current_recipe.defined_tags}")
        print (f"- NEW     defined_tags  : {responder_recipe['defined_tags']}")

    # check differences in the freeform_tags
    if responder_recipe['freeform_tags'] != current_recipe.freeform_tags:
        different = True
        print ("")
        print (f"- CURRENT freeform_tags : {current_recipe.freeform_tags}")
        print (f"- NEW     freeform_tags : {responder_recipe['freeform_tags']}")

    # check differences in each responder rule
    for current_rule in current_recipe.effective_responder_rules:
        rule_found = False
        for new_rule in responder_recipe['effective_responder_rules']:
            if new_rule['responder_rule_id'] == current_rule.responder_rule_id:
                rule_found = True
                break
            
        # if the current rule ID does not exist in backup, stop the script
        if not(rule_found):
            print (f"ERROR: rule id {current_rule.responder_rule_id} not found in backup --> edit backup file, add this rule and re-run the script !")
            exit (5)
        # otherwise, check enabled status, risk level, settings and conditional group
        else:

            # comparing status: "details.is_enabled"
            if current_rule.details.is_enabled != new_rule['details']['is_enabled']:
                different = True
                print ("")
                print (f"- responder rule id {current_rule.responder_rule_id}")
                print (f"  - CURRENT is_enabled : {current_rule.details.is_enabled}")
                print (f"  - NEW     is_enabled : {new_rule['details']['is_enabled']}")

    # If differences are found, ask for confirmation before updating configuration
    # If not, simply stops the script
    if different:
        print ("")
        resp = input("Do you confirm you want to update this responder recipe ? (y/n): ")
        print ("")
        if resp != "y":
            print ("Update not confirmed, so stopping script now !")
            print ("")
            exit (0)
    else:
        print ("NONE")
        print ("")
        print ("No difference detected, so stopping script now !")
        print ("")
        exit (0)

# ---------- main

# -- parse arguments
if (len(sys.argv) == 3):
    profile     = sys.argv[1]
    input_file  = sys.argv[2]
else:
    usage()

# -- If the backup file does not exist, exit in error 
my_file = Path(input_file)
if not(my_file.is_file()):
    print (f"ERROR: the input backup file {input_file} does not exist or is not readable !")
    exit (3)

# -- get info from profile    
try:
    config = oci.config.from_file(configfile,profile)
except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Read detailed configuration from backup file
try:
    with open(input_file, 'r') as filein:
        responder_recipe = json.load(filein)
        print (f"Configuration successfully read from backup file {input_file} !")
except OSError as err:
    print (f"ERROR: {err.strerror}")
    exit (3)
except json.decoder.JSONDecodeError as err:
    print (f"ERROR in JSON input file: {err}")
    exit (4)

# -- Display main characteristics of the responder recipe in the backup file
print (f"- responder recipe name               : {responder_recipe['display_name']}")
print (f"- responder recipe id                 : {responder_recipe['id']}")
print (f"- responder recipe owner              : {responder_recipe['owner']}")
print (f"- Number of effective responder rules : {len(responder_recipe['effective_responder_rules'])}")
print ("")

# -- CloudGuardClient
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)

# -- Display differences between current configuration and configuration in backup file
# -- Stop script if no difference found, or if difference found but update not confirmed
check_differences()

# -- Build class oci.cloud_guard.models.UpdateResponderRecipeDetails from JSON content read in file
details_class = build_update_responder_recipe_class()

# -- Update responder recipe
try:
    response = CloudGuardClient.update_responder_recipe(
        responder_recipe_id = responder_recipe['id'], 
        update_responder_recipe_details = details_class,
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    print ("Responder recipe configuration successfully restored/updated !")
except Exception as err:
    print (f"ERROR: {err}")
    exit (1)

# -- the end
exit (0)
