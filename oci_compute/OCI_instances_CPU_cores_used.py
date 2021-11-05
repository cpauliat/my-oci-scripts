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
# --------------------------------------------------------------------------------------------------------------


# -- import
import oci
import sys

# -- variables
configfile     = "~/.oci/config"    # Define config file to be used.
list_cpu_types = [ "E2", "E3", "E4", "A1", "Std1", "Std2", "DenseIO2", "Opt3", "GPU2", "GPU3", "GPU4", "HPC2", "Others" ]
list_ads       = []
total_tenant   = 0

# -- functions
def usage():
    print ("Usage: {} [-a] OCI_PROFILE".format(sys.argv[0]))
    print ("")
    print ("    If -a is provided, the script search in all active regions instead of single region provided in profile")
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
                results[ad][fd][cpu_type] = 0

# -- Clear results variable

# -- Get the type of CPU and number of cores used by a compute instance
def get_cpu_type_and_nb_of_cores(compute_client, instance_id):
    global results;

    response = compute_client.get_instance(instance_id)
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

    results[ad][fd][cpu_type] += int(float(ocpus))

def display_results():    
    global total_tenant

    # table title
    print ("")

    #print (results)

    # table headers
    header_ad = "Availability domain"
    header_fd = "Fault domain"
    print (f"{header_ad:26s} {header_fd:12s} ",end="")
    for cpu_type in list_cpu_types:
        print (f"{cpu_type:>7s} ",end="")
    print ("")

    # tables content
    total = {}
    for cpu_type in list_cpu_types:
        total[cpu_type] = 0
    for ad in list_ads:
        fds = list(results[ad].keys())
        fds.sort()
        for fd in fds:
            print (f"{ad:26s} {fd:^12s} ",end="")
            for cpu_type in list_cpu_types:
                print (f"{results[ad][fd][cpu_type]:>7d} ",end="")
                total[cpu_type] += results[ad][fd][cpu_type]
            print ("")

    # total number of opcus per cpu_type
    total_region = 0
    trailer_ad = "TOTAL"
    trailer_fd = " "
    print (f"{trailer_ad:>26s} {trailer_fd:12s} ",end="")        
    for cpu_type in list_cpu_types:
        print (f"{total[cpu_type]:>7d} ",end="")
        total_region += total[cpu_type]
    print ("")

    # grand total per region
    trailer_ad = "REGION TOTAL"
    trailer_fd = " "
    print (f"{trailer_ad:>26s} {trailer_fd:12s} {total_region:>7d}")

    # update total for tenant
    total_tenant += total_region

def display_tenant_total():
    print ("")
    trailer_ad = "TENANT TOTAL"
    trailer_fd = " "
    print (f"{trailer_ad:>26s} {trailer_fd:12s} {total_tenant:>7d}")

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

    # display number of all ocpus per AD, FD and cpu type
    display_results()

# ---------- main

# -- parse arguments
all_regions = False

if (len(sys.argv) != 2) and (len(sys.argv) != 3):
    usage()

if len(sys.argv) == 2:
    profile = sys.argv[1] 
elif len(sys.argv) == 3:
    profile = sys.argv[2]
    if sys.argv[1] == "-a":
        all_regions=True
    else:
        usage()
    
#print ("profile = {}".format(profile))

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
regions = response.data

# -- Run the search query/queries
if not(all_regions):
    process(config)
else:
    for region in regions:
        config["region"] = region.region_name
        process(config)
    display_tenant_total()

# -- the end
exit (0)
