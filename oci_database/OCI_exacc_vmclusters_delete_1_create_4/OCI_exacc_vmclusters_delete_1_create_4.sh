#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script replaces the default "big" VM cluster in an Exadata Cloud at customer machine (ExaCC)
# by 4 smaller VM clusters.
# 
# The detailed steps are:
# 1: delete existing VM cluster (keeping the existing VM cluster network)
# 2: create and validate 3 new VM cluster networks
# 3: create 4 new VM clusters
#
# Note: 
# - OCI tenant and region given by an OCI CLI PROFILE
# - This script is provided as-is as an example without support
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : jq (JSON parser) installed, OCI CLI installed and OCI config file configured with profiles
#
# Versions
#    2022-07-15: Initial Version (several scripts)
#    2022-08-05: Combine all individual scripts into a single one, replace hard-coded values by parameters
# --------------------------------------------------------------------------------------------------------------

# -------- Variable

# -------- Functions

usage()
{
    echo "Usage: $0 <config_file>.cfg <step_number>"
    echo
    echo "Step number: 1, 2, 3 or all"
    exit 1
}

get_date_time()
{
    date '+%Y-%m-%d_%H:%M:%S'
}

check_config_file()
{
    # check that config files contains the required parameters
    cfg_file=$1
    ok=true
    for v in OCI_CLI_PROFILE EXADATA_INFRASTRUCTURE_OCID TO_BE_DELETED_VM_CLUSTER_OCID TO_BE_REUSED_VM_CLUSTER_NETWORK_OCID NB_NEW_VM_CLUSTERS VM_CLUSTER_NETWORKS_JSON_FILES VM_CLUSTERS_JSON_FILES
    do
        grep "^${v}=" $cfg_file >/dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "ERROR: missing parameter $v in config file $cfg_file !"
            ok=false
        fi
    done
    if [ "$ok" != true ]; then exit 4; fi

    # check the existence of JSON files for VM cluster networks
    nb=`expr $NB_NEW_VM_CLUSTERS - 1`
    nbm1=`expr $nb - 1`
    IFS=" " 
    VMCNET_FILES=($VM_CLUSTER_NETWORKS_JSON_FILES)
    i=0
    while [ $i -lt $nbm1 ]; do
        if [ ! -f ${VMCNET_FILES[$i]} ]; then
            echo "ERROR: file ${VMCNET_FILES[$i]} does not exist or is not readable !"
            ok=false
        fi
        i=`expr $i + 1`
    done
    if [ "$ok" != true ]; then exit 5; fi

    # check the existence of JSON files for VM clusters
    nbm1=`expr $NB_NEW_VM_CLUSTERS - 1`
    IFS=" " 
    VMC_FILES=($VM_CLUSTERS_JSON_FILES)
    i=0
    while [ $i -lt $nbm1 ]; do
        if [ ! -f ${VMC_FILES[$i]} ]; then
            echo "ERROR: file ${VMC_FILES[$i]} does not exist or is not readable !"
            ok=false
        fi
        i=`expr $i + 1`
    done
    if [ "$ok" != true ]; then exit 6; fi
}

get_vm-cluster_status()
{
    vm_cluster_id=$1
    oci db vm-cluster get --vm-cluster-id $vm_cluster_id | jq -r '.data."lifecycle-state"'
}

wait_for_vm-cluster_status()
{
    vm_cluster_id=$1
    expected_status=$2    
    status=`get_vm-cluster_status $vm_cluster_id`
    new_line_required=false
    while [ "$status" != "$expected_status" ]; do
        new_line_required=true
        printf "."
        sleep 60
        status=`get_vm-cluster_status $vm_cluster_id`
    done
    if [ "$new_line_required" == true ]; then echo; fi
}

get_vm-cluster-network_status()
{
    vm_cluster_network_id=$1
    oci db vm-cluster-network get --vm-cluster-network-id $vm_cluster_network_id | jq -r '.data."lifecycle-state"'
}

wait_for_vm-cluster-network_status()
{
    vm_cluster_network_id=$1
    expected_status=$2    
    status=`get_vm-cluster-network_status $vm_cluster_network_id`
    new_line_required=false
    while [ "$status" != "$expected_status" ]; do
        new_line_required=true
        printf "."
        sleep 60
        status=`get_vm-cluster-network_status $vm_cluster_network_id`
    done
    if [ "$new_line_required" == true ]; then echo; fi
}

step1_delete_vm_cluster()
{
    echo "======== `get_date_time`: Step 1: deleting existing VM cluster"
    echo "oci db vm-cluster delete --force --vm-cluster-id $TO_BE_DELETED_VM_CLUSTER_OCID"
    #oci db vm-cluster delete --force --vm-cluster-id $TO_BE_DELETED_VM_CLUSTER_OCID
    # Output is similar to following (JSON)
    # {
    #     "opc-work-request-id": "ocid1.coreservicesworkrequest.oc1.uk-london-1.abwgiljrmygmcrkj4jnblk4zlo7w45yvmqyolbyjqy7jwv7kos3xoqzl3kga"
    # }

    # Wait for the VM cluster to be TERMINATED
    wait_for_vm-cluster_status $TO_BE_DELETED_VM_CLUSTER_OCID "TERMINATED"
    echo "`get_date_time`: VM cluster terminated !"
    echo
}

