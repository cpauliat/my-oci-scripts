#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists all ExaCC VM clusters and Exadata Infrastructures in a OCI tenant using OCI Python SDK 
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-09-21: Initial Version for VM clusters only
#    2021-01-18: HTML output showing a table with VM clusters details and status
#    2021-05-11: Add a retry strategy for some OCI calls in to avoid potential error "Too many requests for the tenants"
#    2021-08-18: Add a new table showing status for ExaCC Exadata Infrastructures
#    2021-08-18: Show VM clusters contained in each Exadata infrastructure in the Exadata infrastructure table
#    2021-08-18: Show the Exadata infrastructure for each VM cluster in the VM clusters table
#    2021-08-18: Add a 3rd table for autonomous VM clusters
#    2021-08-24: Optimize code for empty tables
#    2021-08-24: Add more details for Exadata infrastructures (Matthieu Bordonne)
#    2021-09-01: Show Memory for VM clusters (Matthieu Bordonne)
#    2021-11-30: Show number of DB nodes on regular VM clusters (not on Autonomous VM clusters)
#    2021-11-30: Replace "xx".format() strings by f-strings
#    2021-12-01: Add a retry strategy for ALL OCI calls in to avoid potential error "Too many requests for the tenants"
#    2022-01-03: use argparse to parse arguments
#    2022-04-27: Add the 'Quarterly maintenances" column
#    2022-05-03: Fix minor bug in HTML code (</tr> instead of <tr> for table end line)
# --------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse
from datetime import datetime, timedelta, timezone

# -------- variables
configfile             = "~/.oci/config"    # Define config file to be used.
exadatainfrastructures = []
vmclusters             = []
autonomousvmclusters   = []

# -------- functions

