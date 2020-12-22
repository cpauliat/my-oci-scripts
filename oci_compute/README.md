### Prerequisites for all Python 3 scripts: ###
- Python 3 installed
- OCI SDK for Python installed (pip3 install oci)
- OCI config file configured with profiles

### Prerequisites for Bash scripts: ###
- OCI CLI installed
- jq JSON parser installed
- OCI config file configured with profiles

### OCI_instances_list_tagget.py ###
```
Python 3 script to list compute instances tagged with a specific tag namespace and key
```

### OCI_limits_compute.sh

```
Bash script to display the limits for compute in a OCI tenant using OCI CLI
in a region or in all active regions using OCI CLI
```

### OCI_free_tier_instances_delete.sh

```
Bash script to delete compute instances using free tier (shape VM.Standard.E2.Micro)
```

### OCI_free_tier_instances_delete_INST_PRINCIPAL.sh

```
Bash script to delete compute instances using free tier (shape VM.Standard.E2.Micro)
This script uses Instance Principal authentication instead of OCI profile for user.
```

### OCI_instances_stop_start_tagged.sh ###
```
Bash script to stop or start Autonomous Databases tagged with a specific tag namespace and key
```

### OCI_instances_stop_start_tagged.py ###
```
Python 3 script to stop or start compute instances tagged with a specific tag namespace and key
```

### OCI_instances_stop_start_tagged_INST_PRINCIPAL.py ###
```
Python 3 script to stop or start Autonomous Databases tagged with a specific tag namespace and key
This script uses Instance Principal authentication instead of OCI profile for user.
```

### OCI_instance_add_ephemeral_public_ip.sh ###
```
Bash script to add an ephemeral public IP address to the primary VNIC of a compute instance 
```

### OCI_instance_remove_public_ip.sh ###
```
Bash script to remove the public IP address of the primary VNIC of a compute instance 
```

### OCI_instance_renew_ephemeral_public_ip.sh ###
```
Bash script to renew an ephemeral public IP address to the primary VNIC of a compute instance 
(remove public IP address, then add new ephemeral public IP address)
```

### OCI_instances_search.py ###
```
Python 3 script to list compute instances using a Search query
```

### OCI_provided_images_list.py ###
```
Python 3 script to display the Oracle provided images list in an OCI region.
```

### OCI_custom_images_list_in_tenancy.py ###
```
Python 3 script to display the Custom images list in an OCI region.
```