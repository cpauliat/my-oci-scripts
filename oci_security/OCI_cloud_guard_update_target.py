#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script updates or restores the configuration of a Cloud Guard target from a JSON backup file created 
# with the "OCI_cloud_guard_save_target.py" script in a OCI tenant using OCI Python SDK 
#
# Restored/updated parameters include:
# - target name
# - defined and freeform tags
# - for detector recipes (if present in backup file):
#       - conditional groups for detector rules
# - for responder recipe (if present in backup file)
#       - rule trigger (Ask me before executing rule OR Execute automatically)
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
#    2021-11-19: Initial Version
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------

# ---------- import
import oci
import sys
import json
import argparse
from pathlib import Path

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.
different  = False              # Is configuration in backup file different from current configuration

# ---------- functions
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

# ---- Get the full name of compartment from its id
def get_cpt_parent(cpt):
    if (cpt.id == RootCompartmentID):
        return "root"
    else:
        for c in compartments:
            if c.id == cpt.compartment_id:
                break
        return (c)

def cpt_full_name(cpt):
    if cpt.id == RootCompartmentID:
        return ""
    else:
        # if direct child of root compartment
        if cpt.compartment_id == RootCompartmentID:
            return cpt.name
        else:
            parent_cpt = get_cpt_parent(cpt)
            return cpt_full_name(parent_cpt)+":"+cpt.name

def get_cpt_full_name_from_id(cpt_id):
    if cpt_id == RootCompartmentID:
        return "root"
    else:
        for c in compartments:
            if (c.id == cpt_id):
                return cpt_full_name(c)
    return

# -- Build class oci.cloud_guard.models.UpdateTargetDetails from JSON content read in file
def build_update_target_class():

    # 
    target_detector_recipes = []
    for target_detector_recipe in target['target_detector_recipes']: 
        rules = []
        for rule in target_detector_recipe['effective_detector_rules']:
            # if we have conditions groups, use them
            if rule['details']['condition_groups'] != None:
                condition_groups = []
                for condition_group in rule['details']['condition_groups']:
                    if condition_group['condition']['kind'] == "SIMPLE":
                        my_condition = oci.cloud_guard.models.SimpleCondition(
                            kind       = "SIMPLE",
                            operator   = condition_group['condition']['operator'],
                            parameter  = condition_group['condition']['parameter'],
                            value      = condition_group['condition']['value'],
                            value_type = condition_group['condition']['value_type']
                        )
                    else:
                        # TO TEST
                        my_condition = oci.cloud_guard.models.CompositeCondition(
                            kind               = condition_group['condition']['kind'],
                            composite_operator = condition_group['condition']['composite_operator'],
                            left_operand       = condition_group['condition']['left_operand'],
                            right_operand      = condition_group['condition']['right_operand']
                        )

                    condition_groups.append(oci.cloud_guard.models.ConditionGroup(
                        compartment_id = condition_group['compartment_id'],
                        condition = my_condition)
                    )
            else:
            # Otherwise, use None
                condition_groups = None

            rules.append(oci.cloud_guard.models.UpdateTargetRecipeDetectorRuleDetails(
                detector_rule_id = rule['detector_rule_id'],
                details = oci.cloud_guard.models.UpdateTargetDetectorRuleDetails(
                    condition_groups = condition_groups)       
            ))   
        target_detector_recipes.append(oci.cloud_guard.models.UpdateTargetDetectorRecipe(
            target_detector_recipe_id = target_detector_recipe['id'],
            detector_rules = rules
        ))

    # 
    target_responder_recipes = []
    for target_responder_recipe in target['target_responder_recipes']:  
        rules = []
        for rule in target_responder_recipe['effective_responder_rules']:
            rules.append(oci.cloud_guard.models.UpdateTargetRecipeResponderRuleDetails(
                responder_rule_id = rule['responder_rule_id'],
                details = oci.cloud_guard.models.UpdateTargetResponderRuleDetails(
                    mode           = rule['details']['mode'],
                    condition      = rule['details']['condition'],
                    configurations = rule['details']['configurations']) 
            ))        
        target_responder_recipes.append(oci.cloud_guard.models.UpdateTargetResponderRecipe(
            target_responder_recipe_id = target_responder_recipe['id'],
            responder_rules = rules
        ))

    details = oci.cloud_guard.models.UpdateTargetDetails(
        defined_tags             = target['defined_tags'], 
        display_name             = target['display_name'], 
        freeform_tags            = target['freeform_tags'],
        target_detector_recipes  = target_detector_recipes, 
        target_responder_recipes = target_responder_recipes)   
    
    return details

