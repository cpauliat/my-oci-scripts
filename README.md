# my-oci-scripts
Scripts I developed for OCI (Oracle Cloud Infrastructure) using OCI CLI or OCI Python SDK
with precious help from Matthieu Bordonne

### OCI_generate_api_keys.sh

```
Bash script to generate an API key pair for OCI
```

### OCI_compartments_list.sh

```
Bash script to display the names and IDs of all compartments and subcompartments
in a OCI tenant using OCI CLI

Note: by default, only active compartments are listed. 
      optionally (-d) deleted compartments can also be listed

prerequisites :
- OCI CLI installed and OCI config file configured with profiles
- OCI user needs enough privileges to read the compartments list
```

### OCI_compartments_list.py

```
Python 3 script to display the names and IDs of all compartments and subcompartments
in a OCI tenant using OCI Python SDK

Note: by default, only active compartments are listed. 
      optionally (-d) deleted compartments can also be listed

prerequisites :
- Python 3 installed, OCI SDK installed and OCI config file configured with profiles
- OCI user needs enough privileges to read the compartments list
```

### OCI_compartments_list_formatted.sh

```
Similar to OCI_compartments_list.sh with formatted output
(color and indent to easily identify parents of subcompartments)
```

### OCI_compartments_list_formatted.py

```
Similar to OCI_compartments_list.py with formatted output
Much faster than OCI_compartments_list_formatted.sh
```

### OCI_instances_list.sh

```
Bash script to list the compute instances in all compartments and subcompartments
in a OCI tenant in a region using OCI CLI

Prerequisites :
- OCI CLI installed and OCI config file configured with profiles
- OCI user needs enough privileges to read all compute instances in all compartments
```

### OCI_autonomous_dbs_list.sh

```
Bash script to list the autonomous databases in all compartments and subcompartments
in a OCI tenant in a region using OCI CLI

Prerequisites :
- OCI CLI installed and OCI config file configured with profiles
- OCI user needs enough privileges to read all compute instances in all compartments
```

### OCI_limits_compute.sh

```
Bash script to display the limits for compute in a OCI tenant using OCI CLI
in a region or in all active regions using OCI CLI

prerequisites :
- OCI CLI 2.6.2 or later installed and OCI config file configured with profiles
- OCI user needs enough privileges to read the compartments list
```

### OCI_objects_list_in_compartment.sh

```
Bash script to list OCI objects in a compartment in a region or in all active regions using OCI CLI

Note: optionally (-r) it can list the objects in sub-compartments

Supported objects:
- COMPUTE            : compute instances, custom images, boot volumes, boot volumes backups
- BLOCK STORAGE      : block volumes, block volumes backups, volume groups, volume groups backups
- OBJECT STORAGE     : buckets
- FILE STORAGE       : file systems, mount targets
- NETWORKING         : VCN, DRG, CPE, IPsec connection, LB, public IPs
- DATABASE           : DB Systems, DB Systems backups, Autonomous DB, Autonomous DB backups
- RESOURCE MANAGER   : Stacks
- EDGE SERVICES      : DNS zones
- DEVELOPER SERVICES : Container clusters (OKE)
- IDENTITY           : Policies

Prerequisites :
- jq installed, OCI CLI installed and OCI config file configured with profiles
- OCI user needs enough privileges to read all objects in the compartment
```

### OCI_objects_list_in_compartment.py

```
Python 3 script to list OCI objects in a compartment in a region or in all active regions using OCI Python SDK

Note: optionally (-r) it can list the objects in sub-compartments

Supported objects:
- COMPUTE            : compute instances, custom images, boot volumes, boot volumes backups
- BLOCK STORAGE      : block volumes, block volumes backups, volume groups, volume groups backups
- OBJECT STORAGE     : buckets
- FILE STORAGE       : file systems, mount targets
- NETWORKING         : VCN, DRG, CPE, IPsec connection, LB, public IPs
- DATABASE           : DB Systems, DB Systems backups, Autonomous DB, Autonomous DB backups
- RESOURCE MANAGER   : Stacks
- EDGE SERVICES      : DNS zones
- DEVELOPER SERVICES : Container clusters (OKE)
- IDENTITY           : Policies

Prerequisites :
- Python 3 installed, OCI SDK installed and OCI config file configured with profiles
- OCI user needs enough privileges to read all objects in the compartment
```

### OCI_objects_list_in_tenancy.sh

```
Bash script to list OCI objects in a tenancy (all compartments) in a region 
or in all active regions using OCI CLI

Supported objects: same as OCI_objects_list_in_compartment.sh

Prerequisites :
- jq installed, OCI CLI installed and OCI config file configured with profiles
- script OCI_objects_list_in_compartment.sh present and accessible (update PATH)
- OCI user needs enough privileges to read all objects in all compartments
```

### OCI_instances_stop_start_tagged.sh

```
Bash script to start or stop OCI compute instances tagged with a specific value 
in a region or in all active regions using OCI CLI (all compartments)

Prerequisites :
- jq installed, OCI CLI installed and OCI config file configured with profiles
- OCI user needs enough privileges
```

### OCI_autonomous_dbs_stop_start_tagged.sh

```
Bash script to start or stop OCI compute instances tagged with a specific value 
in a region or in all active regions using OCI CLI (all compartments)

Prerequisites :
- jq installed, OCI CLI installed and OCI config file configured with profiles
- OCI user needs enough privileges
```

### OCI_vm_db_mv sytems_stop_start_tagged.sh

```
Bash script to start or stop database systems node tagged with a specific value 
in a region or in all active regions using OCI CLI (all compartments)

Prerequisites :
- jq installed, OCI CLI installed and OCI config file configured with profiles
- OCI user needs enough privileges

Note: supports only non RAC VM.Standard* database systems
```

### OCI_free_tier_instances_delete.sh

```
Bash script to delete compute instances using free tier (shape VM.Standard.E2.Micro)

Prerequisites :
- jq installed, OCI CLI 2.6.11 or later installed and OCI config file configured with profiles
- OCI user needs enough privileges
```

### OCI_free_tier_autonomous_dbs_delete.sh

```
Bash script to delete autonomous database instances using free tier

Prerequisites :
- jq installed, OCI CLI 2.6.11 or later installed and OCI config file configured with profiles
- OCI user needs enough privileges
```

### OCI_idcs.sh

```
Bash script to manage IDCS users and groups using REST APIs

Prerequisites :
- jq installed 
- IDCS OAuth2 application already created with Client ID and Client secret available (for authentication)
```

### OCI_idcs.py

```
Python 3 script to manage IDCS users and groups using REST APIs

Prerequisites :
- Python 3 installed  
- Following Python 3 modules installed: sys, json,base64, requests, pathlib, pprint, columnar, operator
- IDCS OAuth2 application already created with Client ID and Client secret available (for authentication)
```

### OCI_vcns_show_in_compartment.py

```
Python 3 script to show detailed VCNs in a compartment using OCI Python SDK

Prerequisites :
- Python 3 installed, OCI SDK installed and OCI config file configured with profiles
```
