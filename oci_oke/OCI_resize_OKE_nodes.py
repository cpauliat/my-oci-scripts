#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script changes the shape or nb of cpus or memory size of nodes in an OKE node pool
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK (version 2.48 or later) installed
#                 - OCI config file configured with profiles
#                 - install and configure kubectl
# Versions
#    2021-12-08: Initial Version
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import time
import os
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions
def usage():
    print (f"Usage: {sys.argv[0]} -p OCI_PROFILE -id oke_node_pool_id -s new_shape [-c new_ocpus] [-m new_memory_in_gb]")
    print ( "")
    print ( "Notes: ")
    print ( "- Examples of shapes: VM.Standard.E2.4, VM.Standard.E3.Flex, VM.Standard.E4.Flex...")
    print (f"- new_ocpus new_memory_in_gb are only needed for Flexible shapes")
    print (f"- OCI_PROFILE must exist in {configfile} file (see example below)")
    print ( "")
    print ( "[EMEAOSC]")
    print ( "tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ( "user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ( "fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ( "key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ( "region      = eu-frankfurt-1")
    exit (1)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Change shape of compute instances in an OKE node pool")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-id", "--oke_node_pool_ocid", help="Node Pool OCID", required=True)
parser.add_argument("-s", "--shape", help="New shape for compute instances in node pool", required=True)
parser.add_argument("-c", "--ocpus", help="Number of OCPUs for new flexible shape")
parser.add_argument("-m", "--memory_in_gbs", help="Amount of memory (GB) for new flexible shape")
args = parser.parse_args()

profile           = args.profile
oke_node_pool_id  = args.oke_node_pool_ocid
new_shape         = args.shape

if args.ocpus:
    try:
        new_ocpus = int(args.ocpus)
    except Exception as err:
        print (f"ERROR: ocpus must be an integer ({err}) !")
        exit (1)

if args.memory_in_gbs:
    try:
        new_memory_in_gbs = int(args.memory_in_gbs)
    except Exception as err:
        print (f"ERROR: memory_in_gbs must be an integer ({err}) !")
        exit (1)

# -- get info from profile
try:
    config = oci.config.from_file(configfile, profile)
except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- Get the list of nodes from OKE node pool ID
ContainerEngineClient = oci.container_engine.ContainerEngineClient(config)
response  = ContainerEngineClient.get_node_pool(oke_node_pool_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
node_pool = response.data
nodes     = node_pool.nodes 

#print (node_pool)

print ("====== List of active nodes found in the nodes pool:")
for node in nodes:
    if node.lifecycle_state == "ACTIVE":
        print(f"- {node.name}   {node.private_ip:15s}  {node.id} ")
print ("")

# -- Change the shape OR nb of OCPUs OR memory for the node pool 
# -- (for future additonal nodes in this pool)
print (f"====== Changing shape configuration in the pool for future additional nodes")
new_shape_config = oci.container_engine.models.UpdateNodeShapeConfigDetails(ocpus = new_ocpus, memory_in_gbs = new_memory_in_gbs)
details   = oci.container_engine.models.UpdateNodePoolDetails(node_shape = new_shape, node_shape_config = new_shape_config)
response  = ContainerEngineClient.update_node_pool(oke_node_pool_id, details, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
print ("")

# -- Change the shape OR nb of OCPUs OR memory for those nodes
ComputeClient = oci.core.ComputeClient(config)

for node in nodes:
    if node.lifecycle_state == "ACTIVE":
        print (f"====== Processing node {node.name} ({node.private_ip})...")

        # put the node in maintenance mode (evacuate PODs)
        print ("- Draining node with 'kubectl drain' command")
        os.system(f"kubectl drain {node.private_ip} --force --ignore-daemonsets")

        # resize
        print (f"- Changing shape or shape config for the compute instance")
        new_shape_config = oci.core.models.UpdateInstanceShapeConfigDetails(ocpus = new_ocpus, memory_in_gbs = new_memory_in_gbs)
        details  = oci.core.models.UpdateInstanceDetails(shape = new_shape, shape_config = new_shape_config)
        response = ComputeClient.update_instance(node.id, details, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)

        # wait a few minutes for the resize to be completed
        print (f"  Wait for 3 minutes for the resize operation to complete")
        time.sleep (180)     

        # 
        print ("- Re-enabling node with 'kubectl uncordon' command")
        os.system(f"kubectl uncordon {node.private_ip}")

        print ("")

# -- Happy end
exit(0)