# -- Check target_detector_recipes  differences between current configuration and configuration in backup file
def check_differences_target_detector_recipes(current_target):

    l_different = False
    for current_target_detector_recipe in current_target.target_detector_recipes:

        # find matching target detector recipe in backup file
        detector_recipe_found = False
        for new_detector_recipe in target['target_detector_recipes']:
            if new_detector_recipe['detector'] == current_target_detector_recipe.detector:
                detector_recipe_found = True
                break

        # if no matching recipe found
        if not(detector_recipe_found):
            l_different = True
            print ("")
            print (f"- Target detector recipe {current_target_detector_recipe.detector}")
            print ( "  - CURRENT : recipe exists")
            print ( "  - NEW     : no recipe")   
        # otherwise, we look for differences in detector rules condition_groups
        else:
            for current_rule in current_target_detector_recipe.effective_detector_rules:
                rule_found = False
                for new_rule in new_detector_recipe['effective_detector_rules']:
                    if new_rule['detector_rule_id'] == current_rule.detector_rule_id:
                        rule_found = True
                        break
            
                # if the current rule ID does not exist in backup, stop the script
                if not(rule_found):
                    print (f"ERROR: rule id {current_rule.detector_rule_id} not found in backup --> edit backup file, add this rule and re-run the script !")
                    exit (5)
                # otherwise, check condition_groups
                else:
                    # comparing condition_groups parameter if it exists
                    if current_rule.details.condition_groups == None:
                        current_condition_groups_dict = None
                    else:
                        current_condition_groups_dict = []
                        for current_condition_group in current_rule.details.condition_groups:
                            current_condition_dict = {}
                            current_condition_dict['kind']       = current_condition_group.condition.kind
                            current_condition_dict['operator']   = current_condition_group.condition.operator
                            current_condition_dict['parameter']  = current_condition_group.condition.parameter
                            current_condition_dict['value']      = current_condition_group.condition.value
                            current_condition_dict['value_type'] = current_condition_group.condition.value_type

                            current_condition_groups_dict.append(
                                { 'compartment_id' : current_condition_group.compartment_id, 'condition': current_condition_dict })

                    if current_condition_groups_dict != new_rule['details']['condition_groups']:
                        l_different = True
                        print ("")    
                        print (f"- Target detector recipe {current_target_detector_recipe.detector}")
                        print (f"  - Detector rule id {current_rule.detector_rule_id}")
                        print (f"    - CURRENT condition : {current_condition_groups_dict}")
                        print (f"    - NEW     condition : {new_rule['details']['condition_groups']}")

    return l_different

# -- Check target_responder_recipes  differences between current configuration and configuration in backup file
def check_differences_target_responder_recipes(current_target):

    l_different = False

    # we have 0 or 1 target_responder_recipe for current_target and  backup target
    # so if len() is different, then a recipe is missing in current target or backup target
    if len(current_target.target_responder_recipes) != len(target['target_responder_recipes']):
        l_different = True
        print ("")
        print ("- Target responder recipe ")
        if len(current_target.target_responder_recipes) == 0:
            print ("  - CURRENT : no recipe")
            print ("  - NEW     : recipe exists")  
        else:
            print ("  - CURRENT : recipe exists")
            print ("  - NEW     : no recipe")  
    
    else:
    # otherwise, the responder recipe is present in both targets
    # so we then compare responder rules
        # find matching target detector recipe in backup file
        for current_rule in current_target.target_responder_recipes[0].effective_responder_rules:
            rule_found = False
            # find matching rule backup file
            for new_rule in target['target_responder_recipes'][0]['effective_responder_rules']:
                if new_rule['responder_rule_id'] == current_rule.responder_rule_id:
                    rule_found = True
                    break
        
            # if the current rule ID does not exist in backup, stop the script
            if not(rule_found):
                print (f"ERROR: rule id {current_rule.responder_rule_id} not found in backup --> edit backup file, add this rule and re-run the script !")
                exit (5)
            # otherwise, check mode, condition and configurations
            else:
                # comparing mode
                if current_rule.details.mode != new_rule['details']['mode']:
                    l_different = True
                    print ("")    
                    print (f"- Target responder recipe")
                    print (f"  - Responder rule id {current_rule.responder_rule_id}")
                    print (f"    - CURRENT condition : {current_rule.details.mode}")
                    print (f"    - NEW     condition : {new_rule['details']['mode']}")

                # comparing condition (conditional group) if it exists
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
                    l_different = True
                    print ("")    
                    print (f"- Target responder recipe")
                    print (f"  - Responder rule id {current_rule.responder_rule_id}")
                    print (f"    - CURRENT condition : {current_condition_dict}")
                    print (f"    - NEW     condition : {new_rule['details']['condition']}")

                # comparing configurations
                current_configurations_list = []
                for current_configuration in current_rule.details.configurations:
                    current_configuration_dict = {}
                    current_configuration_dict['config_key'] = current_configuration.config_key
                    current_configuration_dict['name']       = current_configuration.name
                    current_configuration_dict['value']      = current_configuration.value
                    current_configurations_list.append(current_configuration_dict)

                if current_configurations_list != new_rule['details']['configurations']:
                    l_different = True
                    print ("")    
                    print (f"- Target responder recipe")
                    print (f"  - Responder rule id {current_rule.responder_rule_id}")
                    print (f"    - CURRENT configurations : {current_configurations_list}")
                    print (f"    - NEW     configurations : {new_rule['details']['configurations']}")

    return l_different

