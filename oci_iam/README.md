### Prerequisites for all Python 3 scripts: ###
- Python 3 installed
- OCI SDK for Python installed (pip3 install oci)
- OCI config file configured with profiles

### Prerequisites for Bash scripts: ###
- OCI CLI installed
- jq JSON parser installed
- OCI config file configured with profiles

### Prerequisites for Go programs: ###
- GO language installed
- OCI SDK for Go installed
- OCI config file configured with profiles

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
```

### OCI_compartments_list.py

```
Python 3 script to display the names and IDs of all compartments and subcompartments
in a OCI tenant using OCI Python SDK

Note: 
- By default, only active compartments are listed. Optionally (-d) deleted compartments can 
also be listed
```

### OCI_compartments_list.go

```
Go source code to display the names and IDs of all compartments and subcompartments
in a OCI tenant using OCI Go SDK (deleted compartments also listed)
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

### OCI_compartments_list_formatted.go

```
Similar to OCI_compartments_list.go with formatted output
Much faster than OCI_compartments_list_formatted.sh
```

### OCI_idcs.sh

```
Bash script to manage IDCS users and groups using REST APIs

Prerequisites :
- IDCS OAuth2 application already created with Client ID and Client secret available (for authentication)
```

### OCI_idcs.py

```
Python 3 script to manage IDCS users and groups using REST APIs

Prerequisites :
- Following Python 3 modules installed: sys, json, base64, requests, pathlib, pprint, columnar, operator
- IDCS OAuth2 application already created with Client ID and Client secret available (for authentication)
```