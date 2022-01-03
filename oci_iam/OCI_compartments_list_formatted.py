#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists all the compartments and sub-compartments names and IDs in an OCI tenant using OCI Python SDK
# The output is formatted with colors and indents to easily identify parents of sub-compartments
# Note: OCI tenant given by an OCI CLI PROFILE
# It is much faster than the corresponding Bash script on tenant with many compartments
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2019-10-18: Initial Version
#    2020-04-24: minor code enhancements
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
import argparse

# ---------- Colors for output
COLOR_YELLOW="\033[93m"
COLOR_RED="\033[91m"
COLOR_GREEN="\033[32m"
COLOR_NORMAL="\033[39m"
COLOR_CYAN="\033[96m"
COLOR_BLUE="\033[94m"
COLOR_GREY="\033[90m"

# ---------- variables
configfile = "~/.oci/config"    # Define config file to be used.
flag=[0,0,0,0,0,0,0,0,0,0]

# ---------- functions
def usage():
    print ("Usage: {} [-d] -p OCI_PROFILE".format(sys.argv[0]))
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

def get_cpt_name_and_state_from_id(cpt_id):
    for c in compartments:
        if (c.id == cpt_id):
            return c.name, c.lifecycle_state
    return

def list_compartments(parent_id, level):
    # level = 0 for root, 1 for 1st level compartments, ...
    Debug=False

    if (Debug):
        print ("NEW ITER: DEBUG: level=%d parent_id=%s " % (level, parent_id), end='')
        print ("flag=",flag)
    
    i=1
    while i < level:
        if flag[i] == 0:
            print (COLOR_CYAN+"│      "+COLOR_NORMAL,end='')
        else:
            print ("       ",end='')
        i += 1    

    if level > 0:
        cptname, state = get_cpt_name_and_state_from_id (parent_id)   
   
        if flag[level] == 0:
            print (COLOR_CYAN+"├───── "+COLOR_NORMAL,end='')
        else:
            print (COLOR_CYAN+"└───── "+COLOR_NORMAL,end='')
    else:
        cptname='root'
        state="ACTIVE"
    
    if state == "ACTIVE":
        print (COLOR_GREEN+cptname+COLOR_NORMAL+" "+parent_id+COLOR_YELLOW+" ACTIVE"+COLOR_NORMAL)
    else:
        print (COLOR_BLUE+cptname+COLOR_GREY+" "+parent_id+COLOR_RED+" DELETED"+COLOR_NORMAL)

    # get the list of ids of the direct sub-compartments
    sub_compartments_ids_list=[]
    for c in compartments:
        if c.compartment_id == parent_id:
            if list_deleted or c.lifecycle_state != "DELETED":
                sub_compartments_ids_list.append(c.id)
    
    # then for each of those cpt ids, display the sub-compartments details
    if (Debug):
        print ("DEBUG: len=%d" % len(sub_compartments_ids_list))
    i=1
    for cid in sub_compartments_ids_list:     
        # if processing the last sub dir
        if (Debug):
            print ("DEBUG: test child %s" % cid)  
        if i == len(sub_compartments_ids_list):
            flag[level+1]=1
        else:
            flag[level+1]=0
        if (Debug):
            print ("DEBUG: flag", flag)
        list_compartments(cid, level+1)
        i += 1

# ---------- main

# -- parsing arguments
parser = argparse.ArgumentParser(description = "List compartments in an OCI tenant")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-d", "--list_deleted", help="List also deleted compartments", action="store_true")
args = parser.parse_args()
    
profile       = args.profile
list_deleted  = args.list_deleted
    
# -- get OCI Config
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

list_compartments(RootCompartmentID,0)

exit (0)
