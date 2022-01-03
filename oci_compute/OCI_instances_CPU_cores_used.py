#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists number of CPU cores used by compute instances in a OCI tenant using OCI Python SDK 
# and search queries
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-05: Initial Version
#    2021-11-05: Add HTML output as alternative to text output
#    2021-11-08: Add date/time of report
#    2021-11-08: Add option to also display CPU cores for running instances on HTML output
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------


# -- import
import oci
import sys
import argparse
from datetime import datetime 

# -- variables
configfile           = "~/.oci/config"    # Define config file to be used.
list_cpu_types       = [ "E2", "E3", "E4", "A1", "Std1", "Std2", "DenseIO2", "Opt3", "GPU2", "GPU3", "GPU4", "HPC2", "Others" ]
list_ads             = []
total_tenant_all     = 0
total_tenant_running = 0

# -- functions
def usage():
    print ("Usage: {} [-a] [-o html] -p OCI_PROFILE".format(sys.argv[0]))
    print ("")
    print ("    If -a is provided, the script search in all active regions instead of single region provided in profile")
    print ("    If -o html is provided, output is HTML instead of text")
    print ("")
    print ("note: OCI_PROFILE must exist in {} file (see example below)".format(configfile))
    print ("")
    print ("[EMEAOSCf]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# -- Get the complete name of a compartment from its id, including parent and grand-parent..
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

# -- Initialize results variable
def init_results():
    global results;

    results = {}
    list_fds = [ "FD1", "FD2", "FD3" ]
    for ad in list_ads:
        results[ad] = {}
        for fd in list_fds:
            results[ad][fd] = {}
            for cpu_type in list_cpu_types:
                results[ad][fd][cpu_type] = {}
                results[ad][fd][cpu_type]['running'] = 0
                results[ad][fd][cpu_type]['all']     = 0


# -- Clear results variable

# -- Get the type of CPU and number of cores used by a compute instance
def get_cpu_type_and_nb_of_cores(compute_client, instance_id):
    global results;

    response = compute_client.get_instance(instance_id)
    state = response.data.lifecycle_state

    # ignore terminated compute instances
    if state == "TERMINATED":
        return

    shape = response.data.shape
    ocpus = response.data.shape_config.ocpus
    ad    = response.data.availability_domain
    fd    = response.data.fault_domain.replace("FAULT-DOMAIN-","FD")

    if ".E2." in shape:
        cpu_type = "E2"
    elif ".E3." in shape:
        cpu_type = "E3"
    elif ".E4." in shape:
        cpu_type = "E4"       
    elif ".A1." in shape:
        cpu_type = "A1"  
    elif ".Standard1." in shape:
        cpu_type = "Std1" 
    elif ".Standard2." in shape:
        cpu_type = "Std2" 
    elif ".DenseIO2." in shape:
        cpu_type = "DenseIO2"
    elif ".Optimized3." in shape:
        cpu_type = "Opt3" 
    elif ".GPU2." in shape:
        cpu_type = "GPU2"  
    elif ".GPU3." in shape:
        cpu_type = "GPU3" 
    elif ".GPU4." in shape:
        cpu_type = "GPU4"  
    elif ".HPC2." in shape:
        cpu_type = "HPC2" 
    else:
        cpu_type = "Others"

    results[ad][fd][cpu_type]['all'] += int(float(ocpus))
    if state != "STOPPED":
        results[ad][fd][cpu_type]['running'] += int(float(ocpus))


def display_results_text():    
    global total_tenant_all
    global total_tenant_running

    # table title
    print ("")

    # table headers
    header_ad = "Availability domain"
    header_fd = "Fault domain"
    print (f"{header_ad:26s} {header_fd:12s} ",end="")
    for cpu_type in list_cpu_types:
        print (f"{cpu_type:>7s} ",end="")
    print ("")

    # tables content
    total_all     = {}
    total_running = {}
    for cpu_type in list_cpu_types:
        total_all[cpu_type] = 0
        total_running[cpu_type] = 0
    for ad in list_ads:
        fds = list(results[ad].keys())
        fds.sort()
        for fd in fds:
            print (f"{ad:26s} {fd:^12s} ",end="")
            for cpu_type in list_cpu_types:
                total_all[cpu_type] += results[ad][fd][cpu_type]['all']
                total_running[cpu_type] += results[ad][fd][cpu_type]['running']
                # Choice 1: display zeros
                # print (f"{results[ad][fd][cpu_type]:>7d} ",end="")

                # Choice 2: display . instead of zeros for better readibility
                if results[ad][fd][cpu_type]['all'] != 0:
                    print (f"{results[ad][fd][cpu_type]['all']:>7d} ",end="")
                else:
                    print (f"{'.':>7s} ",end="")
            print ("")

    # total number of opcus per cpu_type
    total_region_all = 0
    total_region_running = 0
    trailer_ad = "TOTAL:"
    trailer_fd = " "
    print (f"{trailer_ad:>26s} {trailer_fd:12s} ",end="")        
    for cpu_type in list_cpu_types:
        print (f"{total_all[cpu_type]:>7d} ",end="")
        total_region_all     += total_all[cpu_type]
        total_region_running += total_running[cpu_type]
    print ("")

    # grand total per region
    trailer_ad = "REGION TOTAL:"
    print (f"{trailer_ad:>26s} {total_region_all:^12d}")

    # update total for tenant
    total_tenant_all     += total_region_all
    total_tenant_running += total_region_running

# -- begin of HTML code
def HTML_begin():
    my_str = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>OCPUS report for OCI compute instances</title>
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
        #tenant-total {
            font-family:Arial;
            color: red; 
        }
        #signature {
            font-size: 80%;
        }
    </style>
