#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists the compartment names and IDs in a OCI tenant using OCI Python SDK
# FROM AN OCI COMPUTE INSTANCE WITH INSTANCE PRINCIPAL PERMISSIONS
# It will also list all subcompartments
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#
# Versions
#    2020-09-09: Initial Version
#    2020-12-12: Display full name of compartments (using parents) using colored outputs
#    2022-01-03: use argparse to parse arguments
#    2022-01-04: add --no_color option
# --------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse

# -------- colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
COLOR_YELLOW = "\033[93m"
COLOR_RED    = "\033[91m"
COLOR_GREEN  = "\033[32m"
COLOR_NORMAL = "\033[39m"
COLOR_CYAN   = "\033[96m"
COLOR_BLUE   = "\033[94m"
COLOR_GREY   = "\033[90m"

# -------- variables
flag=[0,0,0,0,0,0,0,0,0,0]

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} [-nc] [-d]".format(sys.argv[0]))
    print ("")
    print ("    If -d is provided, deleted compartments are also listed.")
    print ("    If not, only active compartments are listed.")
    print 
    exit (1)

# ---- Disable colored output
def disable_colored_output():
    global COLOR_YELLOW 
    global COLOR_RED   
    global COLOR_GREEN 
    global COLOR_NORMAL 
    global COLOR_CYAN   
    global COLOR_BLUE   
    global COLOR_GREY    

    COLOR_YELLOW = ""
    COLOR_RED    = ""
    COLOR_GREEN  = ""
    COLOR_NORMAL = ""
    COLOR_CYAN   = ""
    COLOR_BLUE   = ""
    COLOR_GREY   = ""
    
# ---- Get the complete name of compartment from its id
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

def list_compartments(parent_id, level):
    # level = 0 for root, 1 for 1st level compartments, ...
    if level > 0:
        cptname, state = get_cpt_full_name_and_state_from_id (parent_id)   
    else:
        cptname='root'
        state="ACTIVE"
    
    if state == "ACTIVE":
        #print (COLOR_GREEN+"{:60s}".format(cptname)+COLOR_NORMAL+" "+parent_id+COLOR_YELLOW+" ACTIVE"+COLOR_NORMAL)
        print (COLOR_YELLOW+"ACTIVE  "+COLOR_NORMAL+parent_id+COLOR_GREEN+" {:s}".format(cptname)+COLOR_NORMAL)
    else:
        #print (COLOR_BLUE+"{:60s}".format(cptname)+COLOR_GREY+" "+parent_id+COLOR_RED+" DELETED"+COLOR_NORMAL)
        print (COLOR_RED+"DELETED "+COLOR_GREY+parent_id+COLOR_BLUE+" {:s}".format(cptname)+COLOR_NORMAL)

    # get the list of ids of the direct sub-compartments
    sub_compartments_ids_list=[]
    for c in compartments:
        if c.compartment_id == parent_id:
            if list_deleted or c.lifecycle_state != "DELETED":
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

# -------- main

# -- parsing arguments
parser = argparse.ArgumentParser(description = "List compartments in an OCI tenant")
parser.add_argument("-d", "--list_deleted", help="List also deleted compartments", action="store_true")
parser.add_argument("-nc", "--no_color", help="Disable colored output", action="store_true")
args = parser.parse_args()
    
list_deleted = args.list_deleted
if args.no_color:
  disable_colored_output()

# -- authentication using instance principal
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
IdentityClient = oci.identity.IdentityClient(config={}, signer=signer)
RootCompartmentID = signer.tenancy_id

# -- get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

list_compartments(RootCompartmentID,0)

exit (0)
