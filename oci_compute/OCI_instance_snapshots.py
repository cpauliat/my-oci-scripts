#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script implements snapshot-like feature for Oracle Cloud Infrastructure(OCI) compute instances using OCI Python SDK
#
# The user can execute the following operations:
# --list-all     : list existing snapshots for all compute instances
# --list         : list existing snapshots for a compute instance 
# --create       : take a new snapshot for a compute instance (cloned the boot volume and the block volumes and tag the instance and cloned volumes)
# --create-multi : take a new snapshot for several compute instances (cloned the boot volumes and the block volumes and tag the instances and cloned volumes)
# --delete       : delete a snapshot for a compute instance (delete cloned volumes and remove tag from the instance)
# --delete-all   : delete all snapshots for a compute instance (delete cloned volumes and remove tag from the instance)
# --rollback     : rollback to a snapshot for a compute instance (delete the instance, and recreate a new one with same parameters using cloned volumes)
#                  (new compute instance will have same private IP and same public IP if a reserved public IP was used)
# --rename       : rename a snapshot for a compute instance (rename cloned volumes and update tags for instance and cloned volumes)
# --change-desc  : change the description of a snapshot for a compute instance
#
# IMPORTANT: This script has the following limitations:
# - For rollback: new compute instance will have a single VNIC with a single IP address (multi-VNICs and multi-IP not supported)
# - For rollback: very specific parameters of the original instance may not be present in the new instance after rollback
# - Compute instances with ephemeral public IP adress are not supported (use private IP only or private IP + reserved public IP)
#
# NOTES: 
# - The snapshots information is stored in several JSON files (1 per compute instance) locally or in a OCI bucket (preferred solution)
# - Those JSON files are updated by all operations (except listing snapshots)
# - OCI tenant and region given by an OCI CLI PROFILE            
# - The number of block volumes attached to the compute instance can be different in different snapshots
# - The block volumes can be resized between snapshots
# - When creating a snapshot for several compute instances, all instances must be in the same compartment and the same availability domain
#
# AUTHOR        : Christophe Pauliat
# PLATFORMS     : MacOS / Linux
#
# PREREQUISITES : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
#                 - OCI user with enough privileges 
# VERSIONS:
#    2022-02-18: Initial Version
#    2022-02-18: Add retry strategies
#    2022-02-24: Store snapshots information in local JSON files in snapshots_db folder instead of tags only (quicker and more robust)
#    2022-02-25: Option to store snaphosts information in JSON files in an OCI bucket (preferred storage)
#    2022-02-25: Add required description field when creating a snapshot
#    2022-02-25: Add support for variable number of block volumes attached to compute instance
#    2022-03-01: Add --rename, --change_desc and --list-all operations
#    2022-03-01: Simplify arguments parsing using nargs and metavar in argparse
#    2022-03-02: Add locks to avoid simultaneous operations on the same compute instance
#    2022-03-02: Remove option to store snapshots information in local JSON files (mandatory usage of OCI bucket)
#    2022-03-03: Add --create-multi operation to create a consistent snapshot for several compute instances
#    2022-03-03: Add --delete-all operation to delete all snapshots for a compute instance
#    2022-06-22: Add check_snapshot_name_syntax() to check syntax of snapshot names (avoid errors when adding tag key)
#    2022-06-22: Use stderr for error messages
#    2022-06-22: Modify error codes
# ---------------------------------------------------------------------------------------------------------------------------------

# -------- import
from ast import Delete
import oci
import sys
import os
import argparse
import re
import json
from datetime import datetime
from time import sleep

# -------- variables
db_bucket  = "compute_snapshots"    # OCI bucket (standard mode) to store snapshots information (must be manually created before using the script)
configfile = "~/.oci/config"        # OCI config file to be used (usually, no need to change this)

# -------- functions