</head>
<body>"""
    print (my_str)

# -- end of HTML code
def HTML_end():
    print ("<p>")
    now = datetime.utcnow().strftime("%Y/%m/%d %T")
    print (f"&nbsp;&nbsp;&nbsp;&nbsp;Date/time of report: {now:s} UTC")
    print ("<p>")
    url = "https://github.com/cpauliat/my-oci-scripts/blob/master/oci_compute/OCI_instances_CPU_cores_used.py"
    print (f"&nbsp;&nbsp;&nbsp;&nbsp;<span id=\"signature\">This report was generated using Python script <a href=\"{url}\">{url}</a></span>")
    print ("<p>")
    print ("</body>")
    print ("</html>")

# -- HTML table for the region
def display_results_HTML_table():    
    global total_tenant_all
    global total_tenant_running

    print ("    <table>")

    # table headers
    print (f"        <caption>OCPUs for compute instances in region <b>{config['region']}</b></caption>")
    my_str = """        <tbody>
            <tr>
                <th>Availability domain</th>
                <th>Fault domain</th>"""
    print (my_str)
    for cpu_type in list_cpu_types:
        print (f"                <th>{cpu_type}</th>")
    my_str = """
            </tr>"""
    print (my_str)

    # tables content
    total_all = {}
    total_running = {}
    for cpu_type in list_cpu_types:
        total_all[cpu_type] = 0
        total_running[cpu_type] = 0
    for ad in list_ads:
        fds = list(results[ad].keys())
        fds.sort()
        for fd in fds:
            print("            <tr>")
            print (f"                <td>{ad}</td>")
            print (f"                <td>{fd}</td>")
            for cpu_type in list_cpu_types:
                total_all[cpu_type]     += results[ad][fd][cpu_type]['all']
                total_running[cpu_type] += results[ad][fd][cpu_type]['running']
                print (f"                <td>{results[ad][fd][cpu_type]['running']} / {results[ad][fd][cpu_type]['all']}</td>")
            print("            </tr>")

    # total number of opcus per cpu_type
    print("            <tr>")
    total_region_all     = 0
    total_region_running = 0
    print (f"                <td colspan=\"2\"><b>REGION TOTALS</b></td>")
    #print (f"                <td>&nbsp;</td>")      
    for cpu_type in list_cpu_types:
        print (f"                <td><b>{total_running[cpu_type]} / {total_all[cpu_type]:d}</b></td>")
        total_region_all     += total_all[cpu_type]
        total_region_running += total_running[cpu_type]
    print("            </tr>")

    # grand total per region
    print("            <tr>")
    print (f"                <td colspan=\"2\"><b>REGION GRAND TOTAL</b></td>")
    print (f"                <td colspan=\"{len(list_cpu_types)}\"><b>{total_region_running} / {total_region_all}</b></td>")      
    # for cpu_type in list_cpu_types:
    #     print (f"                <td>&nbsp;</td>")
    print("            </tr>")

    # end of HTML table
    print("        </tbody>")
    print("    </table>")

    # add space between tables
    print("    <p>")

    # update total for tenant
    total_tenant_all     += total_region_all
    total_tenant_running += total_region_running

def display_tenant_total_text():
    print ("")
    trailer_ad = "TENANT TOTAL:"
    print (f"{trailer_ad:>26s} {total_tenant_all:^12d}")

def display_tenant_total_HTML():
    print (f"&nbsp;&nbsp;&nbsp;&nbsp;<span id=\"tenant-total\"><b>TENANT TOTAL: {total_tenant_running:d} / {total_tenant_all:d}<b></span>")
    print ("<p>")

def process(l_config):
    global list_ads

    # get the list of ADs names
    identity_client = oci.identity.IdentityClient(l_config)
    response = identity_client.list_availability_domains(RootCompartmentID)
    ads      = response.data
    list_ads = []
    for ad in ads: 
        list_ads.append(ad.name)

    # init / clear results variable
    init_results()

    # find all compute instances in the region
    query = "query instance resources"
    SearchClient = oci.resource_search.ResourceSearchClient(l_config)
    response = SearchClient.search_resources(oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query))

    # for each instance, look at cpu type and ocpu number
    ComputeClient = oci.core.ComputeClient(l_config)
    for item in response.data.items:
        get_cpu_type_and_nb_of_cores(ComputeClient, item.identifier)

    # compute total per region and update total for tenant
    # and display number of all ocpus per AD, FD and cpu type
    if output_format == "html":
        display_results_HTML_table()
    else:
        display_results_text()

# ---------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List number of CPU cores used by compute instances")
parser.add_argument("-p", "--profile", help="OCI profile", required=True)
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
parser.add_argument("-o", "--output_format", help="Output format ('html' or 'text'). Default is 'text'", choices=["html","text"])
args = parser.parse_args()
    
profile     = args.profile
all_regions = args.all_regions
if args.output_format:
    output_format = args.output_format
else:
    output_format = "text"

# -- get info from profile
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

IdentityClient = oci.identity.IdentityClient(config)
user = IdentityClient.get_user(config["user"]).data
RootCompartmentID = user.compartment_id

# -- get list of subscribed regions
response = oci.pagination.list_call_get_all_results(IdentityClient.list_region_subscriptions, RootCompartmentID)
regions  = response.data

# -- HTML output
if output_format == "html":
    HTML_begin()

# -- Run the search query/queries
if not(all_regions):
    process(config)
else:
    for region in regions:
        config["region"] = region.region_name
        process(config)
    if output_format == "html":
        display_tenant_total_HTML()
    else:
        display_tenant_total_text()

# -- HTML output
if output_format == "html":
    HTML_end()

# -- the end
exit (0)
