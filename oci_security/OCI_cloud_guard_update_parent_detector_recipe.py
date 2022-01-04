#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script updates or restores the configuration of a Cloud Guard "parent" (not attached to a target)
# DETECTOR RECIPE (ACTIVITY or CONFIGURATION) from a JSON backup file created with the 
# "OCI_cloud_guard_save_parent_detector_recipe.py" script in a OCI tenant using OCI Python SDK 
#
# Restored/updated parameters include:
# - recipe name
# - description
# - defined and freeform tags
# - for each detector rule:
#       - status (enabled/disabled)
#       - risk level
#       - labels
#       - input settings
#       - conditional group(s)
# 
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-16: Initial Version
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import json
import argparse
from pathlib import Path

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.
different  = False              # Is configuration in backup file different from current configuration

# -------- functions
def usage():
    print (f"Usage: {sys.argv[0]} -p OCI_PROFILE -f input_backup_file.json")
    print ("")
    print ("notes: ")
    print ("- The OCID of the detector recipe to update is stored in the backup file")
    print (f"- OCI_PROFILE must exist in {configfile} file (see example below)")
    print ("")
    print ("[EMEAOSC]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# -- Build class oci.cloud_guard.models.UpdateDetectorRecipeDetails from JSON content read in file
def build_update_detector_recipe_class():
    rules = []
    for rule in detector_recipe['effective_detector_rules']:
        # configurations
        if rule['details']['configurations'] == None:
            my_configurations = None
        else:
            my_configurations = []
            for c in rule['details']['configurations']:
                my_configurations.append(oci.cloud_guard.models.DetectorConfiguration(
                    config_key = c['config_key'],
                    data_type  = c['data_type'],
                    name       = c['name'],
                    value      = c['value'],
                    values     = c['values']               
                ))

        # conditional groups
        if rule['details']['condition'] == None:
            my_condition = None
        else:
            if rule['details']['condition']['kind'] == "SIMPLE":
                my_condition = oci.cloud_guard.models.SimpleCondition(
                    kind = "SIMPLE",
                    operator = rule['details']['condition']['operator'],
                    parameter = rule['details']['condition']['parameter'],
                    value = rule['details']['condition']['value'],
                    value_type = rule['details']['condition']['value_type']
                )
            else:
                # TO TEST
                my_condition = oci.cloud_guard.models.CompositeCondition(
                    kind = rule['details']['condition']['kind'],
                    composite_operator = rule['details']['condition']['composite_operator'],   
                    left_operand = rule['details']['condition']['left_operand'],   
                    right_operand = rule['details']['condition']['right_operand']
                )

        # 
        new_rule_details = oci.cloud_guard.models.UpdateDetectorRuleDetails(
            risk_level = rule['details']['risk_level'], 
            is_enabled = rule['details']['is_enabled'],
            configurations = my_configurations,
            condition = my_condition)
        new_rule = oci.cloud_guard.models.UpdateDetectorRecipeDetectorRule(
            detector_rule_id = rule['detector_rule_id'], 
            details = new_rule_details)
        rules.append(new_rule)

    details = oci.cloud_guard.models.UpdateDetectorRecipeDetails(
        defined_tags   = detector_recipe['defined_tags'], 
        description    = detector_recipe['description'], 
        detector_rules = rules, 
        display_name   = detector_recipe['display_name'], 
        freeform_tags  = detector_recipe['freeform_tags'])   
    
    return details

# -- Check differences between current configuration and configuration in backup file
def check_differences():
    global different

    print ("DIFFERENCES between current configuration and configuration in file: ", end="")

    # get current configuration of the detector recipe
    response = CloudGuardClient.get_detector_recipe(detector_recipe_id=detector_recipe['id'])
    current_recipe = response.data

    # check differences in the display_name
    if detector_recipe['display_name'] != current_recipe.display_name:
        different = True
        print ("")
        print (f"- CURRENT display_name  : {current_recipe.display_name}")
        print (f"- NEW     display_name  : {detector_recipe['display_name']}")

    # check differences in the description
    if detector_recipe['description'] != current_recipe.description:
        different = True
        print ("")
        print (f"- CURRENT description   : {current_recipe.description}")
        print (f"- NEW     description   : {detector_recipe['description']}")

    # check differences in the defined_tags
    if detector_recipe['defined_tags'] != current_recipe.defined_tags:
        different = True
        print ("")
        print (f"- CURRENT defined_tags  : {current_recipe.defined_tags}")
        print (f"- NEW     defined_tags  : {detector_recipe['defined_tags']}")

    # check differences in the freeform_tags
    if detector_recipe['freeform_tags'] != current_recipe.freeform_tags:
        different = True
        print ("")
        print (f"- CURRENT freeform_tags : {current_recipe.freeform_tags}")
        print (f"- NEW     freeform_tags : {detector_recipe['freeform_tags']}")

    # check differences in each detector rule
    for current_rule in current_recipe.effective_detector_rules:
        rule_found = False
        for new_rule in detector_recipe['effective_detector_rules']:
            if new_rule['detector_rule_id'] == current_rule.detector_rule_id:
                rule_found = True
                break
            
        # if the current rule ID does not exist in backup, stop the script
        if not(rule_found):
            print (f"ERROR: rule id {current_rule.detector_rule_id} not found in backup --> edit backup file, add this rule and re-run the script !")
            exit (5)
        # otherwise, check enabled status, risk level, settings and conditional group
        else:

            # comparing status: "details.is_enabled"
            if current_rule.details.is_enabled != new_rule['details']['is_enabled']:
                different = True
                print ("")
                print (f"- Detector rule id {current_rule.detector_rule_id}")
                print (f"  - CURRENT is_enabled : {current_rule.details.is_enabled}")
                print (f"  - NEW     is_enabled : {new_rule['details']['is_enabled']}")

            # comparing risk levels: "details.risk_level"
            if current_rule.details.risk_level != new_rule['details']['risk_level']:
                different = True
                print ("")
                print (f"- Detector rule id {current_rule.detector_rule_id}")
                print (f"  - CURRENT risk_level : {current_rule.details.risk_level}")
                print (f"  - NEW     risk_level : {new_rule['details']['risk_level']}")

            # comparing configurations (settings) if they exists (for config_key and value)
            try:
                for new_config in new_rule['details']['configurations']:
                    for current_config in current_rule.details.configurations:
                        if current_config.config_key == new_config['config_key']:
                            break
                    if current_config.value != new_config['value']:
                        different = True
                        print ("")
                        print (f"- Detector rule id {current_rule.detector_rule_id}")
                        print (f"  - CURRENT configurations key {current_config.config_key} : {current_config.value}")
                        print (f"  - NEW     configurations key {current_config.config_key} : {new_config['value']}")                    
            except:
                pass

            # comparing condition (conditional group) if it exists
            #try:
            if current_rule.details.condition != None:
                current_condition_dict = {}
                current_condition_dict['kind']       = current_rule.details.condition.kind
                current_condition_dict['operator']   = current_rule.details.condition.operator
                current_condition_dict['parameter']  = current_rule.details.condition.parameter
                current_condition_dict['value']      = current_rule.details.condition.value
                current_condition_dict['value_type'] = current_rule.details.condition.value_type
            else:
                current_condition_dict = None

            if current_condition_dict != new_rule['details']['condition']:
                different = True
                print ("")    
                print (f"- Detector rule id {current_rule.detector_rule_id}")
                print (f"  - CURRENT condition : {current_condition_dict}")
                print (f"  - NEW     condition : {new_rule['details']['condition']}")

    # If differences are found, ask for confirmation before updating configuration
    # If not, simply stops the script
    if different:
        print ("")
        resp = input("Do you confirm you want to update this detector recipe ? (y/n): ")
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

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Update a Cloud Guard detector recipe from a backup file")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-f", "--file", help="input file (.json)", required=True)
args = parser.parse_args()
    
