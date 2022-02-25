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
# - For rollback: new instance will have a single VNIC with a single IP address
# - For rollback: very specific parameters of the original instance may not be present in the new instance after rollback
# - Compute instances with ephemeral public IP adress are not supported
# - The snapshot name must be unique on all instances (cannot use same name for 2 instances)
#
# Note: OCI tenant and region given by an OCI CLI PROFILE
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
# ---------------------------------------------------------------------------------------------------------------------------------

# -------- import
from ast import Delete
import oci
import sys
import os
import argparse
import re
from datetime import datetime
from time import sleep

# -------- variables
configfile = "~/.oci/config"    # Define config file to be used.

# -------- functions

# ---- Get the OCID of the cloned boot volume
def get_bootvol_id(snapshot_name):
    query = f"query bootvolume resources where freeformTags.key = 'snapshot_{snapshot_name}'"
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
         retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)

    if len(response.data.items) == 0:
        print (f"ERROR 04: no cloned boot volume found for snapshot {snapshot_name} !")
        print ("If you created the cloned boot volume a few minutes ago, it may not yet be fully available: wait and retry !")
        exit (4)
    elif len(response.data.items) > 1:
        print (f"ERROR 05: 2 or more cloned boot volumes found for snapshot {snapshot_name} !")
        exit (5)
    bootvol_id = response.data.items[0].identifier
    return bootvol_id

# ---- Get the OCIDs of the cloned block volume(s) if they exist
def get_blkvol_ids(snapshot_name):
    query      = f"query volume resources where freeformTags.key = 'snapshot_{snapshot_name}'"
    response   = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    blkvol_ids = []
    if len(response.data.items) > 0:
        for bkv in response.data.items:
            blkvol_ids.append(bkv.identifier)
    return blkvol_ids

