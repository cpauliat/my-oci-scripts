#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script lists the Oracle provided images in a region using OCI Python SDK
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-06-12: Initial Version
#    2022-01-03: use argparse to parse arguments
#    2022-02-07: add option --shapes to list compatible shapes for each image
# ---------------------------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- usage syntax
def usage():
    print ("Usage: {} -p OCI_PROFILE [-s]".format(sys.argv[0]))
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

def list_compute_images():
    ComputeClient = oci.core.ComputeClient(config)
    response = oci.pagination.list_call_get_all_results(ComputeClient.list_images,compartment_id=RootCompartmentID)
    if len(response.data) > 0:
        for image in response.data:
            print ('{0:100s} {1:s}'.format(image.id, image.display_name))
            if list_compatible_shapes:
                response2 = oci.pagination.list_call_get_all_results(ComputeClient.list_image_shape_compatibility_entries, image_id = image.id)
                for shape in response2.data:
                    print (f"      - {shape.shape}")

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List Oracle provided images")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-s", "--shapes", help="List compatible shapes for each image", action="store_true")
args = parser.parse_args()
    
profile = args.profile
list_compatible_shapes = args.shapes

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- list images
list_compute_images()

# -- the end
exit (0)