# ---- Lock one or more compute instances (stop if lock already present)
def lock(instance_ids):
    # look for lock file(s) in the OCI bucket
    try:
        response = ObjectStorageClient.list_objects(os_namespace, db_bucket, prefix="lock", retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except:
        pass

    # if at least one lock file is present, stop
    lock_present = False
    for object in response.data.objects:
        for instance_id in instance_ids:
            if object.name == f"lock.{instance_id}":
                lock_present = True
                break
    if lock_present:
        print ("ERROR 14: another operation is in progress on one of the compute instances (lock present) ! Please retry later.", file=sys.stderr)
        exit(14)

    # create lock files in the OCI bucket
    locked_instance_ids = []
    for instance_id in instance_ids:
        object_name  = f"lock.{instance_id}"
        print (f"Locking compute instance ...{instance_id[-6:]} to avoid simultaneous snapshot operations on it")
        try:
            response = ObjectStorageClient.put_object(os_namespace, db_bucket, object_name, "locked", retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            locked_instance_ids.append(instance_id)
        except Exception as error:
            print (f"ERROR 15: cannot lock compute instance ...{instance_id[-6:]}: {error}", file=sys.stderr)
            unlock(locked_instance_ids)
            exit(15)

# ---- Unlock 1 or more compute instances 
def unlock(instance_ids):
    for instance_id in instance_ids:
        object_name = f"lock.{instance_id}"
        print (f"Unlocking compute instance ...{instance_id[-6:]}")
        try:
            response = ObjectStorageClient.delete_object(os_namespace, db_bucket, object_name, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        except Exception as error:
            pass

# ---- Get the full name of a compartment from its id
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

# ---- Check that the OCI bucket exists
def stop_if_bucket_does_not_exist():
    try:
        ObjectStorageClient.get_bucket(os_namespace, db_bucket, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print (f"ERROR 05: Bucket does not exist: {error.message}", file=sys.stderr)
        exit(5)

# ---- Get the primary VNIC of the compute instance
def get_primary_vnic(cpt_id, instance_id):
    response        = ComputeClient.list_vnic_attachments(cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    primary_vnic_id = response.data[0].vnic_id
    reponse         = VirtualNetworkClient.get_vnic(primary_vnic_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    primary_vnic    = reponse.data
    return primary_vnic

# ---- get the OCID of primary private IP in VNIC
def get_private_ip_id(vnic_id):
    response = VirtualNetworkClient.list_private_ips(vnic_id=vnic_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    return response.data[0].id
    
# ---- Stop if ephemeral public IP attched to compute instance
def stop_if_ephemeral_public_ip(public_ip_address, instance_ids):
    if public_ip_address == None:
        return
    response = VirtualNetworkClient.get_public_ip_by_ip_address(
        oci.core.models.GetPublicIpByIpAddressDetails(ip_address=public_ip_address),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    if response.data.lifetime == "EPHEMERAL":
        print ("ERROR 06: this script does not support compute instances with ephemeral public IP. Use reserved public IP instead !", file=sys.stderr)
        unlock(instance_ids)
        exit(6)
    return response.data.id

# ---- Wait for a specific status on a compute instance
def wait_for_instance_status(instance_id, expected_status):
    print (f"Waiting for instance to get status {expected_status}")
    current_status = None
    while current_status != expected_status:
        sleep(5)
        response = ComputeClient.get_instance(instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        current_status = response.data.lifecycle_state

# ---- Get compute instance details and exits if instance does not exist (unless stop==False)
def get_instance_details(instance_id, stop=True):
    try:
        response = ComputeClient.get_instance(instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except:
        if stop:
            print ("ERROR 09: compute instance not found !", file=sys.stderr)
            unlock([ instance_id ])
            exit(9)
        else:
            return None

    if response.data.lifecycle_state in ["TERMINATED", "TERMINATING"]:
        if stop:
            print (f"ERROR 08: compute instance in status {response.data.lifecycle_state} !", file=sys.stderr)
            unlock([ instance_id ])
            exit(8)    
        else:
            return None

    return response.data

# ---- Get the OCID of the source boot volume for a cloned boot volume
def get_source_bootvol_id(cloned_bootvol_id, instance_ids):
    try:
        response = BlockstorageClient.get_boot_volume(cloned_bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        source_bootvol_id = response.data.source_details.id
    except:
        print (f"ERROR 10: cannot find the source boot volume from cloned boot volume {cloned_bootvol_id} !", file=sys.stderr)
        unlock(instance_ids)
        exit(10)

    return source_bootvol_id

# ---- Get the OCID of the source block volume for a cloned block volume
def get_source_blkvol_id(cloned_blkvol_id, instance_ids):
    try:
        response = BlockstorageClient.get_volume(cloned_blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        source_blkvol_id = response.data.source_details.id
    except:
        print (f"ERROR 11: cannot find the source volume from cloned volume {cloned_blkvol_id} !", file=sys.stderr)
        unlock(instance_ids)
        exit(11)

    return source_blkvol_id

# ---- Rename a boot volume
def rename_boot_volume(bootvol_id, bootvol_name):
    response = BlockstorageClient.update_boot_volume(
        bootvol_id, 
        oci.core.models.UpdateBootVolumeDetails(display_name = bootvol_name),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Rename a block volume
def rename_block_volume(blkvol_id, blkvol_name):
    response = BlockstorageClient.update_volume(
        blkvol_id, 
        oci.core.models.UpdateVolumeDetails(display_name = blkvol_name),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Delete a block volume
def delete_block_volume(blkvol_id):
    response = BlockstorageClient.delete_volume(blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)

# ---- Get the name of a boot volume for its id
def get_boot_volume_name_from_id(bootvol_id):
    response = BlockstorageClient.get_boot_volume(bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    name     = response.data.display_name
    return name

# ---- Get the name of a block volume for its id
def get_volume_name_from_id(blkvol_id):
    response = BlockstorageClient.get_volume(blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    name     = response.data.display_name
    return name

# ---- Remove a snapshot tag from a boot volume
def remove_boot_volume_tag(bootvol_id, snapshot_name):
    response = BlockstorageClient.get_boot_volume(bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    ff_tags  = response.data.freeform_tags
    tag_key  = f"snapshot_{snapshot_name}"
    del ff_tags[tag_key]
    response = BlockstorageClient.update_boot_volume(
        bootvol_id, 
        oci.core.models.UpdateBootVolumeDetails(freeform_tags=ff_tags),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Remove a snapshot tag from a block volume
def remove_block_volume_tag(blkvol_id, snapshot_name):
    response = BlockstorageClient.get_volume(blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    ff_tags  = response.data.freeform_tags
    tag_key  = f"snapshot_{snapshot_name}"
    del ff_tags[tag_key]
    response = BlockstorageClient.update_volume(
        blkvol_id, 
        oci.core.models.UpdateBootVolumeDetails(freeform_tags=ff_tags),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Rename and tag boot volume
def rename_and_tag_boot_volume(bootvol_id, snapshot_name, tag_key, tag_value, keyword="cloned"):
    response          = BlockstorageClient.get_boot_volume(bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    vol_name_prefix   = re.search(f'^(.+?)_{keyword}.*$',response.data.display_name).group(1)
    vol_new_name      = f"{vol_name_prefix}_snapshot_{snapshot_name}"
    ff_tags           = response.data.freeform_tags
    ff_tags[tag_key]  = tag_value

    if keyword == "cloned":
        print (f"Adding a free-form tag for this snapshot to the cloned boot volume ...{bootvol_id[-6:]}")
    response = BlockstorageClient.update_boot_volume(
        bootvol_id, 
        oci.core.models.UpdateBootVolumeDetails(display_name=vol_new_name, freeform_tags=ff_tags),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Rename and tag block volume
def rename_and_tag_block_volume(blkvol_id, snapshot_name, tag_key, tag_value, keyword="cloned"):
    response          = BlockstorageClient.get_volume(blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    vol_name_prefix   = re.search(f'^(.+?)_{keyword}.*$',response.data.display_name).group(1)
    vol_new_name      = f"{vol_name_prefix}_snapshot_{snapshot_name}"
    ff_tags           = response.data.freeform_tags
    ff_tags[tag_key]  = tag_value

    if keyword == "cloned":
        print (f"Adding a free-form tag for this snapshot to the cloned block volume ...{blkvol_id[-6:]}")
    response = BlockstorageClient.update_volume(
        blkvol_id, 
        oci.core.models.UpdateBootVolumeDetails(display_name=vol_new_name, freeform_tags=ff_tags),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Attach block volume to new compute instance
def attach_block_volume_to_instance(blkvol, new_instance_id):
    response = ComputeClient.attach_volume(oci.core.models.AttachVolumeDetails(
        device       = blkvol["device"],
        display_name = blkvol["display_name"],
        is_read_only = blkvol["is_read_only"],
        is_shareable = blkvol["is_shareable"],
        type         = blkvol["attachment_type"],
        volume_id    = blkvol["cloned_id"],
        instance_id  = new_instance_id),
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- load the dictionary containing snapshots details for this compute instance id 
# ---- from the corresponding json file stored in local folder or in oci bucket
def load_snapshots_dict(instance_id, verbose = True):
    empty_dict = { "instance_id": instance_id, "snapshots": [] }
    try:
        object_name = f"{instance_id}.json"
        response    = ObjectStorageClient.get_object(os_namespace, db_bucket, object_name, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        snapshots_dict = json.loads(response.data.text)
        if verbose:
            print (f"Loading snapshots information for compute instance ...{instance_id[-6:]} from object '{object_name}' in OCI bucket '{db_bucket}'")
        return snapshots_dict
    except:
        return empty_dict     

# ---- save the dictionary containing snapshots details for this compute instance id 
# ---- to the corresponding json file stored in local folder or in oci bucket
def save_snapshots_dict(dict, instance_id, verbose = True):
    object_name = f"{instance_id}.json"
    if len(dict["snapshots"]) > 0:
        if verbose:
            print (f"Saving snapshots information for compute instance ...{instance_id[-6:]} to object '{object_name}' in OCI bucket '{db_bucket}'")
        try:
            response = ObjectStorageClient.put_object(os_namespace, db_bucket, object_name, json.dumps(dict, indent=4), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        except Exception as error:
            print (f"ERROR 07: {error}", file=sys.stderr)
            unlock([ instance_id ])
            exit(7)
    else:
        try:
            print (f"No more snapshot for compute instance ...{instance_id[-6:]}: deleting object '{object_name}' in OCI bucket '{db_bucket}'")
            response = ObjectStorageClient.delete_object(os_namespace, db_bucket, object_name, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        except Exception as error:
            pass            

# -- Remove JSON file in local folder or OCI bucket for deleted compute instance
def delete_snapshots_dict(instance_id):
    old_object_name = f"{instance_id}.json"
    try:
        response = ObjectStorageClient.delete_object(os_namespace, db_bucket, old_object_name, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

# ---- Stop if the snapshot does not exist
def stop_if_snapsnot_does_not_exist(snap_dict, snapshot_name):
    for snap in snap_dict["snapshots"]:
        if snap["name"] == snapshot_name:
            return snap

    # if snapshot_name not found in snapshots list
    print (f"ERROR 03: there is no snapshot named '{snapshot_name}' for this compute instance !", file=sys.stderr)
    unlock([ instance_id ])
    exit(3)

# ---- Get a list of compute instances OCIDs contained in a text file (1 OCID per line)
def get_instance_ids_from_file(filename):
    # read content of file and exit if file does not exist
    try:
        with open(filename) as f:
            lines = f.readlines()
    except Exception as error:
        print (f"ERROR 12: Cannot read file {filename}: {error}", file=sys.stderr)
        exit(12)
    # get the list of compute instances OCIDs present in the files
    instance_ids = []
    for line in lines:
        if line.startswith("ocid1.instance"):
            instance_ids.append(line.rstrip("\n"))
    # 
    if len(instance_ids) < 2:
        print (f"ERROR 13: the file {filename} must contain at least 2 compute instance ocids !", file=sys.stderr)
        exit(13)

    return instance_ids

# ---- Check the syntax of the snapshot name (between 5 and 30 characters, accepted characters are [A-Za-z0-9_-])
def check_snapshot_name_syntax(snapshot_name):
    allowedCharacters = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-"
    validCharacters = all(char in allowedCharacters for char in snapshot_name)
    validSize = (len(snapshot_name) >= 5 and len(snapshot_name) <= 30)
    if not(validCharacters and validSize):
        print (f"ERROR 04: the snapshot name '{snapshot_name}' is invalid: between 5 and 30 characters, accepted characters are [A-Za-z0-9_-] !", file=sys.stderr)
        exit(4)

# ==== List snapshots of all compute instances
def list_snapshots_for_all_instances():
    # get the list of objects ocid*.json in the OCI bucket
    response = ObjectStorageClient.list_objects(os_namespace, db_bucket, prefix="ocid1.instance",
                                                retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    for object in response.data.objects:
        instance_id = object.name[:-5]

        # -- get compute instance details if it exists
        instance = get_instance_details(instance_id, stop=False)
        # if compute instance does not exist or is in TERMINATING/TERMINATED status, delete JSON file
        if instance == None:
            try:
                print ("")
                print (f"Deleting object '{object.name}' in OCI bucket '{db_bucket}' as this instance does not exist any more !")
                response = ObjectStorageClient.delete_object(os_namespace, db_bucket, object.name, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            except Exception as error:
                pass      
            continue

        # load the dictionary containing snapshots details for this compute instance
        snap_dict = load_snapshots_dict(instance_id, False)

        # display the snapshots list for this compute instance 
        if len(snap_dict["snapshots"]) > 0:
            print ("")
            inst_name = instance.display_name
            inst_cpt  = get_cpt_full_name_from_id(instance.compartment_id)
            print (f"Compute instance '{inst_name}' in compartment '{inst_cpt}' ({instance_id}):")
            for snap in snap_dict["snapshots"]:
                nb_blkvols = len(snap['block_volumes'])
                if nb_blkvols > 1:
                    str_blkvols = "block volumes"
                else:
                    str_blkvols = "block volume"
                print (f"- Snapshot '{snap['name']}' created {snap['date_time']}, contains {nb_blkvols} {str_blkvols}, description = '{snap['description']}'")

# ==== List snapshots of a compute instance
# - get the list of snapshots from compute instance tags
# - display them sorted by most recent dates stored in tag value
def list_snapshots(instance_id):

    # -- stop if instance does not exist
    instance = get_instance_details(instance_id)

    # -- load the dictionary containing snapshots details for this compute instance
    snap_dict = load_snapshots_dict(instance_id, False)

    # -- 
    if len(snap_dict["snapshots"]) > 0:
        for snap in snap_dict["snapshots"]:
            print (f"- Snapshot '{snap['name']}' created {snap['date_time']}, contains {len(snap['block_volumes'])} block volume(s), description = '{snap['description']}'")
    else:
        print ("No snapshot found for this compute instance !")

# ==== Create a snapshot of 1 or more compute instances
# For each instance:
# - create a cloned of the boot volume
# - create a cloned of each attached block volume
# - add a free-form tag to the compute instance and the cloned volumes
# - tag key   = snapshot_<snapshot_name>
# - tag value = date in YYYY/MM/DD_HH:DD format
def create_snapshot_multi(instance_ids, snapshot_name, description):

    # -- load the dictionaries containing snapshots details for those compute instances
    snaps_dict = {}
    for instance_id in instance_ids:
        snaps_dict[instance_id] = load_snapshots_dict(instance_id)

    # -- get the instances details and stop if one of the compute instances does not exist
    instances_dict = {}
    for instance_id in instance_ids:
        print (f"Getting details of compute instance ...{instance_id[-6:]}")
        instance = get_instance_details(instance_id, stop=False)
        if instance == None:
            unlock(instance_ids)
            print (f"ERROR 17: compute instance ...{instance_id[-6:]} does not exist or is in TERMINATING/TERMINATED status.", file=sys.stderr)
            exit(17)
        instances_dict[instance_id] = instance

    # -- make sure the compute instances belong to the same compartment and are in the same availability domain
    first_instance_id = instance_ids[0]
    ad_name = instances_dict[first_instance_id].availability_domain
    cpt_id  = instances_dict[first_instance_id].compartment_id
    for instance_id in instance_ids:
        if instances_dict[instance_id].availability_domain != ad_name:
            print ("ERROR 18: all compute instances must be in the same availability domain !", file=sys.stderr)
            unlock(instance_ids)
            exit(18)
        if instances_dict[instance_id].compartment_id != cpt_id:
            print ("ERROR 19: all compute instances must be in the same compartment !", file=sys.stderr)
            unlock(instance_ids)
            exit(19) 

    # -- make sure the snapshot_name is not already used on thoses compute instances
    for instance_id in instance_ids:
        for snap in snaps_dict[instance_id]["snapshots"]:
            if snap["name"] == snapshot_name:
                print (f"ERROR 01: A snapshot with name '{snapshot_name}' already exists for instance ...{instance_id[-6:]}. Please retry using a different name !", file=sys.stderr)
                unlock(instance_ids)
                exit(1)

    # -- make sure the compute instances does not use an ephemeral public IP
    for instance_id in instance_ids:
        print (f"Getting details of primary VNIC for compute instance ...{instance_id[-6:]}")
        primary_vnic = get_primary_vnic(instances_dict[instance_id].compartment_id, instance_id)
        stop_if_ephemeral_public_ip(primary_vnic.public_ip, instance_ids)

    # -- get the OCID of boot volume for each instance
    bootvol_ids_dict = {}
    for instance_id in instance_ids:
        response   = ComputeClient.list_boot_volume_attachments(ad_name, cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        bootvol_id = response.data[0].boot_volume_id
        bootvol_ids_dict[instance_id] = bootvol_id
    nb_bootvols = len(instance_ids)

    # -- get the block volume(s) attachment(s) (ignore non ATTACHED volumes) for each compute instance
    nb_blkvols = 0
    blkvol_attachments_dict = {}
    for instance_id in instance_ids:
        response           = ComputeClient.list_volume_attachments(cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        blkvol_attachments = []
        for blkvol_attachment in response.data:
            if blkvol_attachment.lifecycle_state == "ATTACHED":
                blkvol_attachments.append(blkvol_attachment)
                nb_blkvols += 1
        blkvol_attachments_dict[instance_id] = blkvol_attachments

    # -- create a temporary volume group containing all boot volumes and all block volume(s) for all compute instances
    if nb_bootvols > 1:
        string_bootvols = "boot volumes"
    else:
        string_bootvols = "boot volume"
    if nb_blkvols > 1:
        string_blkvols = "block volumes"
    else:
        string_blkvols = "block volume"
    print (f"Creating a temporary volume group (containing {nb_bootvols} {string_bootvols} and {nb_blkvols} {string_blkvols} for data consistency)")
    volume_ids = []
    for instance_id in instance_ids:
        volume_ids.append(bootvol_ids_dict[instance_id])
        for blkvol_attachment in blkvol_attachments_dict[instance_id]:
            volume_ids.append(blkvol_attachment.volume_id)
    source_details = oci.core.models.VolumeGroupSourceFromVolumesDetails(type="volumeIds", volume_ids=volume_ids)
    vg_details     = oci.core.models.CreateVolumeGroupDetails(
        availability_domain = ad_name, 
        compartment_id      = cpt_id, 
        display_name        = f"snapshot_{snapshot_name}_tempo_source",
        source_details      = source_details)
    # the creation of VG will fail if volumes are over limits (max 32 volumes and max 128 TB in March 2022)
    try:
        response = BlockstorageClient.create_volume_group(vg_details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        vg_id    = response.data.id
    except Exception as error:
        print (f"ERROR 16: creation of volume group failed: {error.message}", file=sys.stderr)
        unlock(instance_ids)
        exit(16)

    # -- clone the volume group to make a consistent copy of boot volume and block volume(s)
    print (f"Cloning the temporary volume group")
    c_source_details = oci.core.models.VolumeGroupSourceFromVolumeGroupDetails(volume_group_id = vg_id)
    cvg_details      = oci.core.models.CreateVolumeGroupDetails(
        availability_domain = ad_name, 
        compartment_id      = cpt_id, 
        display_name        = f"snapshot_{snapshot_name}_tempo_cloned",
        source_details      = c_source_details)
    cloning = False
    while not cloning:
        try:
            response = BlockstorageClient.create_volume_group(cvg_details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            cloning  = True
        except:
            print ("Cloning operation not yet possible (another cloning operation in progress). Will retry in 5 seconds...")
            sleep(5)
            cloning = False
    cvg_id            = response.data.id
    cloned_volume_ids = response.data.volume_ids

    # -- wait for the cloned process to be completed (cannot add tags or delete VG before completion)
    print ("Cloning successfully submitted and done in background: you can continue working on the compute instance(s).")
    print ("Waiting for cloning operation to complete... ")
    vg_status = response.data.lifecycle_state
    while vg_status == "PROVISIONING":
        sleep(5)
        response  = BlockstorageClient.get_volume_group(cvg_id,  retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        vg_status = response.data.lifecycle_state
    print ("Cloning operation completed !")

    # -- rename cloned volumes and add tags to them
    tag_key   = f"snapshot_{snapshot_name}"
    tag_value = datetime.utcnow().strftime("%Y/%m/%d_%T")
    cloned_boot_volume_ids_dict  = {}
    cloned_block_volume_ids_dict = {}
    for instance_id in instance_ids:
        cloned_block_volume_ids_dict[instance_id] = {}
    for cloned_volume_id in cloned_volume_ids:
        if "ocid1.bootvolume" in cloned_volume_id:
            try:
                rename_and_tag_boot_volume(cloned_volume_id, snapshot_name, tag_key, tag_value)
                source_bootvol_id  = get_source_bootvol_id(cloned_volume_id, instance_ids)
                # find the compute instance id for this source boot volume
                for instance_id in instance_ids:
                    if bootvol_ids_dict[instance_id] == source_bootvol_id:
                        break
                cloned_boot_volume_ids_dict[instance_id] = cloned_volume_id
            except Exception as error:
                print ("WARNING: ",error)
        else:
            try:
                rename_and_tag_block_volume(cloned_volume_id, snapshot_name, tag_key, tag_value)
                source_blkvol_id = get_source_blkvol_id(cloned_volume_id, instance_ids)
                # find the compute instance for this source block volume
                exit_nested_loops = False
                for instance_id in instance_ids:
                    for blkvol_attachment in blkvol_attachments_dict[instance_id]:
                        if blkvol_attachment.volume_id == source_blkvol_id:
                            exit_nested_loops = True
                            break
                    if exit_nested_loops:
                        break
                cloned_block_volume_ids_dict[instance_id][source_blkvol_id] = cloned_volume_id
            except Exception as error:
                print ("WARNING: ",error)

    # -- delete the 2 volume groups, keeping only the cloned volumes
    print ("Deleting the 2 temporary volumes groups")
    try:
        response = BlockstorageClient.delete_volume_group(volume_group_id=vg_id,  retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        response = BlockstorageClient.delete_volume_group(volume_group_id=cvg_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

    # -- add tag to compute instance(s)
    for instance_id in instance_ids:
        print (f"Adding a free-form tag for this snapshot to the compute instance ...{instance_id[-6:]}")
        ff_tags_inst = instances_dict[instance_id].freeform_tags
        ff_tags_inst[tag_key] = tag_value
        try:
            response = ComputeClient.update_instance(instance_id, oci.core.models.UpdateInstanceDetails(freeform_tags=ff_tags_inst), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        except Exception as error:
            print ("WARNING: ",error)

    # -- Update snapshots database
    for instance_id in instance_ids:
        bootvol_id              = bootvol_ids_dict[instance_id]
        cloned_boot_volume_id   = cloned_boot_volume_ids_dict[instance_id]
        cloned_block_volume_ids = cloned_block_volume_ids_dict[instance_id]
        blkvol_attachments      = blkvol_attachments_dict[instance_id]
        snap_dict               = snaps_dict[instance_id]
        # boot volume
        bootvol_name = get_boot_volume_name_from_id(bootvol_id)
        bootvol_dict = { "name": bootvol_name, "cloned_id": cloned_boot_volume_id }
        # block volume
        blkvols_list = []
        for blkvol_attachment in blkvol_attachments:
            blkvol_dict = {} 
            blkvol_dict["name"]            = get_volume_name_from_id(blkvol_attachment.volume_id) 
            blkvol_dict["cloned_id"]       = cloned_block_volume_ids[blkvol_attachment.volume_id]
            blkvol_dict["device"]          = blkvol_attachment.device
            blkvol_dict["attachment_type"] = blkvol_attachment.attachment_type
            blkvol_dict["display_name"]    = blkvol_attachment.display_name
            blkvol_dict["is_read_only"]    = blkvol_attachment.is_read_only
            blkvol_dict["is_shareable"]    = blkvol_attachment.is_shareable
            blkvols_list.append(blkvol_dict)
        # save all
        new_snap = {}
        new_snap["name"]          = snapshot_name
        new_snap["description"]   = description
        new_snap["date_time"]     = tag_value
        new_snap["boot_volume"]   = bootvol_dict
        new_snap["block_volumes"] = blkvols_list 
        snap_dict["snapshots"].append(new_snap)
        save_snapshots_dict(snap_dict, instance_id)

# ---- Create snapshot for a single compute instance
def create_snapshot(instance_id, snapshot_name, description):
    create_snapshot_multi([ instance_id ], snapshot_name, description)

# ==== Rollback a compute instance to a snapshot
def rollback_snapshot(instance_id, snapshot_name):

    # -- get the compute instance details and stop if instance does not exist
    print (f"Getting details of compute instance ...{instance_id[-6:]}")
    instance = get_instance_details(instance_id)
    ff_tags  = instance.freeform_tags

    # -- load the dictionary containing snapshots details for this compute instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- check that the snapshot exists
    snap = stop_if_snapsnot_does_not_exist(snap_dict, snapshot_name)

    # -- get the details for primary VNIC
    print (f"Getting details of primary VNIC")
    primary_vnic = get_primary_vnic(instance.compartment_id, instance_id)

    # -- make sure the compute instance does not use an ephemeral public IP
    public_ip_id = stop_if_ephemeral_public_ip(primary_vnic.public_ip, [instance_id])

    # --
    print (f"Getting details of boot volume and block volume(s)")

    # -- get the current block volume attachments details
    response = ComputeClient.list_volume_attachments(
        compartment_id = instance.compartment_id,
        instance_id    = instance_id,
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    blkvol_attachments = response.data

    # -- delete compute instance and boot volume
    print (f"Terminating current compute instance ...{instance_id[-6:]} and associated boot volume")
    response = ComputeClient.terminate_instance(instance_id, preserve_boot_volume=False, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    wait_for_instance_status(instance_id, "TERMINATED")

    # -- rename boot volume (use the name of the boot volume when snapshot was created)
    bootvol_name   = snap["boot_volume"]["name"]
    new_bootvol_id = snap["boot_volume"]["cloned_id"]
    print (f"Renaming cloned boot volume ...{new_bootvol_id[-6:]}")
    try:
        rename_boot_volume(new_bootvol_id, bootvol_name)
    except Exception as error:
        print ("WARNING: ",error)

    # -- remove the free-form tag for this snapshot in the new compute instance
    tag_key  = f"snapshot_{snapshot_name}"
    new_ff_tags = instance.freeform_tags
    try:
        del new_ff_tags[tag_key]
    except Exception as error:
        print ("WARNING: ",error)

    # -- create new compute instance using cloned boot volume
    print (f"Creating new compute instance using cloned boot volume ...{new_bootvol_id[-6:]}")
    details = oci.core.models.LaunchInstanceDetails(
        availability_domain = instance.availability_domain,
        compartment_id = instance.compartment_id,
        create_vnic_details = oci.core.models.CreateVnicDetails(
            assign_public_ip       = False,
            defined_tags           = primary_vnic.defined_tags,
            display_name           = primary_vnic.display_name,
            freeform_tags          = primary_vnic.freeform_tags,
            hostname_label         = primary_vnic.hostname_label,
            nsg_ids                = primary_vnic.nsg_ids,
            private_ip             = primary_vnic.private_ip,
            skip_source_dest_check = primary_vnic.skip_source_dest_check,
            subnet_id              = primary_vnic.subnet_id,
        ),
        defined_tags      = instance.defined_tags,
        display_name      = instance.display_name,
        extended_metadata = instance.extended_metadata,
        fault_domain      = instance.fault_domain,
        freeform_tags     = new_ff_tags,
        metadata          = instance.metadata,
        shape             = instance.shape,
        shape_config      = oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus           = instance.shape_config.ocpus,
            memory_in_gbs   = instance.shape_config.memory_in_gbs,
        ),
        source_details    = oci.core.models.InstanceSourceViaBootVolumeDetails(
            source_type     = "bootVolume", 
            boot_volume_id  = new_bootvol_id,
        ),
    )
    response = ComputeClient.launch_instance(details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    new_instance_id = response.data.id
    wait_for_instance_status(new_instance_id, "RUNNING")

    print (f"New compute instance ...{new_instance_id[-6:]} created !")

    # -- attach and rename cloned block volume(s) (use name of the block volumes when the snapshot was created)
    if len(snap["block_volumes"]) > 0:
        for blkvol in snap["block_volumes"]:
            new_blkvol_id    = blkvol["cloned_id"]
            print (f"Attaching cloned block volume ...{new_blkvol_id[-6:]} to new compute instance ...{new_instance_id[-6:]}")
            try:
                attach_block_volume_to_instance(blkvol, new_instance_id)
            except Exception as error:
                print ("WARNING: ",error)

            print (f"Renaming cloned block volume ...{new_blkvol_id[-6:]}")
            try:
                rename_block_volume(new_blkvol_id, blkvol["name"])
            except Exception as error:
                print ("WARNING: ",error)
                
    # -- delete the previously attached block volume(s)
    if len(blkvol_attachments) > 0:
        for blkvol_attachment in blkvol_attachments:
            print (f"Deleting original block volume ...{blkvol_attachment.volume_id[-6:]}")
            delete_block_volume(blkvol_attachment.volume_id)

    # -- remove free-form tags from boot volume
    print (f"Removing the free-form tag from the boot volume ...{new_bootvol_id[-6:]}")
    remove_boot_volume_tag(new_bootvol_id, snapshot_name)

    # -- remove free-form tags from block volume(s)
    for blkvol in snap["block_volumes"]:
        new_blkvol_id = blkvol["cloned_id"]            
        print (f"Removing the free-form tag from block volume ...{new_blkvol_id[-6:]}")
        remove_block_volume_tag(new_blkvol_id, snapshot_name)

    # -- assign reserved public IP address if it was present on original compute instance
    if primary_vnic.public_ip != None:
        print (f"Attaching reserved public IP address to new compute instance")
        new_primary_vnic  = get_primary_vnic(instance.compartment_id, new_instance_id)
        new_private_ip_id = get_private_ip_id(new_primary_vnic.id)
        VirtualNetworkClient.update_public_ip(
            public_ip_id             = public_ip_id, 
            update_public_ip_details = oci.core.models.UpdatePublicIpDetails(private_ip_id = new_private_ip_id),
            retry_strategy           = oci.retry.DEFAULT_RETRY_STRATEGY)

    # -- Update snapshots database
    snap2 = snap.copy()

    # delete the snapshot
    for i in range(len(snap_dict["snapshots"])):
        if snap_dict["snapshots"][i]['name'] == snapshot_name:
            del snap_dict["snapshots"][i]
            break

    # save
    save_snapshots_dict(snap_dict, new_instance_id)

    # remove JSON file in local folder or OCI bucket for deleted compute instance
    delete_snapshots_dict(instance_id)

    # -- new compute instance is ready
    print (f"The new compute instance is ready. OCID = {new_instance_id}")

# ==== Delete a snapshot of a compute instance
def delete_cloned_volumes(snap):
    # -- delete the cloned block volume(s)
    for blkvol in snap["block_volumes"]:
        cloned_blkvol_id = blkvol["cloned_id"]
        print (f"Deleting the cloned block volume ...{cloned_blkvol_id[-6:]}")
        try:
            response = BlockstorageClient.delete_volume(cloned_blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        except Exception as error:
            print ("WARNING: ",error)

    # -- delete the cloned boot volume
    cloned_bootvol_id = snap["boot_volume"]["cloned_id"]
    print (f"Deleting the cloned boot volume ...{cloned_bootvol_id[-6:]}")
    try:
        response = BlockstorageClient.delete_boot_volume(cloned_bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

def delete_snapshot(instance_id, snapshot_name):
    # -- load the dictionary containing snapshots details for this compute instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- get the compute instance details and stop if compute instance does not exist
    instance = get_instance_details(instance_id)
    ff_tags  = instance.freeform_tags

    # -- check that the snapshot exists
    snap = stop_if_snapsnot_does_not_exist(snap_dict, snapshot_name)

    # -- delete cloned boot volume and block volume(s)
    delete_cloned_volumes(snap)

    # -- remove the free-form tag from the compute instance
    print (f"Removing the free-form tag from the compute instance ...{instance_id[-6:]}")
    tag_key  = f"snapshot_{snapshot_name}"
    try:
        del ff_tags[tag_key]
        ComputeClient.update_instance(instance_id, oci.core.models.UpdateInstanceDetails(freeform_tags=ff_tags), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

    # -- Update snapshots database
    for i in range(len(snap_dict["snapshots"])):
        if snap_dict["snapshots"][i]['name'] == snapshot_name:
            del snap_dict["snapshots"][i]
            break
    save_snapshots_dict(snap_dict, instance_id)

# ==== Delete all snapshots of a compute instance
def delete_all_snapshots(instance_id):
    # -- load the dictionary containing snapshots details for this compute instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- get the compute instance details and stop if compute instance does not exist
    instance = get_instance_details(instance_id)
    ff_tags  = instance.freeform_tags

    # -- for each snapshot
    for snap in snap_dict["snapshots"]:
        snapshot_name = snap["name"]

        print ("")
        print (f"======== Deleting snapshot '{snapshot_name}'")

        # delete cloned boot volume and block volume(s)
        delete_cloned_volumes(snap)

        # remove the free-form tag in free-form tags
        print (f"Removing the free-form tag for snapshot '{snapshot_name}' from the compute instance ...{instance_id[-6:]}")
        tag_key  = f"snapshot_{snapshot_name}"
        try:
            del ff_tags[tag_key]
        except Exception as error:
            print ("WARNING: ",error)

    # -- update free-form tags for the compute instance
    print ("")
    try:
        ComputeClient.update_instance(instance_id, oci.core.models.UpdateInstanceDetails(freeform_tags=ff_tags), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

    # -- Remove snapshots database (JSON file) for this compute instance
    snap_dict["snapshots"] = []
    save_snapshots_dict(snap_dict, instance_id)

# ==== Rename a snapshot of a compute instance
def rename_snapshot(instance_id, snapshot_old_name, snapshot_new_name):
    # -- load the dictionary containing snapshots details for this compute instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- make sure the new snapshot_name is not already used on this compute instance
    for snap in snap_dict["snapshots"]:
        if snap["name"] == snapshot_new_name:
            print (f"ERROR 01: A snapshot with name '{snapshot_new_name}' already exists. Please retry using a different name !", file=sys.stderr)
            unlock([ instance_id ])
            exit(1)

    # -- check that the snapshot exists
    snap = stop_if_snapsnot_does_not_exist(snap_dict, snapshot_old_name)

    # -- get the compute instance details and stop if instance does not exist
    print (f"Getting details of compute instance ...{instance_id[-6:]}")
    instance = get_instance_details(instance_id)

    # -- update name for this snapshot
    print (f"Modifying snapshot name: old name = {snapshot_old_name}, new name = {snapshot_new_name}")
    snap["name"] = snapshot_new_name

    # -- updates free-form tags for compute instance
    print ("Updating the free form-tags for the compute instance")
    ff_tags_inst = instance.freeform_tags
    tag_old_key  = f"snapshot_{snapshot_old_name}"
    tag_new_key  = f"snapshot_{snapshot_new_name}"
    try:
        tag_value = ff_tags_inst[tag_old_key]
        del ff_tags_inst[tag_old_key]
        ff_tags_inst[tag_new_key] = tag_value
        response = ComputeClient.update_instance(instance_id, oci.core.models.UpdateInstanceDetails(freeform_tags=ff_tags_inst), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

    # -- rename and update free-form tags for cloned boot volume
    bootvol_id = snap["boot_volume"]["cloned_id"]
    print (f"Updating free-form tag on cloned boot volume ...{bootvol_id[-6:]}")
    remove_boot_volume_tag(bootvol_id, snapshot_old_name)
    print (f"Renaming cloned boot volume ...{bootvol_id[-6:]}")
    rename_and_tag_boot_volume(bootvol_id, snapshot_new_name, tag_new_key, tag_value, keyword="snapshot")

    # -- rename and update free-form tags for cloned block volume(s)
    for blkvol in snap["block_volumes"]:
        blkvol_id = blkvol["cloned_id"]
        print (f"Updating free-form tag on cloned block volume ...{blkvol_id[-6:]}")
        remove_block_volume_tag(blkvol_id, snapshot_old_name)
        print (f"Renaming cloned block volume ...{blkvol_id[-6:]}")
        rename_and_tag_block_volume(blkvol_id, snapshot_new_name, tag_new_key, tag_value, keyword="snapshot")

    # -- save snapshots database
    save_snapshots_dict(snap_dict, instance_id)

# ==== Change the description of a snapshot of a compute instance
def change_snapshot_decription(instance_id, snapshot_name, new_desc):
    # -- load the dictionary containing snapshots details for this compute instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- check that the snapshot exists
    snap = stop_if_snapsnot_does_not_exist(snap_dict, snapshot_name)

    # -- update description for this snapshot
    print (f"Modifying description for snapshot {snapshot_name}")
    snap["description"] = new_desc

    # -- save snapshots database
    save_snapshots_dict(snap_dict, instance_id)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Implement snapshot-like feature on OCI compute instances")
parser.add_argument("--profile",    help="OCI profile", required=True)

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--list-all",    help="List snapshots for all compute instances", action="store_true")
group.add_argument("--list",        help="List snapshots for the specified compute instance",                       nargs=1, metavar="<INSTANCE_OCID>")
group.add_argument("--create",      help="Create a snapshot for the specified compute instance",                    nargs=3, metavar=("<SNAPSHOT_NAME>","<SNAPSHOT_DESCRIPTION>","<INSTANCE_OCID>"))
group.add_argument("--create-multi",help="Create a snapshot for multiple compute instances (list of OCIDs in file, 1 OCID per line)",nargs=3, metavar=("<SNAPSHOT_NAME>","<SNAPSHOT_DESCRIPTION>","<FILE_CONTAINING_INSTANCE_OCIDS>"))
group.add_argument("--rollback",    help="Rollback to a snapshot for the specified compute instance",               nargs=2, metavar=("<SNAPSHOT_NAME>","<INSTANCE_OCID>"))
group.add_argument("--delete",      help="Delete a snapshot for the specified compute instance",                    nargs=2, metavar=("<SNAPSHOT_NAME>","<INSTANCE_OCID>"))
group.add_argument("--delete-all",  help="Delete all snapshots for the specified compute instance",                 nargs=1, metavar=("<INSTANCE_OCID>"))
group.add_argument("--rename",      help="Rename a snapshot for the specified compute instance",                    nargs=3, metavar=("<SNAPSHOT_OLD_NAME>","<SNAPSHOT_NEW_NAME>","<INSTANCE_OCID>"))
group.add_argument("--change-desc", help="Change the description of a snapshot for the specified compute instance", nargs=3, metavar=("<SNAPSHOT_NAME>","<SNAPSHOT_NEW_DESCRIPTION>","<INSTANCE_OCID>"))
args = parser.parse_args()

profile = args.profile

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print (f"ERROR 02: profile '{profile}' not found in config file {configfile} !", file=sys.stderr)
    exit(2)

# -- OCI clients
IdentityClient       = oci.identity.IdentityClient(config)
ComputeClient        = oci.core.ComputeClient(config)
BlockstorageClient   = oci.core.BlockstorageClient(config)
ObjectStorageClient  = oci.object_storage.ObjectStorageClient(config)
SearchClient         = oci.resource_search.ResourceSearchClient(config)
VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

# -- check that OCI bucket exists
response = ObjectStorageClient.get_namespace(retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
os_namespace = response.data
stop_if_bucket_does_not_exist()

# -- get list of compartments with all sub-compartments
user              = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id
response          = oci.pagination.list_call_get_all_results(IdentityClient.list_compartments,RootCompartmentID,compartment_id_in_subtree=True)
compartments      = response.data

# -- do the job
if args.list_all:
    list_snapshots_for_all_instances()
elif args.list:
    instance_id = args.list[0]
    list_snapshots(instance_id)
elif args.create:
    snapshot_name = args.create[0]
    snapshot_desc = args.create[1]
    instance_id   = args.create[2]
    check_snapshot_name_syntax(snapshot_name)
    lock([ instance_id ])
    create_snapshot(instance_id, snapshot_name, snapshot_desc)
    unlock([ instance_id ])
elif args.create_multi:
    snapshot_name = args.create_multi[0]
    snapshot_desc = args.create_multi[1]
    instances_file= args.create_multi[2]
    check_snapshot_name_syntax(snapshot_name)
    instance_ids = get_instance_ids_from_file(instances_file)
    lock(instance_ids)
    create_snapshot_multi(instance_ids, snapshot_name, snapshot_desc)
    unlock(instance_ids)
elif args.rollback:
    snapshot_name = args.rollback[0]
    instance_id   = args.rollback[1]
    check_snapshot_name_syntax(snapshot_name)
    lock([ instance_id ])
    rollback_snapshot(instance_id, snapshot_name)
    unlock([ instance_id ])
elif args.delete:
    snapshot_name = args.delete[0]
    instance_id   = args.delete[1]
    check_snapshot_name_syntax(snapshot_name)
    lock([ instance_id ])
    delete_snapshot(instance_id, snapshot_name)
    unlock([ instance_id ])
elif args.delete_all:
    instance_id   = args.delete_all[0]
    lock([ instance_id ])
    delete_all_snapshots(instance_id)
    unlock([ instance_id ])
elif args.rename:
    snapshot_old_name = args.rename[0]
    snapshot_new_name = args.rename[1]
    instance_id       = args.rename[2]
    check_snapshot_name_syntax(snapshot_old_name)
    check_snapshot_name_syntax(snapshot_new_name)
    lock([ instance_id ])
    rename_snapshot(instance_id, snapshot_old_name, snapshot_new_name)
    unlock([ instance_id ])
elif args.change_desc:
    snapshot_name     = args.change_desc[0]
    snapshot_new_desc = args.change_desc[1]
    instance_id       = args.change_desc[2]
    check_snapshot_name_syntax(snapshot_name)
    lock([ instance_id ])
    change_snapshot_decription(instance_id, snapshot_name, snapshot_new_desc)
    unlock([ instance_id ])

# -- the end
exit(0)
