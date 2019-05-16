# my-oci-scripts
Scripts I wrote for OCI (Oracle Cloud Infrastructure)

### OCI_compartments_list.sh

> Bash script to display the names and IDs of all compartments in a OCI tenant using OCI CLI
>
> prerequisites : OCI CLI installed and OCI config file configured with profiles

### OCI_instances_list.sh

> Bash script to list the instance names and IDs in all compartments in a OCI tenant in a region using OCI CLI
>
> prerequisites : OCI CLI installed and OCI config file configured with profiles

### OCI_objects_list_in_compartment.sh

> Bash script to list OCI objects in a compartment in a region using OCI CLI
>
> Supported objects:
> - Compute       : compute instances, custom images, boot volumes, boot volumes backups
> - Block Storage : block volumes, block volumes backups, volume groups, volume groups backups
> - Object Storage: buckets
> - File Storage  : filesystems, mount targets
> - Network       : VCNs, DRGs, CPEs, IPsec connections, Public IPs
>
> prerequisites : OCI CLI installed and OCI config file configured with profiles
