# Limiting OCI consumption

You can use the scripts in this folder to automatically stop OCI compute instances, OCI VM databases systems and OCI serverless autonomous databases when they are not needed and restart them when needed. 
By doing this, you can limit your consumption of OCI credits.

### Principles:
- create a tag namespace
- create 2 keys named automatic_shutdown and automatic_startup in this namespace
- set the list of possible values for those keys to the list: off, 00:00_UTC, 01:00_UTC, 02:00_UTC, ..., 23:00_UTC
- add the 2 tag keys to all compute instances, VM databases systems and serverless autonomous databases with appropriate value (off means no automatic shutdown/starting, and a time mean automatic shutdown/startup at this time)
- add the 2 tag keys with default tag values to the default tags for your compartment or for the root compartment if you want all compartments
- on a Linux machine (on-premises or in OCI):
    - install Python3 and Python OCI module (pip3 install oci)
    - configure OCI config file
    - create crontab jobs to run scripts every hour
    Example below:
    00 * * * 1,2,3,4,5 /home/opc/bin/OCI_instances_stop_start_tagged.py               -a --confirm_stop --confirm_start DEFAULT 
    10 * * * 1,2,3,4,5 /home/opc/bin/cpauliat/OCI_vm_db_systems_stop_start_tagged.py  -a --confirm_stop --confirm_start DEFAULT 
    20 * * * 1,2,3,4,5 /home/opc/bin/cpauliat/OCI_autonomous_dbs_stop_start_tagged.py -a --confirm_stop --confirm_start DEFAULT 

