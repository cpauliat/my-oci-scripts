### Prerequisites for all Python scripts: ###
- Python 3 installed
- OCI SDK for Python installed (pip3 install oci)
- OCI config file configured with profiles

### OCI_preauth_requests_list.py

```
Python 3 script to list pre-authenticated requests in an object storage bucket using OCI Python SDK
It lists the expired and actives requests
```

### OCI_preauth_requests_delete_expired.py

```
Python 3 script to delete expired pre-authenticated requests in an object storage bucket using OCI Python SDK
It first lists the expired requests, then asks to confirm deletion, then deletes them.
```

### OCI_preauth_requests_delete.py

```
Python 3 script to delete individual pre-authenticated requests in an object storage bucket using OCI Python SDK
It first lists all the requests, then for each of them ask if the request must be deleted and deletes it if confirmed .
```

### OCI_preauth_requests_create.py

```
Python 3 script to create a pre-authenticated request for an object in an object storage bucket using OCI Python SDK
```

### OCI_object_storage_report.py

```
Python 3 script to display object storage consumption for all compartments in 1 region using OCI Python SDK
```