# ---- Get the primary VNIC of the compute instance
def get_primary_vnic(cpt_id, instance_id):
    response        = ComputeClient.list_vnic_attachments(cpt_id, instance_id=instance_id,  retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    primary_vnic_id = response.data[0].vnic_id
    reponse         = VirtualNetworkClient.get_vnic(primary_vnic_id)
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
        exit (6)
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

# ---- Check if a block volume exists and is not TERMINATED
def is_volume_available(blkvol_id):
    try:
        response = BlockstorageClient.get_volume(blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        if response.data.lifecycle_state == "TERMINATED":
            return False
        else:
            return True
    except:
        return False

# ---- If the source volume does not exist any more, return the ID of the currently attached volume with same source volume
def get_alternate_source_volume_id(blkvol_attachments, source_blkvol_id, cloned_blkvol_id):
    for blkvol_attachment in blkvol_attachments:
        if get_source_volume_id(blkvol_attachment.volume_id) == source_blkvol_id:
            return blkvol_attachment.volume_id

    print (f"ERROR 12: cannot find the alternate source volume from cloned volume {cloned_blkvol_id} !")
    exit(12)

# ---- Get the volume attachment for a source volume
def get_source_volume_attachment(blkvol_attachments, source_blkvol_id):
    for blkvol_attachment in blkvol_attachments:
        if blkvol_attachment.volume_id == source_blkvol_id:
            return blkvol_attachment
    print (f"ERROR 11: cannot find volume attachment for block volume {source_blkvol_id} !")
    exit(11)

# ---- Get the name of the current boot volume for an instance
def get_boot_volume_name(ad_name, cpt_id, instance_id):
    response   = ComputeClient.list_boot_volume_attachments(ad_name, cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    bootvol_id = response.data[0].boot_volume_id
    response   = BlockstorageClient.get_boot_volume(bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    vol_name   = response.data.display_name
    return vol_name

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

# ---- Get the name of block volume for its id
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
def attach_block_volume_to_instance(blkvol_id, old_blkvol_attachments, new_instance_id, source_blkvol_id):
    source_volume_attachment = get_source_volume_attachment(old_blkvol_attachments, source_blkvol_id)
    response = ComputeClient.attach_volume(oci.core.models.AttachVolumeDetails(
        device       = source_volume_attachment.device,
        display_name = source_volume_attachment.display_name,
        is_read_only = source_volume_attachment.is_read_only,
        is_shareable = source_volume_attachment.is_shareable,
        type         = source_volume_attachment.attachment_type,
        instance_id  = new_instance_id,
        volume_id    = blkvol_id),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )

# ---- Stop if the snapshot name is used on another instance
def stop_if_snapshot_name_used(snapshot_name):
    query    = f"query instance resources where freeformTags.key = 'snapshot_{snapshot_name}'"
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
        retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    if len(response.data.items) > 0:
        print (f"ERROR 07: the snapshot name {snapshot_name} is already used on another instance. Please choose a different snapshot name !")
        exit(7)

# ==== List snapshots of a compute instance
# - get the list of snapshots from compute instance tags
# - display them sorted by most recent dates stored in tag value
def list_snapshots(instance_id):

    # -- get the instance details and stop if instance does not exist
    instance     = get_instance_details(instance_id)
    ff_tags_inst = instance.freeform_tags
    kv_sorted    = sorted(ff_tags_inst.items(), key=lambda x: x[1], reverse=True)

    snapshot_found = False
    for key,value in kv_sorted:
        if key.startswith("snapshot_"):
            snapshot_found = True
            snapshot_name  = key.replace("snapshot_","")
            print (f"{snapshot_name} created {value}")
    if not(snapshot_found):
        print ("No snapshot found for this compute instance !")

# ==== Create a snapshot of a compute instance
# - create a cloned of the boot volume
# - create a cloned of each attached block volume
# - add a freeform tag to the compute instance and the cloned volumes
# - tag key   = snapshot_<snapshot_name>
# - tag value = date in YYYY/MM/DD_HH:DD format
def create_snapshot(instance_id, snapshot_name):

    # -- get the instance details and stop if instance does not exist
    print (f"Getting details of compute instance ...{instance_id[-6:]}")
    instance     = get_instance_details(instance_id)
    ad_name      = instance.availability_domain
    cpt_id       = instance.compartment_id
    ff_tags_inst = instance.freeform_tags

    # -- make sure the snapshot_name is not already used on this compute instance
    tag_key   = f"snapshot_{snapshot_name}"
    if tag_key in ff_tags_inst:
        print ("A snapshot with that name already exists. Please retry using a different name !")
        exit(1)

    # -- make sure the snapshot_name is not already used on other compute instances
    stop_if_snapshot_name_used(snapshot_name)

    # -- make sure the compute instance does not use an ephemeral public IP
    primary_vnic = get_primary_vnic(cpt_id, instance_id)
    stop_if_ephemeral_public_ip(primary_vnic.public_ip)

    # -- get the OCID of boot volume
    response   = ComputeClient.list_boot_volume_attachments(ad_name, cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    bootvol_id = response.data[0].boot_volume_id

    # -- get the OCIDs of attached block volume(s) 
    response   = ComputeClient.list_volume_attachments(cpt_id, instance_id=instance_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    blkvol_ids = []
    nb_blkvols = len(response.data)
    if nb_blkvols > 0:
        for bkv in response.data:
            blkvol_ids.append(bkv.volume_id)

    # -- create a temporary volume group containing boot volume and block volume(s)
    print (f"Creating a temporary volume group (containing 1 boot volume and {nb_blkvols} block volume(s)) for data consistency")
    volume_ids = [ bootvol_id ]
    volume_ids.extend(blkvol_ids)
    source_details = oci.core.models.VolumeGroupSourceFromVolumesDetails(type="volumeIds", volume_ids=volume_ids)
    vg_details     = oci.core.models.CreateVolumeGroupDetails(
        availability_domain = ad_name, 
        compartment_id      = cpt_id, 
        display_name        = f"snapshot_{snapshot_name}_tempo",
        source_details      = source_details)
    response = BlockstorageClient.create_volume_group(vg_details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    vg_id    = response.data.id

    # -- cloned the volume group to make a consistent copy of boot volume and block volume(s)
    print (f"Cloning the temporary volume group")
    c_source_details = oci.core.models.VolumeGroupSourceFromVolumeGroupDetails(volume_group_id = vg_id)
    cvg_details      = oci.core.models.CreateVolumeGroupDetails(
        availability_domain = ad_name, 
        compartment_id      = cpt_id, 
        display_name        = f"snapshot_{snapshot_name}_cloned",
        source_details      = c_source_details)
    response         = BlockstorageClient.create_volume_group(cvg_details, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    cvg_id           = response.data.id
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
    tag_value = datetime.utcnow().strftime("%Y/%m/%d_%T")
    for id in cloned_volume_ids:
        if "ocid1.bootvolume" in id:
            rename_and_tag_boot_volume(id, snapshot_name, tag_key, tag_value)
        else:
            rename_and_tag_block_volume(id, snapshot_name, tag_key, tag_value)

    # -- delete the 2 volume groups, keeping only the cloned volumes
    print ("Deleting the 2 temporary volumes groups")
    response = BlockstorageClient.delete_volume_group(volume_group_id=vg_id,  retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
    response = BlockstorageClient.delete_volume_group(volume_group_id=cvg_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)

    # -- add tag to compute instance
    print ("Adding a freeform tag for this snapshot to the compute instance")
    ff_tags_inst[tag_key] = tag_value
    response = ComputeClient.update_instance(instance_id, oci.core.models.UpdateInstanceDetails(freeform_tags=ff_tags_inst), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)

# ==== Rollback a compute instance to a snapshot
def rollback_snapshot(instance_id, snapshot_name):

    # -- get the instance details and stop if instance does not exist
    print (f"Getting details of compute instance ...{instance_id[-6:]}")
    instance = get_instance_details(instance_id)
    ff_tags  = instance.freeform_tags

    # -- check that the snapshot exists
    tag_key  = f"snapshot_{snapshot_name}"
    if not(tag_key in ff_tags):
        print (f"ERROR 03: there is no snapshot named {snapshot_name} for this compute instance !")
        exit(3)

    # -- get the details for primary VNIC
    print (f"Getting details of primary VNIC")
    primary_vnic = get_primary_vnic(instance.compartment_id, instance_id)

    # -- make sure the compute instance does not use an ephemeral public IP
    public_ip_id = stop_if_ephemeral_public_ip(primary_vnic.public_ip)

    # --
    print (f"Getting details of boot volume and block volume(s)")

    # -- get the name of the current boot volume
    bootvol_name = get_boot_volume_name(instance.availability_domain, instance.compartment_id, instance_id)

    # -- get the id of the cloned boot volume
    new_bootvol_id = get_bootvol_id(snapshot_name)

    # -- get the list of ids of the cloned block volume(s) (may be empty)
    new_blkvol_ids = get_blkvol_ids(snapshot_name)

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

    # -- rename boot volume 
    print (f"Renaming cloned boot volume ...{new_bootvol_id[-6:]}")
    rename_boot_volume(new_bootvol_id, bootvol_name)

    # -- remove the freeform tag for this snapshot in the new compute instance
    tag_key  = f"snapshot_{snapshot_name}"
    new_ff_tags = instance.freeform_tags
    del new_ff_tags[tag_key]

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
        metadata          = {},
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

    # -- attach and rename cloned block volume(s)
    if len(new_blkvol_ids) > 0:
        print ("DEBUG 01: ",new_blkvol_ids)
        for blkvol_id in new_blkvol_ids:
            print ("DEBUG 02: ",blkvol_id)
            source_blkvol_id = get_source_volume_id(blkvol_id)
            print ("DEBUG 03: ",source_blkvol_id)
            if not(is_volume_available(source_blkvol_id)):
                alt_source_blkvol_id = get_alternate_source_volume_id(blkvol_attachments, source_blkvol_id, blkvol_id)
                source_blkvol_id = alt_source_blkvol_id

            print (f"Attaching cloned block volume ...{blkvol_id[-6:]} to new instance ...{new_instance_id[-6:]}")
            attach_block_volume_to_instance(blkvol_id, blkvol_attachments, new_instance_id, source_blkvol_id)

            print (f"Renaming cloned block volume ...{blkvol_id[-6:]}")
            rename_block_volume(blkvol_id, get_volume_name_from_id(source_blkvol_id))

    # -- delete the previously attached block volume(s)
    if len(blkvol_attachments) > 0:
        for blkvol_attachment in blkvol_attachments:
            print (f"Deleting original block volume ...{blkvol_attachment.volume_id[-6:]}")
            delete_block_volume(blkvol_attachment.volume_id)

    # -- remove freeforms tags from boot volume
    print (f"Removing tag from boot volume ...{new_bootvol_id[-6:]}")
    remove_boot_volume_tag(new_bootvol_id, snapshot_name)

    # -- remove freeforms tags from block volume(s)
    if len(new_blkvol_ids) > 0:
        for blkvol_id in new_blkvol_ids:
            print (f"Removing tag from block volume ...{blkvol_id[-6:]}")
            remove_block_volume_tag(blkvol_id, snapshot_name)

    # -- assign reserved public IP address if it was present on original instance
    if primary_vnic.public_ip != None:
        print (f"Attaching reserved public IP address to new compute instance")
        new_primary_vnic  = get_primary_vnic(instance.compartment_id, new_instance_id)
        new_private_ip_id = get_private_ip_id(new_primary_vnic.id)
        VirtualNetworkClient.update_public_ip(
            public_ip_id             = public_ip_id, 
            update_public_ip_details = oci.core.models.UpdatePublicIpDetails(private_ip_id = new_private_ip_id),
            retry_strategy           = oci.retry.DEFAULT_RETRY_STRATEGY)

    # -- new compute instance is ready
    print (f"The new compute instance is ready. OCID = {new_instance_id}")

# ==== Delete a snapshot of a compute instance
def delete_snapshot(instance_id, snapshot_name):

    # -- get the instance details and stop if instance does not exist
    instance = get_instance_details(instance_id)
    ff_tags  = instance.freeform_tags

    # -- check that the snapshot exists
    tag_key  = f"snapshot_{snapshot_name}"
    if not(tag_key in ff_tags):
        print (f"ERROR 03: there is no snapshot named {snapshot_name} for this compute instance !")
        exit(3)

    # -- get the ids of the cloned volume(s)
    bootvol_id = get_bootvol_id(snapshot_name)
    blkvol_ids = get_blkvol_ids(snapshot_name)

    # -- delete the cloned block volume(s)
    for blkvol_id in blkvol_ids:
        print (f"Deleting the cloned block volume ...{blkvol_id[-6:]}")
        response = BlockstorageClient.delete_volume(blkvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)

    # -- delete the cloned boot volume
    print (f"Deleting the cloned boot volume ...{bootvol_id[-6:]}")
    response = BlockstorageClient.delete_boot_volume(bootvol_id, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)

    # -- remove the freeform tag from the compute instance
    print (f"Removing the freeform tags from the compute instance ...{instance_id[-6:]}")
    del ff_tags[tag_key]
    ComputeClient.update_instance(instance_id, oci.core.models.UpdateInstanceDetails(freeform_tags=ff_tags), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)

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
args = parser.parse_args()
    
profile     = args.profile
instance_id = args.instance_id

# -- load profile from config file
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR 02: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- OCI clients
ComputeClient        = oci.core.ComputeClient(config)
BlockstorageClient   = oci.core.BlockstorageClient(config)
SearchClient         = oci.resource_search.ResourceSearchClient(config)
VirtualNetworkClient = oci.core.VirtualNetworkClient(config)

# -- do the job
if args.list:
    list_snapshots(instance_id)
elif args.create:
    create_snapshot(instance_id, args.create)
elif args.rollback:
    rollback_snapshot(instance_id, args.rollback)
elif args.delete:
    delete_snapshot(instance_id, args.delete)

# -- the end
exit (0)
