#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists the IAM policies for all compartments in a OCI tenant using OCI Python SDK
# It will also list all sub-compartments
# Note: OCI tenant given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-06-25: Initial Version
#    2021-06-25: Improved display by Matthieu Bordonne
# --------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import re
from datetime import datetime

# ---------- Colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
colored_output=True
if (colored_output):
    COLOR_YELLOW="\033[93m"
    COLOR_RED="\033[91m"
    COLOR_GREEN="\033[32m"
    COLOR_NORMAL="\033[39m"
    COLOR_CYAN="\033[96m"
    COLOR_BLUE="\033[94m"
    COLOR_GREY="\033[90m"
else:
    COLOR_YELLOW=""
    COLOR_RED=""
    COLOR_GREEN=""
    COLOR_NORMAL=""
    COLOR_CYAN=""
    COLOR_BLUE=""
    COLOR_GREY=""

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.
flag=[0,0,0,0,0,0,0,0,0,0]

# ---------- functions
def usage():
    print (f"Usage: {sys.argv[0]} [-d] OCI_PROFILE")
    print ("")
    print (f"note: OCI_PROFILE must exist in {configfile} file (see example below)")
    print ("")
    print ("[EMEAOSCf]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

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

def get_cpt_full_name_and_state_from_id(cpt_id):
    for c in compartments:
        if (c.id == cpt_id):
            return cpt_full_name(c), c.lifecycle_state
    return

def list_policies_in_compartment(cpt_id, cpt_name):
    resp = oci.pagination.list_call_get_all_results(IdentityClient.list_policies, cpt_id)
    policies = resp.data
    if len(policies) > 0:
        print (COLOR_YELLOW+"Compartment "+COLOR_GREEN+f"{cpt_name:s}"+COLOR_NORMAL)
        for policy in policies:
            try:
                creator = policy.defined_tags['osc']['created-by']
            except:
                try:
                    creator = policy.defined_tags['Oracle-Tags']['CreatedBy']
                except:
                    creator = "??"
            creator_stripped = re.sub('^.*/','',creator)
            print (f"    - {policy.name:40s} \n               created on {policy.time_created.strftime('%m/%d/%Y')},  by {creator_stripped}\n               Description:  {policy.description:s}")

def list_compartments(parent_id, level):
    # level = 0 for root, 1 for 1st level compartments, ...
    if level > 0:
        cptname, state = get_cpt_full_name_and_state_from_id (parent_id)   
    else:
        cptname='root'
        state="ACTIVE"
    
    if state == "ACTIVE":
        list_policies_in_compartment(parent_id, cptname)

    # get the list of ids of the direct sub-compartments
    sub_compartments_ids_list=[]
    for c in compartments:
        if c.compartment_id == parent_id:
            if c.lifecycle_state != "DELETED":
                sub_compartments_ids_list.append(c.id)
    
    # then for each of those cpt ids, display the sub-compartments details
    i=1
    for cid in sub_compartments_ids_list:     
        # if processing the last sub dir
        if i == len(sub_compartments_ids_list):
            flag[level+1]=1
        else:
            flag[level+1]=0
        list_compartments(cid, level+1)
        i += 1

# ---------- main

# -- parsing arguments
if (len(sys.argv) == 2):
    profile = sys.argv[1] 
else:
    usage()
    
# -- get OCI Config
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

list_compartments(RootCompartmentID,0)

exit (0)