step2_create_and_validate_vm_cluster_networks()
{
    nb=`expr $NB_NEW_VM_CLUSTERS - 1`
    nbm1=`expr $nb - 1`
    echo "======== `get_date_time`: Step 2: creating and validating ${nb} VM cluster networks"

    i=0
    while [ $i -lt $nbm1 ]; do
        # -- Create a VM cluster network
        echo "---- `get_date_time`: Create VM cluster network #`expr $i + 2`"
        echo "oci db vm-cluster-network create --from-json file://${VMCNET_FILES[$i]}"
        vmcnet_id=`oci db vm-cluster-network create --from-json file://${VMCNET_FILES[$i]} | jq -r '.data.id'`
        # Output is similar to following (JSON)
        # {
        # ...
        #     "id": "ocid1.vmclusternetwork.oc1.uk-london-1.anwgiljrnmvrbeaakyuxdvmb6skjztraew7mvhcgb2klaqp7gdg6xpihxmwq",
        # ...
        # }
        wait_for_vm-cluster-network_status $vmcnet_id "REQUIRES_VALIDATION"
        echo "VM cluster network created: ID = $vmcnet_id"
        echo

        # -- Validate a VM cluster network
        echo "---- `get_date_time`: Validate VM cluster network #`expr $i + 2`"
        echo "oci db vm-cluster-network validate --exadata-infrastructure-id $EXADATA_INFRASTRUCTURE_OCID --vm-cluster-network-id $vmcnet_id"
        oci db vm-cluster-network validate --exadata-infrastructure-id $EXADATA_INFRASTRUCTURE_OCID --vm-cluster-network-id $vmcnet_id > /dev/null
        # Output is similar to following (JSON)
        # {
        # ...
        #     "id": "ocid1.vmclusternetwork.oc1.uk-london-1.anwgiljrnmvrbeaakyuxdvmb6skjztraew7mvhcgb2klaqp7gdg6xpihxmwq",
        # ...
        # }
        wait_for_vm-cluster-network_status $vmcnet_id "VALIDATED"     # takes approximately 
        echo "VM cluster network validated: ID = $vmcnet_id"
        echo

        # -- Save VM cluster network ID in the JSON file for VM cluster creation
        vmc_file=${VMC_FILES[`expr $i + 1`]}
        echo "---- `get_date_time`: Update VM cluster network ID in file ${vmc_file}"
        cp -p ${vmc_file} ${vmc_file}.bak
        sed "s/\"vmClusterNetworkId\".*$/\"vmClusterNetworkId\": \"${vmcnet_id}\"/g" ${vmc_file}.bak > ${vmc_file}
        echo

        # -- go to next VM cluster network
        i=`expr $i + 1`
    done
}

step3_create_vm_clusters()
{
    echo "======== `get_date_time`: Step 3: creating ${NB_NEW_VM_CLUSTERS} VM clusters in PARALLEL"
    nbm1=`expr $NB_NEW_VM_CLUSTERS - 1`

    # First, submit the creation of all VM clusters in parallel
    VMC_IDS=()
    i=0
    while [ $i -lt $nbm1 ]; do
        echo "---- `get_date_time`: VM cluster network #`expr $i + 1`"
        echo "oci db vm-cluster create --from-json file://${VMC_FILES[$i]}"
        # takes approximately 5h for a 2 node VM cluster
        vmc_id=`oci db vm-cluster create --from-json file://${VMC_FILES[$i]}  | jq -r '.data.id'`
        # Output is similar to following (JSON)
        # {
        # ...
        #     "id": "ocid1.vmclusternetwork.oc1.uk-london-1.anwgiljrnmvrbeaakyuxdvmb6skjztraew7mvhcgb2klaqp7gdg6xpihxmwq",
        # ...
        # }
        echo "VM cluster ${vmc_id} creation in progress !"
        echo
        sleep 30
        VMC_IDS+=($vmc_id)
        i=`expr $i + 1`
    done

    # Then wait for all of them to be ready
    echo "Now, waiting for the VM clusters to be ready (status AVAILABLE)!"
    echo
    new_line_required=false
    nb_completed=0
    while [ $nb_completed -lt $NB_NEW_VM_CLUSTERS ]; do
        new_line_required=true
        printf "."
        sleep 60
        i=0
        while [ $i -lt $nbm1 ]; do
            status=`get_vm-cluster_status ${VMC_IDS[$i]}`
            if [ "$status" == "AVAILABLE" ]; then
                if [ "$new_line_required" == true ]; then echo; fi
                echo "`get_date_time`: VM cluster ${VMC_IDS[$i]} is AVAILABLE !"
                new_line_required=false
                nb_completed=`expr $nb_completed + 1`
            fi
            i=`expr $i + 1`
        done 
    done
    echo
    echo "`get_date_time`: All VM clusters are AVAILABLE !"
}

# -------- Main

# -- parse arguments
if [ $# -ne 2 ]; then usage; fi

CONFIG_FILE=$1
if [ ! -f $CONFIG_FILE ]; then 
    echo "ERROR: file ${CONFIG_FILE} does not exist or is not readable !"
    exit 1
fi

STEP=$2

# -- Copy stdout and stderr to Log file
LOG_FILE="`basename $0 | sed 's/.sh$//g'`_`get_date_time`.log"

exec > >(tee -i $LOG_FILE)
exec 2>&1

echo "Log file: $LOG_FILE"
echo

# -- import variables from config file
. ${CONFIG_FILE}
check_config_file ${CONFIG_FILE}
export OCI_CLI_PROFILE

# --
case "$STEP" in
"1")    step1_delete_vm_cluster
        ;;
"2")    step2_create_and_validate_vm_cluster_networks
        ;;
"3")    step3_create_vm_clusters
        ;;
"all")  step1_delete_vm_cluster
        step2_create_and_validate_vm_cluster_networks
        step3_create_vm_clusters
        ;;
*)    usage
        ;;
esac

exit 0
