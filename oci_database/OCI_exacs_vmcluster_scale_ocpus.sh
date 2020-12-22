#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script scales up or down the number of OCPUs in a ExaCS VM Cluster using OCI CLI
# Note: OCI tenant and region given by an OCI CLI PROFILE
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2020-12-08: Initial Version
# --------------------------------------------------------------------------------------------------------------

usage()
{
    echo "Usage: $0 OCI_PROFILE CLOUD_VM_CLUSTER_ID NB_OCPUS"
    echo
    echo "Note: You can scale down to 0 OCPU to stop the VM cluster"
    exit 1
}
# ------ Main
if [ $# -ne 3 ]; then usage; fi

PROFILE=$1
OCID=$2
NB_OCPUS=$3

oci --profile $PROFILE db cloud-vm-cluster update --cloud-vm-cluster-id $OCID --cpu-core-count $NB_OCPUS --wait-for-state AVAILABLE