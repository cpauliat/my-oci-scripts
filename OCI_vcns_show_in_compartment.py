#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This script lists VCNs with details in a given compartment using OCI Python SDK
#
# Details for VCNs:
# - Display-Name
# - CIDR
# - Subnets
#      - display-name
#      - CIDR
#      - the route table with route rules
#      - the security list(s) with security rules
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2020-02-27: Initial Version
# --------------------------------------------------------------------------------------------------------------------------


# -- import
import oci
import sys

# ---------- Colors for output
# see https://misc.flogisoft.com/bash/tip_colors_and_formatting to customize
colored_output=True
if (colored_output):
  COLOR_LMAGENTA="\033[95m"         # light magenta
  COLOR_LRED="\033[91m"             # light red
  COLOR_GREEN="\033[32m"            # green
  COLOR_LBLUE="\033[94m"            # light blue
  COLOR_LYELLOW="\033[93m"          # light yellow
  COLOR_CYAN="\033[36m"             # cyan
  COLOR_NORMAL="\033[39m"
else:
  COLOR_LMAGENTA=""
  COLOR_LRED=""
  COLOR_GREEN=""
  COLOR_LBLUE=""
  COLOR_LYELLOW=""
  COLOR_CYAN=""
  COLOR_NORMAL=""

# ---------- Functions

# -- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -- usage syntax
def usage():
    print ("Usage: {} OCI_PROFILE compartment_ocid".format(sys.argv[0]))
    print ("    or {} OCI_PROFILE compartment_name".format(sys.argv[0]))  
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

# -- List VCNs
def rule_details(lrule):
    if lrule.protocol=="all": 
        return "ALL"
    
    elif lrule.protocol=="1":
        return "icmp"

    elif lrule.protocol=="6":
        try:
            port_min=lrule.tcp_options.destination_port_range.min
            port_max=lrule.tcp_options.destination_port_range.max
            if (port_min == port_max):
                return "tcp  port  {:d}".format(port_min)
            else:
                return "tcp  ports {:d}-{:d}".format(port_min,port_max)
        except: 
            #tcp_options does not exist
            return "tcp  ports all"

    elif lrule.protocol=="17":
        try:
            port_min=lrule.udp_options.destination_port_range.min
            port_max=lrule.udp_options.destination_port_range.max
            if (port_min == port_max):
                return "udp  port  {:d}".format(port_min)
            else:
                return "udp  ports {:d}-{:d}".format(port_min,port_max)
        except: 
            #udp_options does not exist
            return "udp  ports all"

def list_vcns (cpt_ocid,cpt_name):
    VirtualNetworkClient = oci.core.VirtualNetworkClient(config)
    response_vcn = oci.pagination.list_call_get_all_results(VirtualNetworkClient.list_vcns,compartment_id=cpt_ocid)
    if len(response_vcn.data) > 0:
        for vcn in response_vcn.data:
            print ("")
            print (COLOR_LYELLOW+"---------------------------------------- VCN = ",end='')
            print (COLOR_LRED+'{:s}'.format(vcn.display_name)+COLOR_NORMAL,end='')
            print (COLOR_LBLUE+' {:s}'.format(vcn.cidr_block)+COLOR_NORMAL,end='')
            #print (COLOR_NORMAL+' {:s}'.format(vcn.dns_label)+COLOR_NORMAL,end='')
            print ("")
            #print (COLOR_NORMAL+' ({:s})'.format(vcn.id))
            response_subnet = oci.pagination.list_call_get_all_results(VirtualNetworkClient.list_subnets,compartment_id=cpt_ocid,vcn_id=vcn.id)
            if len(response_subnet.data) > 0:
                for subnet in response_subnet.data:
                    # subnet name, CIDR
                    print ('    subnet = '+COLOR_GREEN+'{:s}'.format(subnet.display_name),end='')
                    print (COLOR_LBLUE+' {:s}'.format(subnet.cidr_block)+COLOR_NORMAL,end='')
                    print ("")
                    #print (COLOR_NORMAL+' ({:s})'.format(subnet.id))

                    # route table and route rules
                    response_rt=VirtualNetworkClient.get_route_table(subnet.route_table_id)
                    print ("        route table   = "+COLOR_LMAGENTA+"{}".format(response_rt.data.display_name)+COLOR_NORMAL)
                    for rule in response_rt.data.route_rules:
                        print (COLOR_CYAN+"            {:18s} --> {:s}".format(rule.destination,rule.network_entity_id)+COLOR_NORMAL)

                    # security lists and security rules
                    for sl_id in subnet.security_list_ids:
                        response_sl=VirtualNetworkClient.get_security_list(sl_id)
                        print ("        security list = "+COLOR_LMAGENTA+"{}".format(response_sl.data.display_name)+COLOR_NORMAL)
                        print ("            ingress:")
                        for rule in response_sl.data.ingress_security_rules:
                            print (COLOR_CYAN+"                source       {:18s} {:s}".format(rule.source,rule_details(rule))+COLOR_NORMAL)
                        print ("            engress:")
                        for rule in response_sl.data.egress_security_rules:
                            print (COLOR_CYAN+"                destination  {:18s} {:4s}".format(rule.destination,rule_details(rule))+COLOR_NORMAL)


# ------------ main
global config
global IdentityClient
global initial_cpt_ocid
global initial_cpt_name

# -- parse arguments

if len(sys.argv) == 3:
    profile  = sys.argv[1] 
    cpt      = sys.argv[2]
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

# -- get list of compartments
response = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments, RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data
cpt_exist = False
for compartment in compartments:  
    if (cpt == compartment.id) or (cpt == compartment.name):
        initial_cpt_ocid = compartment.id
        initial_cpt_name = compartment.name
        cpt_exist = True
if not(cpt_exist):
    print ("ERROR 03: compartment '{}' does not exist !".format(cpt))
    exit (3) 

list_vcns(initial_cpt_ocid,initial_cpt_name)

# -- the end
exit (0)
