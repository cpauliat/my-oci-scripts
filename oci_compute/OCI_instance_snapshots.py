#!/usr/bin/env python3

# ---------------------------------------------------------------------------------------------------------------------------------
# This script implements snapshot-like feature for OCI compute instance using OCI Python SDK
# It can:
# - list existing snapshots for an instance (names saved as tags in the instance)
# - take a new snapshot for a compute instance (cloned the boot volume and the block volumes and tag the cloneds volumes)
# - delete a snapshot (delete cloned volumes and remove tag from the instance)
# - rollback to a snapshot (delete the compute instance, and recreate a new one with same parameters using cloned volumes)
#            (new instance will have same private IP and same public IP if a reserved public IP was used)
#
# IMPORTANT: This script has the following limitations:
# - For rollback: new instance will have a single VNIC with a single IP address (multi-VNICs and multi-IP not supported)
# - For rollback: very specific parameters of the original instance may not be present in the new instance after rollback
# - Compute instances with ephemeral public IP adress are not supported (use private IP only or private IP + reserved public IP)
#
# Notes: 
# - OCI tenant and region given by an OCI CLI PROFILE
# - The number of block volumes attached to the instance can be different in different snapshots
# - The block volumes can be resized between snapshots
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
#                 - OCI user with enough privileges 
# Versions
#    2022-02-18: Initial Version
#    2022-02-18: Add retry strategies
#    2022-02-24: Store snapshots information in local JSON files in snapshots_db folder instead of tags only (quicker and more robust)
#    2022-02-25: Option to store snaphosts information in JSON files in an OCI bucket (preferred storage)
#    2022-02-25: Add required description field when creating a snapshot
#    2022-02-25: Add support for variable number of block volumes attached to instance
#
# TO DO:
# - add lock on instance json files to avoid 2 or more snapshots operations on the same instance at the same time
# - add support for multiple IP address per VNIC
# - add support for multiple VNICs per instance
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
db_mode    = "oci_bucket"           # "local_file" or "oci_bucket" ("oci_bucket" recommended)
db_folder  = "./.snapshots_db"      # Folder to be created locally to store snapshots information
db_bucket  = "compute_snapshots"    # OCI bucket (standard mode) to store snapshots information (must be manually created before using the script)
configfile = "~/.oci/config"        # OCI config file to be used (usually, no need to change this)

# -------- functions

