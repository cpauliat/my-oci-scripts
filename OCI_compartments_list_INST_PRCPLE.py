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
# --------------------------------------------------------------------------------------------------------------


# -- import
import oci
import sys

# -- functions
def usage():
    print ("Usage: {} [-d]".format(sys.argv[0]))
    print ("")
    print ("    If -d is provided, deleted compartments are also listed.")
    print ("    If not, only active compartments are listed.")
    print 
    exit (1)

# -- main
LIST_DELETED=False

if (len(sys.argv) != 1) and (len(sys.argv) != 2):
    usage()

if (len(sys.argv) == 2):
    if (sys.argv[1] == "-d"):
        LIST_DELETED=True
    else:
        usage()
    
# -- authentication using instance principal
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
identity = oci.identity.IdentityClient(config={}, signer=signer)

RootCompartmentID = signer.tenancy_id

response = oci.pagination.list_call_get_all_results(identity.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments = response.data

print ("Compartment name               State    Compartment OCID")
print ("RootCompartment                ACTIVE   {}".format(RootCompartmentID))

for c in compartments:
    if LIST_DELETED or (c.lifecycle_state != "DELETED"):
        print ("{:30s} {:9s} {}".format(c.name,c.lifecycle_state,c.id))

exit (0)