# -- Check target differences between current configuration and configuration in backup file
def check_differences():

    global different

    print ("DIFFERENCES between current configuration and configuration in file: ", end="")

    # get current configuration of the target
    response = CloudGuardClient.get_target(target_id=target['id'])
    current_target = response.data

    # check differences in the display_name
    if target['display_name'] != current_target.display_name:
        different = True
        print ("")
        print (f"- CURRENT display_name  : {current_target.display_name}")
        print (f"- NEW     display_name  : {target['display_name']}")

    # check differences in the description
    if target['description'] != current_target.description:
        different = True
        print ("")
        print (f"- CURRENT description   : {current_target.description}")
        print (f"- NEW     description   : {target['description']}")

    # check differences in the defined_tags
    if target['defined_tags'] != current_target.defined_tags:
        different = True
        print ("")
        print (f"- CURRENT defined_tags  : {current_target.defined_tags}")
        print (f"- NEW     defined_tags  : {target['defined_tags']}")

    # check differences in the freeform_tags
    if target['freeform_tags'] != current_target.freeform_tags:
        different = True
        print ("")
        print (f"- CURRENT freeform_tags : {current_target.freeform_tags}")
        print (f"- NEW     freeform_tags : {target['freeform_tags']}")

    # check rules differences in target_detector_recipes (only condition_groups)
    if check_differences_target_detector_recipes(current_target):
        different = True

    # check rules differences in target_responder_recipes (only mode, conditions, configurations)
    if check_differences_target_responder_recipes(current_target):
        different = True

    # If differences are found, ask for confirmation before updating configuration
    # If not, simply stops the script
    if different:
        print ("")
        resp = input("Do you confirm you want to update this target ? (y/n): ")
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
parser = argparse.ArgumentParser(description = "Update a Cloud Guard target from a backup file")
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

# -- get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

# -- Read detailed configuration from backup file
try:
    with open(input_file, 'r') as filein:
        target = json.load(filein)
        print (f"Configuration successfully read from backup file {input_file} !")
except OSError as err:
    print (f"ERROR: {err.strerror}")
    exit (3)
except json.decoder.JSONDecodeError as err:
    print (f"ERROR in JSON input file: {err}")
    exit (4)

# -- Display main characteristics of the target in the backup file
print (f"- target name          : {target['display_name']}")
print (f"- target ocid          : {target['id']}")
print (f"- target resource id   : {target['target_resource_id']}")
print (f"- target resource name : {get_cpt_full_name_from_id(target['target_resource_id'])}")
print (f"- compartment          : {get_cpt_full_name_from_id(target['compartment_id'])}")
print (f"- recipe count         : {target['recipe_count']}")
print ("")

# -- CloudGuardClient
CloudGuardClient = oci.cloud_guard.CloudGuardClient(config)

# -- Display differences between current configuration and configuration in backup file
# -- Stop script if no difference found, or if difference found but update not confirmed
check_differences()

# -- Build class oci.cloud_guard.models.UpdateTargetDetails from JSON content read in file
details_class = build_update_target_class()

# -- Update target
try:
    response = CloudGuardClient.update_target(
        target_id = target['id'], 
        update_target_details = details_class,
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    print ("Target configuration successfully restored/updated !")
except Exception as err:
   print (f"ERROR: {err}")
   exit (1)

# -- the end
exit (0)