# ---- usage syntax
def usage():
    print (f"Usage: {sys.argv[0]} [-a] -p OCI_PROFILE")
    print ( "")
    print ( "    If -a is provided, the script search in all active regions instead of single region provided in profile")
    print ( "")
    print (f"note: OCI_PROFILE must exist in {configfile} file (see example below)")
    print ( "")
    print ( "[EMEAOSC]")
    print ( "tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ( "user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ( "fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ( "key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ( "region      = eu-frankfurt-1")
    exit (1)

# ---- Get the complete name of a compartment from its id, including parent and grand-parent..
def get_cpt_name_from_id(cpt_id):

    if cpt_id == RootCompartmentID:
        return "root"

    name=""
    for c in compartments:
        if (c.id == cpt_id):
            name=c.name
    
            # if the cpt is a direct child of root compartment, return name
            if c.compartment_id == RootCompartmentID:
                return name
            # otherwise, find name of parent and add it as a prefix to name
            else:
                name = get_cpt_name_from_id(c.compartment_id)+":"+name
                return name

# ---- Get details of an Exadata infrastructure from its id
def get_exadata_infrastructure_from_id (exadatainfrastructure_id):
    exainfra = {}
    for exadatainfrastructure in exadatainfrastructures:
        if exadatainfrastructure.id == exadatainfrastructure_id:
            exainfra = exadatainfrastructure
    return exainfra

# ---- Get url link to a specific Exadata infrastructure in OCI Console
def get_url_link_for_exadatainfrastructure(exadatainfrastructure):
    return f"https://console.{home_region}.oraclecloud.com/exacc/infrastructures/{exadatainfrastructure.id}?tenant={tenant_name}&region={exadatainfrastructure.region}"

# ---- Get url link to a specific VM cluster in OCI Console
def get_url_link_for_vmcluster(vmcluster):
    return f"https://console.{home_region}.oraclecloud.com/exacc/clusters/{vmcluster.id}?tenant={tenant_name}&region={vmcluster.region}"

# ---- Get url link to a specific autonomous VM cluster in OCI Console
def get_url_link_for_autonomousvmcluster(vmcluster):
    return f"https://console.{home_region}.oraclecloud.com/exacc/clusters/{vmcluster.id}?tenant={tenant_name}&region={vmcluster.region}"

# ---- Get the details for a next maintenance run
def get_next_maintenance_date(DatabaseClient, maintenance_run_id):
    if maintenance_run_id:
        response = DatabaseClient.get_maintenance_run (maintenance_run_id = maintenance_run_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
        return response.data.time_scheduled
    else:
        return ""

# ---- Get the details for a last maintenance run
def get_last_maintenance_dates(DatabaseClient, maintenance_run_id):
    if maintenance_run_id:
        response = DatabaseClient.get_maintenance_run (maintenance_run_id = maintenance_run_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
        return response.data.time_started, response.data.time_ended
    else:
        return "",""

# ---- Get details for an Exadata infrastructure
def exadatainfrastructure_get_details (exadatainfrastructure_id):
    global exadatainfrastructures

    # get details about exadatainfrastructure from regular API 
    DatabaseClient = oci.database.DatabaseClient(config)
    response = DatabaseClient.get_exadata_infrastructure (exadata_infrastructure_id = exadatainfrastructure_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    exainfra = response.data
    exainfra.region = config["region"]
    # print (f"<pre>DEBUG: {exainfra}</pre>")
    exainfra.last_maintenance_start, exainfra.last_maintenance_end = get_last_maintenance_dates(DatabaseClient, exainfra.last_maintenance_run_id)
    exainfra.next_maintenance = get_next_maintenance_date(DatabaseClient, exainfra.next_maintenance_run_id)
    exadatainfrastructures.append (exainfra)

# ---- Get details for a VM cluster
def vmcluster_get_details (vmcluster_id):
    global vmclusters

    # get details about vmcluster from regular API 
    DatabaseClient = oci.database.DatabaseClient(config)
    response = DatabaseClient.get_vm_cluster (vm_cluster_id = vmcluster_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    vmclust = response.data
    vmclust.region = config["region"]
    vmclusters.append (vmclust)

# ---- Get details for an autonomous VM cluster
def autonomousvmcluster_get_details (autonomousvmcluster_id):
    global autonomousvmclusters

    # get details about autonomous vmcluster from regular API 
    DatabaseClient = oci.database.DatabaseClient(config)
    response = DatabaseClient.get_autonomous_vm_cluster (autonomous_vm_cluster_id = autonomousvmcluster_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    autovmclust = response.data
    autovmclust.region = config["region"]
    autonomousvmclusters.append (autovmclust)

# ---- Get the list of Exadata infrastructures
def search_exadatainfrastructures():
    query = "query exadatainfrastructure resources"
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query), 
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for item in response.data.items:
        exadatainfrastructure_get_details (item.identifier)

# ---- Get the list of VM clusters
def search_vmclusters():
    query = "query vmcluster resources"
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for item in response.data.items:
        vmcluster_get_details (item.identifier)

# ---- Get the list of autonomous VM clusters
def search_autonomousvmclusters():
    query = "query autonomousvmcluster resources"
    SearchClient = oci.resource_search.ResourceSearchClient(config)
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for item in response.data.items:
        if item.lifecycle_state != "TERMINATED":
            autonomousvmcluster_get_details (item.identifier)

# ---- Generate HTML page 
def generate_html_headers():
    my_str = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>ExaCC VM clusters and Exadata infrastructure list</title>
    <style type="text/css">
        tr:nth-child(odd) { background-color: #f2f2f2; }
        tr:hover          { background-color: #ffdddd; }
        table {
            border-collapse: collapse;
            font-family:Arial;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr {
            background-color: #FFF5F0;
        }
        th, td {
            border: 1px solid #808080;
            text-align: center;
            padding: 7px;
        }
        caption {
            caption-side: bottom;
            padding: 10px;
            align: right;
            font-style: italic;
        }
    </style>
</head>"""
    print (my_str)

def generate_html_table_exadatainfrastructures():
    print ("    <table>")
    print (f"        <caption>ExaCC Exadata infrastructures in tenant <b>{tenant_name.upper()}</b> on <b>{now_str}</b></caption>")
    my_str = """        <tbody>
            <tr>
                <th>Region</th>
                <th>Compartment</th>
                <th>Name</th>
                <th>Quarterly<br>maintenances</th>
                <th>Shape</th>
                <th>Compute Nodes<br>/ Storage Nodes</th>
                <th>OCPUs<br>/ total</th>
                <th>Status</th>
                <th>VM cluster(s)</th>
                <th>Autonomous<br>VM cluster(s)</th>
            </tr>"""
    print (my_str)

    for exadatainfrastructure in exadatainfrastructures:
        format   = "%b %d %Y %H:%M %Z"
        # format   = "%Y/%m/%d %H:%M %Z"
        cpt_name = get_cpt_name_from_id(exadatainfrastructure.compartment_id)
        url      = get_url_link_for_exadatainfrastructure(exadatainfrastructure)
        print ( '            <tr>')
        print (f'                <td>&nbsp;{exadatainfrastructure.region}&nbsp;</td>')
        print (f'                <td>&nbsp;{cpt_name}&nbsp;</td>')
        print (f'                <td>&nbsp;<a href="{url}">{exadatainfrastructure.display_name}</a> &nbsp;</td>')
        print (f'                <td style="text-align: left">&nbsp;Last maintenance: <br>')
        try:
            print (f'                    &nbsp; - {exadatainfrastructure.last_maintenance_start.strftime(format)} (start)&nbsp;<br>')
        except:
            print (f'                    &nbsp; - no date/time (start)&nbsp;<br>')
        try:
            print (f'                    &nbsp; - {exadatainfrastructure.last_maintenance_end.strftime(format)} (end)&nbsp;<br><br>')
        except:
            print (f'                    &nbsp; - no date/time (end)&nbsp;<br><br>')
        print (f'                    &nbsp;Next maintenance: <br>')
        if exadatainfrastructure.next_maintenance == "":
            print (f'                    &nbsp; - Not yet scheduled &nbsp;</td>')
        else:
            # if the next maintenance date is soon, display it in red
            if (exadatainfrastructure.next_maintenance - now < timedelta(days=15)):
                print (f'                    &nbsp; - <span style="color: #ff0000">{exadatainfrastructure.next_maintenance.strftime(format)}</span>&nbsp;</td>')
            else:
                print (f'                    &nbsp; - {exadatainfrastructure.next_maintenance.strftime(format)}&nbsp;</td>')

        print (f'                <td>&nbsp;{exadatainfrastructure.shape}&nbsp;</td>')
        print (f'                <td>&nbsp;{exadatainfrastructure.compute_count} / {exadatainfrastructure.storage_count}&nbsp;</td>')
        print (f'                <td>&nbsp;{exadatainfrastructure.cpus_enabled} / {exadatainfrastructure.max_cpu_count}&nbsp;</td>')
        if (exadatainfrastructure.lifecycle_state != "ACTIVE"):
            print (f'                <td>&nbsp;<span style="color: #ff0000">{exadatainfrastructure.lifecycle_state}&nbsp;</span></td>')
        else:
            print (f'                <td>&nbsp;{exadatainfrastructure.lifecycle_state}&nbsp;</td>')

        vmc = []
        for vmcluster in vmclusters:
            if vmcluster.exadata_infrastructure_id == exadatainfrastructure.id:
                url = get_url_link_for_vmcluster(vmcluster)
                vmc.append(f'<a href="{url}">{vmcluster.display_name}</a>')
        separator = '&nbsp;<br>&nbsp;'
        print (f'                <td>&nbsp;{separator.join(vmc)}&nbsp;</td>')

        avmc = []
        for autonomousvmcluster in autonomousvmclusters:
            if autonomousvmcluster.exadata_infrastructure_id == exadatainfrastructure.id:
                url = get_url_link_for_autonomousvmcluster(autonomousvmcluster)
                avmc.append(f'<a href="{url}">{autonomousvmcluster.display_name}</a>')
        separator = ', '
        print (f'                <td>&nbsp;{separator.join(avmc)}&nbsp;</td>')

        print ('            </tr>')

    print ("        </tbody>")
    print ("    </table>")

def generate_html_table_vmclusters():
    print ("    <table>")
    print (f"        <caption>ExaCC VM clusters in tenant <b>{tenant_name.upper()}</b> on <b>{now_str}</b></caption>")
    my_str = """        <tbody>
            <tr>
                <th>Region</th>
                <th>Compartment</th>
                <th>Name</th>
                <th>Status</th>
                <th>DB nodes</th>
                <th>OCPUs</th>
                <th>Memory (GB)</th>
                <th>Exadata infrastructure</th>
            </tr>"""
    print (my_str)

    for vmcluster in vmclusters:
        cpt_name = get_cpt_name_from_id(vmcluster.compartment_id)
        url      = get_url_link_for_vmcluster(vmcluster)
        print ( '            <tr>')
        print (f'                <td>&nbsp;{vmcluster.region}&nbsp;</td>')
        print (f'                <td>&nbsp;{cpt_name}&nbsp;</td>')
        print (f'                <td>&nbsp;<a href="{url}">{vmcluster.display_name}</a> &nbsp;</td>')
        if (vmcluster.lifecycle_state != "AVAILABLE"):
            print (f'                <td>&nbsp;<span style="color: #ff0000">{vmcluster.lifecycle_state}&nbsp;</span></td>')
        else:
            print (f'                <td>&nbsp;{vmcluster.lifecycle_state}&nbsp;</td>')
        print (f'                <td>&nbsp;{len(vmcluster.db_servers)}&nbsp;</td>')
        print (f'                <td>&nbsp;{vmcluster.cpus_enabled}&nbsp;</td>')
        print (f'                <td>&nbsp;{vmcluster.memory_size_in_gbs}&nbsp;</td>')

        exadatainfrastructure = get_exadata_infrastructure_from_id(vmcluster.exadata_infrastructure_id)
        url  = get_url_link_for_exadatainfrastructure(exadatainfrastructure)      
        print (f'                <td>&nbsp;<a href="{url}">{exadatainfrastructure.display_name}</a>&nbsp;</td>')
        print ('            </tr>')

    print ("        </tbody>")
    print ("    </table>")

def generate_html_table_autonomousvmclusters():
    print ("    <table>")
    print (f"        <caption>ExaCC autonomous VM clusters in tenant <b>{tenant_name.upper()}</b> on <b>{now_str}</b></caption>")
    my_str = """        <tbody>
            <tr>
                <th>Region</th>
                <th>Compartment</th>
                <th>Name</th>
                <th>Status</th>
                <th>OCPUs</th>
                <th>Exadata infrastructure</th>
            </tr>"""
    print (my_str)

    for autonomousvmcluster in autonomousvmclusters:
        cpt_name = get_cpt_name_from_id(autonomousvmcluster.compartment_id)
        url      = get_url_link_for_autonomousvmcluster(autonomousvmcluster)
        print ( '            <tr>')
        print (f'                <td>&nbsp;{autonomousvmcluster.region}&nbsp;</td>')
        print (f'                <td>&nbsp;{cpt_name}&nbsp;</td>')
        print (f'                <td>&nbsp;<a href="{url}">{autonomousvmcluster.display_name}</a> &nbsp;</td>')
        if (autonomousvmcluster.lifecycle_state != "AVAILABLE"):
            print (f'                <td>&nbsp;<span style="color: #ff0000">{autonomousvmcluster.lifecycle_state}&nbsp;</span></td>')
        else:
            print (f'                <td>&nbsp;{autonomousvmcluster.lifecycle_state}&nbsp;</td>')
        print (f'                <td>&nbsp;{autonomousvmcluster.cpus_enabled}&nbsp;</td>')

        exadatainfrastructure = get_exadata_infrastructure_from_id(autonomousvmcluster.exadata_infrastructure_id)
        url  = get_url_link_for_exadatainfrastructure(exadatainfrastructure)      
        print (f'                <td>&nbsp;<a href="{url}">{exadatainfrastructure.display_name}</a>&nbsp;</td>')
        print ('            </tr>')

    print ("        </tbody>")
    print ("    </table>")

def generate_html():

    # headers
    generate_html_headers()

    # body start
    print ("<body>")

    # ExaCC Exadata infrastructures
    print ("    <h2>ExaCC Exadata infrastructures</h2>")
    if len(exadatainfrastructures) > 0:
        generate_html_table_exadatainfrastructures()
    else:
        print ("    None")

    # ExaCC VM Clusters
    print ("    <h2>ExaCC VM Clusters</h2>")
    if len(vmclusters) > 0:
        generate_html_table_vmclusters()
    else:
        print ("    None")

    # ExaCC Autonomous VM Clusters
    print ("    <h2>ExaCC Autonomous VM Clusters</h2>")
    if len(autonomousvmclusters) > 0:
        generate_html_table_autonomousvmclusters()
    else:
        print ("    None")

    # end of body and html page
    print ("    <p>")
    print ("</body>")
    print ("</html>")

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List ExaCC VM clusters in HTML format")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
args = parser.parse_args()

profile     = args.profile
all_regions = args.all_regions

# -- get info from profile    
try:
    config = oci.config.from_file(configfile,profile)
except:
    print (f"ERROR: profile '{profile}' not found in config file {configfile} !")
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"], retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY).data
RootCompartmentID = user.compartment_id

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(
    IdentityClient.list_region_subscriptions, 
    tenancy_id = RootCompartmentID, 
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
regions = response.data

# -- Find the home region to build the console URLs later
for r in regions:
    if r.is_home_region:
        home_region = r.region_name

# -- Get list of compartments with all sub-compartments
response = oci.pagination.list_call_get_all_results(
    IdentityClient.list_compartments,
    compartment_id = RootCompartmentID,
    compartment_id_in_subtree = True,
    retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
compartments = response.data

# -- Get current Date and Time (UTC timezone)
now = datetime.now(timezone.utc)
now_str = now.strftime("%c %Z")

# -- Get Tenancy Name
response = IdentityClient.get_tenancy(RootCompartmentID, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
tenant_name = response.data.name

# -- Run the search query/queries for ExaCC Exadata infrastructures and save results in exadatainfrastructures list
if not(all_regions):
    search_exadatainfrastructures()
else:
    for region in regions:
        config["region"]=region.region_name
        search_exadatainfrastructures()

# -- Run the search query/queries for ExaCC VM clusters and save results in vmclusters list
if not(all_regions):
    search_vmclusters()
else:
    for region in regions:
        config["region"]=region.region_name
        search_vmclusters()

# -- Run the search query/queries for ExaCC autonomous VM clusters and save results in autonomousvmclusters list
if not(all_regions):
    search_autonomousvmclusters()
else:
    for region in regions:
        config["region"]=region.region_name
        search_autonomousvmclusters()

# -- Generate HTML page with results
generate_html()

# -- the end
exit (0)
