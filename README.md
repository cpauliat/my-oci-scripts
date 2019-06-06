# my-oci-scripts
Scripts I developed for OCI (Oracle Cloud Infrastructure)

### OCI_compartments_list.sh

> Bash script to display the names and IDs of all compartments and subcompartments in a OCI tenant using OCI CLI
>
> prerequisites :
> - OCI CLI installed and OCI config file configured with profiles
> - OCI user needs enough privileges to read the compartments list

### OCI_compartments_list_formatted.sh

> Similar to OCI_compartments_list.sh with formatted output
> (color and indent to easily identify parents of subcompartments)

### OCI_instances_list.sh

> Bash script to list the instance names and IDs in all compartments and subcompartments in a OCI tenant in a region using OCI CLI
>
> Prerequisites :
> - OCI CLI installed and OCI config file configured with profiles
> - OCI user needs enough privileges to read all compute instances in all compartments

### OCI_objects_list_in_compartment.sh

> Bash script to list OCI objects in a compartment in a region or in all active regions using OCI CLI
>
> Note: it does not list the objects in subcompartments
>
> Supported objects:
> - COMPUTE            : compute instances, custom images, boot volumes, boot volumes backups
> - BLOCK STORAGE      : block volumes, block volumes backups, volume groups, volume groups backups
> - OBJECT STORAGE     : buckets
> - FILE STORAGE       : file systems, mount targets
> - NETWORKING         : VCN, DRG, CPE, IPsec connection, LB, public IPs
> - DATABASE           : DB Systems, DB Systems backups, Autonomous DB, Autonomous DB backups
> - RESOURCE MANAGER   : Stacks
> - EDGE SERVICES      : DNS zones
> - DEVELOPER SERVICES : Container clusters (OKE)
> - IDENTITY           : Policies
>
> Prerequisites :
> - jq installed, OCI CLI installed and OCI config file configured with profiles
> - OCI user needs enough privileges to read all objects in the compartment

### OCI_objects_list_in_tenancy.sh

> Bash script to list OCI objects in a tenancy (all compartments) in a region or in all active regions using OCI CLI
>
> Supported objects:
> - Compute       : compute instances, custom images, boot volumes, boot volumes backups
> - Block Storage : block volumes, block volumes backups, volume groups, volume groups backups
> - Object Storage: buckets
> - File Storage  : filesystems, mount targets
> - Network       : VCNs, DRGs, CPEs, IPsec connections, Public IPs
> - IAM           : Policies
>
> Prerequisites :
> - jq installed, OCI CLI installed and OCI config file configured with profiles
> - script OCI_objects_list_in_compartment.sh present and accessible (update PATH)
> - OCI user needs enough privileges to read all objects in all compartments