# ---- Check that the OCI bucket exists
def stop_if_bucket_does_not_exist():
    try:
        ObjectStorageClient.get_bucket(os_namespace, db_bucket, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print (f"ERROR 11: {error}")
        exit(11)

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
def stop_if_ephemeral_public_ip(public_ip_address):
    if public_ip_address == None:
        return

    response = VirtualNetworkClient.get_public_ip_by_ip_address(
        oci.core.models.GetPublicIpByIpAddressDetails(ip_address=public_ip_address),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    if response.data.lifetime == "EPHEMERAL":
        print ("ERROR 06: this script does not support compute instances with ephemeral public IP. Use reserved public IP instead !")
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

# ---- Get instance details and exits if instance does not exist
def get_instance_details(instance_id):
    try:
        response = ComputeClient.get_instance(instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except:
        print ("ERROR 09: compute instance not found !")
        exit(9)

    if response.data.lifecycle_state in ["TERMINATED", "TERMINATING"]:
        print (f"ERROR 08: compute instance in status {response.data.lifecycle_state} !")
        exit(8)            
    return response.data

# ---- Get the OCID of the source block volume for a cloned block volume
def get_source_volume_id(cloned_blkvol_id):
    try:
        response = BlockstorageClient.get_volume(cloned_blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        source_blkvol_id = response.data.source_details.id
    except:
        print (f"ERROR 10: cannot find the source volume from cloned volume {cloned_blkvol_id} !")
        exit(10)

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
def rename_and_tag_boot_volume(bootvol_id, snapshot_name, tag_key, tag_value):
    response          = BlockstorageClient.get_boot_volume(bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    vol_name_prefix   = re.search('^(.+?)_cloned.*$',response.data.display_name).group(1)
    vol_new_name      = f"{vol_name_prefix}_snapshot_{snapshot_name}"
    ff_tags           = response.data.freeform_tags
    ff_tags[tag_key]  = tag_value

    print (f"Adding a freeform tag for this snapshot to the cloned boot volume ...{bootvol_id[-6:]}")
    response = BlockstorageClient.update_boot_volume(
        bootvol_id, 
        oci.core.models.UpdateBootVolumeDetails(display_name=vol_new_name, freeform_tags=ff_tags),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Rename and tag block volume
def rename_and_tag_block_volume(blkvol_id, snapshot_name, tag_key, tag_value):
    response          = BlockstorageClient.get_volume(blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    vol_name_prefix   = re.search('^(.+?)_cloned.*$',response.data.display_name).group(1)
    vol_new_name      = f"{vol_name_prefix}_snapshot_{snapshot_name}"
    ff_tags           = response.data.freeform_tags
    ff_tags[tag_key]  = tag_value

    print (f"Adding a freeform tag for this snapshot to the cloned block volume ...{blkvol_id[-6:]}")
    response = BlockstorageClient.update_volume(
        blkvol_id, 
        oci.core.models.UpdateBootVolumeDetails(display_name=vol_new_name, freeform_tags=ff_tags),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Attach block volume to new instance
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

# ---- load the dictionary containing snapshots details for this instance id 
# ---- from the corresponding json file stored in local folder or in oci bucket
def load_snapshots_dict(instance_id, verbose = True):
    empty_dict = { "instance_id": instance_id, "snapshots": [] }

    if db_mode == "local_file":
        json_file = f"{db_folder}/{instance_id}.json"
        if not os.path.exists(json_file):
            return empty_dict
        else:
            if verbose:
                print (f"Loading snapshots information for this instance from file {json_file}")
            try:
                with open(json_file, "r") as f:
                    data = f.read()
                snapshots_dict = json.loads(data)
            except Exception as error:
                print ("ERROR 04: ",error)                    
                exit(4)            
            return snapshots_dict

    elif db_mode == "oci_bucket":
        try:
            object_name = f"{instance_id}.json"
            response    = ObjectStorageClient.get_object(os_namespace, db_bucket, object_name, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            snapshots_dict = json.loads(response.data.text)
            if verbose:
                print (f"Loading snapshots information for this instance from object {object_name} in OCI bucket {db_bucket}")
            return snapshots_dict
        except:
            return empty_dict     

# ---- save the dictionary containing snapshots details for this instance id 
# ---- to the corresponding json file stored in local folder or in oci bucket
def save_snapshots_dict(dict, instance_id, verbose = True):
    if db_mode == "local_file":
        if verbose:
            print (f"Saving snapshots information for this instance to file {json_file}")
        json_file = f"{db_folder}/{instance_id}.json"
        if len(dict["snapshots"]) > 0:
            with open(json_file, "w") as f:
                try:
                    f.write(json.dumps(dict, indent=4))
                except Exception as error:
                    print ("ERROR 05: ",error)                    
                    exit(5)
        else:
            try:
                os.remove(json_file)
            except Exception as error:
                print ("WARNING: ",error)

    elif db_mode == "oci_bucket":
        object_name = f"{instance_id}.json"
        if len(dict["snapshots"]) > 0:
            if verbose:
                print (f"Saving snapshots information for this instance to object {object_name} in OCI bucket {db_bucket}")
            try:
                response = ObjectStorageClient.put_object(os_namespace, db_bucket, object_name, json.dumps(dict, indent=4), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            except Exception as error:
                print ("ERROR 07: ",error)
                exit(7)
        else:
            try:
                response = ObjectStorageClient.delete_object(os_namespace, db_bucket, object_name, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
            except Exception as error:
                pass            

# -- Remove JSON file in local folder or OCI bucket for deleted instance
def delete_snapshots_dict(instance_id):
    if db_mode == "local_file":
        old_json_file = f"{db_folder}/{instance_id}.json"
        try:
            os.remove(old_json_file)
        except Exception as error:
            print ("WARNING: ",error)

    elif db_mode == "oci_bucket":
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
    print (f"ERROR 03: there is no snapshot named {snapshot_name} for this compute instance !")
    exit(3)

# ==== List snapshots of a compute instance
# - get the list of snapshots from compute instance tags
# - display them sorted by most recent dates stored in tag value
def list_snapshots(instance_id):

    # -- stop if instance does not exist
    instance = get_instance_details(instance_id)

    # -- load the dictionary containing snapshots details for this instance
    snap_dict = load_snapshots_dict(instance_id, False)

    # -- 
    if len(snap_dict["snapshots"]) > 0:
        for snap in snap_dict["snapshots"]:
            print (f"- Snapshot '{snap['name']}' created {snap['date_time']}, contains {len(snap['block_volumes'])} block volume(s), description = '{snap['description']}'")
    else:
        print ("No snapshot found for this compute instance !")

# ==== Create a snapshot of a compute instance
# - create a cloned of the boot volume
# - create a cloned of each attached block volume
# - add a freeform tag to the compute instance and the cloned volumes
# - tag key   = snapshot_<snapshot_name>
# - tag value = date in YYYY/MM/DD_HH:DD format
def create_snapshot(instance_id, snapshot_name, description):

    # -- load the dictionary containing snapshots details for this instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- get the instance details and stop if instance does not exist
    print (f"Getting details of compute instance ...{instance_id[-6:]}")
    instance     = get_instance_details(instance_id)
    ad_name      = instance.availability_domain
    cpt_id       = instance.compartment_id
    ff_tags_inst = instance.freeform_tags

    # -- make sure the snapshot_name is not already used on this compute instance
    for snap in snap_dict["snapshots"]:
        if snap["name"] == snapshot_name:
            print (f"ERROR 01: A snapshot with name '{snapshot_name}' already exists. Please retry using a different name !")
            exit(1)

    # -- make sure the compute instance does not use an ephemeral public IP
    print (f"Getting details of primary VNIC")
    primary_vnic = get_primary_vnic(cpt_id, instance_id)
    stop_if_ephemeral_public_ip(primary_vnic.public_ip)

    # -- get the OCID of boot volume
    response   = ComputeClient.list_boot_volume_attachments(ad_name, cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    bootvol_id = response.data[0].boot_volume_id

    # -- get the block volume(s) attachment(s) (ignore non ATTACHED volumes)
    response           = ComputeClient.list_volume_attachments(cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    blkvol_attachments = []
    for blkvol_attachment in response.data:
        if blkvol_attachment.lifecycle_state == "ATTACHED":
            blkvol_attachments.append(blkvol_attachment)

    # -- create a temporary volume group containing boot volume and block volume(s)
    print (f"Creating a temporary volume group (containing 1 boot volume and {len(blkvol_attachments)} block volume(s)) for data consistency")
    volume_ids = [ bootvol_id ]
    for blkvol_attachment in blkvol_attachments:
        volume_ids.append(blkvol_attachment.volume_id)
    source_details = oci.core.models.VolumeGroupSourceFromVolumesDetails(type="volumeIds", volume_ids=volume_ids)
    vg_details     = oci.core.models.CreateVolumeGroupDetails(
        availability_domain = ad_name, 
        compartment_id      = cpt_id, 
        display_name        = f"snapshot_{snapshot_name}_tempo_source",
        source_details      = source_details)
    response = BlockstorageClient.create_volume_group(vg_details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    vg_id    = response.data.id

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
    print ("Cloning successfully submitted and done in background: you can continue working on the compute instance.")
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
    cloned_block_volume_ids = {}
    for cloned_volume_id in cloned_volume_ids:
        if "ocid1.bootvolume" in cloned_volume_id:
            try:
                rename_and_tag_boot_volume(cloned_volume_id, snapshot_name, tag_key, tag_value)
                cloned_boot_volume_id = cloned_volume_id
            except Exception as error:
                print ("WARNING: ",error)
        else:
            try:
                rename_and_tag_block_volume(cloned_volume_id, snapshot_name, tag_key, tag_value)
                source_volume_id = get_source_volume_id(cloned_volume_id)
                cloned_block_volume_ids[source_volume_id] = cloned_volume_id
            except Exception as error:
                print ("WARNING: ",error)

    # -- delete the 2 volume groups, keeping only the cloned volumes
    print ("Deleting the 2 temporary volumes groups")
    try:
        response = BlockstorageClient.delete_volume_group(volume_group_id=vg_id,  retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        response = BlockstorageClient.delete_volume_group(volume_group_id=cvg_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

    # -- add tag to compute instance
    print ("Adding a freeform tag for this snapshot to the compute instance")
    ff_tags_inst[tag_key] = tag_value
    try:
        response = ComputeClient.update_instance(instance_id, oci.core.models.UpdateInstanceDetails(freeform_tags=ff_tags_inst), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    except Exception as error:
        print ("WARNING: ",error)

    # -- Update snapshots database
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

# ==== Rollback a compute instance to a snapshot
def rollback_snapshot(instance_id, snapshot_name):

    # -- get the instance details and stop if instance does not exist
    print (f"Getting details of compute instance ...{instance_id[-6:]}")
    instance = get_instance_details(instance_id)
    ff_tags  = instance.freeform_tags

    # -- load the dictionary containing snapshots details for this instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- check that the snapshot exists
    snap = stop_if_snapsnot_does_not_exist(snap_dict, snapshot_name)

    # -- get the details for primary VNIC
    print (f"Getting details of primary VNIC")
    primary_vnic = get_primary_vnic(instance.compartment_id, instance_id)

    # -- make sure the compute instance does not use an ephemeral public IP
    public_ip_id = stop_if_ephemeral_public_ip(primary_vnic.public_ip)

    # --
    print (f"Getting details of boot volume and block volume(s)")

    # -- get the current block volume attachments details
    response = ComputeClient.list_volume_attachments(
        compartment_id = instance.compartment_id,
        instance_id    = instance_id,
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    blkvol_attachments = response.data

    # -- delete instance and boot volume
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

    # -- remove the freeform tag for this snapshot in the new compute instance
    tag_key  = f"snapshot_{snapshot_name}"
    new_ff_tags = instance.freeform_tags
    try:
        del new_ff_tags[tag_key]
    except Exception as error:
        print ("WARNING: ",error)

    # -- create new instance using cloned boot volume
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
            print (f"Attaching cloned block volume ...{new_blkvol_id[-6:]} to new instance ...{new_instance_id[-6:]}")
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

    # -- remove freeforms tags from boot volume
    print (f"Removing tag from boot volume ...{new_bootvol_id[-6:]}")
    remove_boot_volume_tag(new_bootvol_id, snapshot_name)

    # -- remove freeforms tags from block volume(s)
    #TODO if len(snap["block_volumes"]) > 0:
    for blkvol in snap["block_volumes"]:
        new_blkvol_id = blkvol["cloned_id"]            
        print (f"Removing tag from block volume ...{new_blkvol_id[-6:]}")
        remove_block_volume_tag(new_blkvol_id, snapshot_name)

    # -- assign reserved public IP address if it was present on original instance
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

    # remove JSON file in local folder or OCI bucket for deleted instance
    delete_snapshots_dict(instance_id)

    # -- new compute instance is ready
    print (f"The new compute instance is ready. OCID = {new_instance_id}")

# ==== Delete a snapshot of a compute instance
def delete_snapshot(instance_id, snapshot_name):

    # -- load the dictionary containing snapshots details for this instance
    snap_dict = load_snapshots_dict(instance_id)

    # -- get the instance details and stop if instance does not exist
    instance = get_instance_details(instance_id)
    ff_tags  = instance.freeform_tags

    # -- check that the snapshot exists
    snap = stop_if_snapsnot_does_not_exist(snap_dict, snapshot_name)

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

    # -- remove the freeform tag from the compute instance
    print (f"Removing the freeform tags from the compute instance ...{instance_id[-6:]}")
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

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "Implement snapshot-like feature on OCI compute instances")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-i", "--instance-id", help="compute instance OCID", required=True)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-c", "--create", help="Create a snapshot (name required)")
group.add_argument("-r", "--rollback", help="Rollback to a snapshot (name required)")
group.add_argument("-d", "--delete", help="Delete a snapshot (name required)")
group.add_argument("-l", "--list", help="List snapshots", action="store_true")
parser.add_argument("-ds", "--desc", help="Snapshot description (use with -c)")
args = parser.parse_args()

if args.create and not args.desc:
    parser.error("-c/--create requires -ds/--desc !")

if args.desc and not args.create:
    parser.error("-ds/--desc only requires -c/--create !")

profile     = args.profile
instance_id = args.instance_id

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit(2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- OCI clients
ComputeClient        = oci.core.ComputeClient(config)
BlockstorageClient   = oci.core.BlockstorageClient(config)
ObjectStorageClient  = oci.object_storage.ObjectStorageClient(config)
SearchClient         = oci.resource_search.ResourceSearchClient(config)
VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

# -- check that OCI bucket exists
response = ObjectStorageClient.get_namespace(retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
os_namespace = response.data
stop_if_bucket_does_not_exist()

# -- if using local files as database, create snapshots db folder if it does not exist
if db_mode == "local_file":
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
        print ("Create dir")

# -- do the job
if args.list:
    list_snapshots(instance_id)
elif args.create:
    create_snapshot(instance_id, args.create, args.desc)
elif args.rollback:
    rollback_snapshot(instance_id, args.rollback)
elif args.delete:
    delete_snapshot(instance_id, args.delete)

# -- the end
exit(0)