profile    = args.profile
input_file = args.file

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
        detector_recipe = json.load(filein)
        print (f"Configuration successfully read from backup file {input_file} !")
except OSError as err:
    print (f"ERROR: {err.strerror}")
    exit (3)
except json.decoder.JSONDecodeError as err:
    print (f"ERROR in JSON input file: {err}")
    exit (4)

# -- Display main characteristics of the detector recipe in the backup file
print (f"- Detector recipe name               : {detector_recipe['display_name']}")
print (f"- Detector recipe id                 : {detector_recipe['id']}")
print (f"- Detector recipe type               : {detector_recipe['detector']}")
print (f"- Detector recipe owner              : {detector_recipe['owner']}")
print (f"- Number of effective detector rules : {len(detector_recipe['effective_detector_rules'])}")
print ("")

# -- CloudGuardClient
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)

# -- Display differences between current configuration and configuration in backup file
# -- Stop script if no difference found, or if difference found but update not confirmed
check_differences()

# -- Build class oci.cloud_guard.models.UpdateDetectorRecipeDetails from JSON content read in file
details_class = build_update_detector_recipe_class()

# -- Update detector recipe
try:
    response = CloudGuardClient.update_detector_recipe(
        detector_recipe_id = detector_recipe['id'], 
        update_detector_recipe_details = details_class,
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    print ("Detector recipe configuration successfully restored/updated !")
except Exception as err:
    print (f"ERROR: {err}")
    exit (1)

# -- the end
exit (0)
