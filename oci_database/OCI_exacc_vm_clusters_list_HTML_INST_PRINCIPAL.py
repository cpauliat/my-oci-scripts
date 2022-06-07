#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists all ExaCC VM clusters and Exadata Infrastructures in a OCI tenant using OCI Python SDK 
# It looks in all compartments in the region given by profile or in all subscribed regions
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#
# THIS SCRIPT MUST BE EXECUTED FROM AN OCI COMPUTE INSTANCE WITH INSTANCE PRINCIPAL PERMISSIONS
#
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
#    2020-06-03: Add the --email option to send the HTML report by email
#    2022-06-03: Replace user authentication by instance principal authentication
# --------------------------------------------------------------------------------------------------------------

# -------- import
import oci
import sys
import argparse
import os
import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

# -------- variables
exadatainfrastructures = []
vmclusters             = []
autonomousvmclusters   = []

# -------- functions

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
    DatabaseClient = oci.database.DatabaseClient(config={}, signer=signer)
    response = DatabaseClient.get_exadata_infrastructure (exadata_infrastructure_id = exadatainfrastructure_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    exainfra = response.data
    exainfra.region = signer.region
    # print (f"<pre>DEBUG: {exainfra}</pre>")
    exainfra.last_maintenance_start, exainfra.last_maintenance_end = get_last_maintenance_dates(DatabaseClient, exainfra.last_maintenance_run_id)
    exainfra.next_maintenance = get_next_maintenance_date(DatabaseClient, exainfra.next_maintenance_run_id)
    exadatainfrastructures.append (exainfra)

# ---- Get details for a VM cluster
def vmcluster_get_details (vmcluster_id):
    global vmclusters

    # get details about vmcluster from regular API 
    DatabaseClient = oci.database.DatabaseClient(config={}, signer=signer)
    response = DatabaseClient.get_vm_cluster (vm_cluster_id = vmcluster_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    vmclust = response.data
    vmclust.region = signer.region
    vmclusters.append (vmclust)

# ---- Get details for an autonomous VM cluster
def autonomousvmcluster_get_details (autonomousvmcluster_id):
    global autonomousvmclusters

    # get details about autonomous vmcluster from regular API 
    DatabaseClient = oci.database.DatabaseClient(config={}, signer=signer)
    response = DatabaseClient.get_autonomous_vm_cluster (autonomous_vm_cluster_id = autonomousvmcluster_id, retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    autovmclust = response.data
    autovmclust.region = signer.region
    autonomousvmclusters.append (autovmclust)

# ---- Get the list of Exadata infrastructures
def search_exadatainfrastructures():
    query = "query exadatainfrastructure resources"
    SearchClient = oci.resource_search.ResourceSearchClient(config={}, signer=signer)
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query), 
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for item in response.data.items:
        exadatainfrastructure_get_details (item.identifier)

# ---- Get the list of VM clusters
def search_vmclusters():
    query = "query vmcluster resources"
    SearchClient = oci.resource_search.ResourceSearchClient(config={}, signer=signer)
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for item in response.data.items:
        vmcluster_get_details (item.identifier)

# ---- Get the list of autonomous VM clusters
def search_autonomousvmclusters():
    query = "query autonomousvmcluster resources"
    SearchClient = oci.resource_search.ResourceSearchClient(config={}, signer=signer)
    response = SearchClient.search_resources(
        oci.resource_search.models.StructuredSearchDetails(type="Structured", query=query),
        retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY)
    for item in response.data.items:
        if item.lifecycle_state != "TERMINATED":
            autonomousvmcluster_get_details (item.identifier)

# ---- Generate HTML page 
def generate_html_headers():
    html_content = """<!DOCTYPE html>
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
</head>\n"""

    return html_content

def generate_html_table_exadatainfrastructures():
    html_content  =   "    <table>\n"
    html_content +=  f"        <caption>ExaCC Exadata infrastructures in tenant <b>{tenant_name.upper()}</b> on <b>{now_str}</b></caption>\n"
    html_content += """        <tbody>
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
            </tr>\n"""

    for exadatainfrastructure in exadatainfrastructures:
        format   = "%b %d %Y %H:%M %Z"
        # format   = "%Y/%m/%d %H:%M %Z"
        cpt_name = get_cpt_name_from_id(exadatainfrastructure.compartment_id)
        url      = get_url_link_for_exadatainfrastructure(exadatainfrastructure)
        html_content +=  '            <tr>\n'
        html_content += f'                <td>&nbsp;{exadatainfrastructure.region}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{cpt_name}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;<a href="{url}">{exadatainfrastructure.display_name}</a> &nbsp;</td>\n'
        html_content += f'                <td style="text-align: left">&nbsp;Last maintenance: <br>\n'
        try:
            html_content += f'                    &nbsp; - {exadatainfrastructure.last_maintenance_start.strftime(format)} (start)&nbsp;<br>\n'
        except:
            html_content += f'                    &nbsp; - no date/time (start)&nbsp;<br>\n'
        try:
            html_content += f'                    &nbsp; - {exadatainfrastructure.last_maintenance_end.strftime(format)} (end)&nbsp;<br><br>\n'
        except:
            html_content += f'                    &nbsp; - no date/time (end)&nbsp;<br><br>\n'
        
        html_content += f'                    &nbsp;Next maintenance: <br>\n'
        if exadatainfrastructure.next_maintenance == "":
            html_content += f'                    &nbsp; - Not yet scheduled &nbsp;</td>\n'
        else:
            # if the next maintenance date is soon, display it in red
            if (exadatainfrastructure.next_maintenance - now < timedelta(days=15)):
                html_content += f'                    &nbsp; - <span style="color: #ff0000">{exadatainfrastructure.next_maintenance.strftime(format)}</span>&nbsp;</td>\n'
            else:
                html_content += f'                    &nbsp; - {exadatainfrastructure.next_maintenance.strftime(format)}&nbsp;</td>\n'

        html_content += f'                <td>&nbsp;{exadatainfrastructure.shape}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{exadatainfrastructure.compute_count} / {exadatainfrastructure.storage_count}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{exadatainfrastructure.cpus_enabled} / {exadatainfrastructure.max_cpu_count}&nbsp;</td>\n'
        if (exadatainfrastructure.lifecycle_state != "ACTIVE"):
            html_content += f'                <td>&nbsp;<span style="color: #ff0000">{exadatainfrastructure.lifecycle_state}&nbsp;</span></td>\n'
        else:
            html_content += f'                <td>&nbsp;{exadatainfrastructure.lifecycle_state}&nbsp;</td>\n'

        vmc = []
        for vmcluster in vmclusters:
            if vmcluster.exadata_infrastructure_id == exadatainfrastructure.id:
                url = get_url_link_for_vmcluster(vmcluster)
                vmc.append(f'<a href="{url}">{vmcluster.display_name}</a>')
        separator = '&nbsp;<br>&nbsp;'
        html_content += f'                <td>&nbsp;{separator.join(vmc)}&nbsp;</td>\n'

        avmc = []
        for autonomousvmcluster in autonomousvmclusters:
            if autonomousvmcluster.exadata_infrastructure_id == exadatainfrastructure.id:
                url = get_url_link_for_autonomousvmcluster(autonomousvmcluster)
                avmc.append(f'<a href="{url}">{autonomousvmcluster.display_name}</a>')
        separator = ', '
        html_content += f'                <td>&nbsp;{separator.join(avmc)}&nbsp;</td>\n'
        html_content +=  '            </tr>\n'

    html_content +=  "        </tbody>\n"
    html_content +=  "    </table>\n"

    return html_content

def generate_html_table_vmclusters():
    html_content  =   "    <table>\n"
    html_content +=  f"        <caption>ExaCC VM clusters in tenant <b>{tenant_name.upper()}</b> on <b>{now_str}</b></caption>\n"
    html_content += """        <tbody>
            <tr>
                <th>Region</th>
                <th>Compartment</th>
                <th>Name</th>
                <th>Status</th>
                <th>DB nodes</th>
                <th>OCPUs</th>
                <th>Memory (GB)</th>
                <th>Exadata infrastructure</th>
            </tr>\n"""

    for vmcluster in vmclusters:
        cpt_name = get_cpt_name_from_id(vmcluster.compartment_id)
        url      = get_url_link_for_vmcluster(vmcluster)
        html_content +=  '            <tr>\n'
        html_content += f'                <td>&nbsp;{vmcluster.region}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{cpt_name}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;<a href="{url}">{vmcluster.display_name}</a> &nbsp;</td>\n'
        if (vmcluster.lifecycle_state != "AVAILABLE"):
            html_content +=f'                <td>&nbsp;<span style="color: #ff0000">{vmcluster.lifecycle_state}&nbsp;</span></td>\n'
        else:
            html_content +=f'                <td>&nbsp;{vmcluster.lifecycle_state}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{len(vmcluster.db_servers)}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{vmcluster.cpus_enabled}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{vmcluster.memory_size_in_gbs}&nbsp;</td>\n'

        exadatainfrastructure = get_exadata_infrastructure_from_id(vmcluster.exadata_infrastructure_id)
        url  = get_url_link_for_exadatainfrastructure(exadatainfrastructure)      
        html_content += f'                <td>&nbsp;<a href="{url}">{exadatainfrastructure.display_name}</a>&nbsp;</td>\n'
        html_content +=  '            </tr>\n'

    html_content += "        </tbody>\n"
    html_content += "    </table>\n"

    return html_content

def generate_html_table_autonomousvmclusters():
    html_content  =   "    <table>\n"
    html_content +=  f"        <caption>ExaCC autonomous VM clusters in tenant <b>{tenant_name.upper()}</b> on <b>{now_str}</b></caption>\n"
    html_content += """        <tbody>
            <tr>
                <th>Region</th>
                <th>Compartment</th>
                <th>Name</th>
                <th>Status</th>
                <th>OCPUs</th>
                <th>Exadata infrastructure</th>
            </tr>\n"""

    for autonomousvmcluster in autonomousvmclusters:
        cpt_name = get_cpt_name_from_id(autonomousvmcluster.compartment_id)
        url      = get_url_link_for_autonomousvmcluster(autonomousvmcluster)
        html_content += '            <tr>\n'
        html_content += f'                <td>&nbsp;{autonomousvmcluster.region}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{cpt_name}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;<a href="{url}">{autonomousvmcluster.display_name}</a> &nbsp;</td>\n'
        if (autonomousvmcluster.lifecycle_state != "AVAILABLE"):
            html_content += f'                <td>&nbsp;<span style="color: #ff0000">{autonomousvmcluster.lifecycle_state}&nbsp;</span></td>\n'
        else:
            html_content += f'                <td>&nbsp;{autonomousvmcluster.lifecycle_state}&nbsp;</td>\n'
        html_content += f'                <td>&nbsp;{autonomousvmcluster.cpus_enabled}&nbsp;</td>\n'

        exadatainfrastructure = get_exadata_infrastructure_from_id(autonomousvmcluster.exadata_infrastructure_id)
        url  = get_url_link_for_exadatainfrastructure(exadatainfrastructure)      
        html_content += f'                <td>&nbsp;<a href="{url}">{exadatainfrastructure.display_name}</a>&nbsp;</td>\n'
        html_content +=  '            </tr>\n'

    html_content += "        </tbody>\n"
    html_content += "    </table>\n"

    return html_content

def generate_html_report():

    # headers
    html_report = generate_html_headers()

    # body start
    html_report += "<body>\n"

    # ExaCC Exadata infrastructures
    html_report += "    <h2>ExaCC Exadata infrastructures</h2>\n"
    if len(exadatainfrastructures) > 0:
        html_report += generate_html_table_exadatainfrastructures()
    else:
        html_report += "    None\n"

    # ExaCC VM Clusters
    html_report += "    <h2>ExaCC VM Clusters</h2>\n"
    if len(vmclusters) > 0:
        html_report += generate_html_table_vmclusters()
    else:
        html_report += "    None\n"

    # ExaCC Autonomous VM Clusters
    html_report += "    <h2>ExaCC Autonomous VM Clusters</h2>\n"
    if len(autonomousvmclusters) > 0:
        html_report += generate_html_table_autonomousvmclusters()
    else:
        html_report += "    None\n"

    # end of body and html page
    html_report += "    <p>\n"
    html_report += "</body>\n"
    html_report += "</html>\n"

    #
    return html_report

# ---- send an email to 1 or more recipients 
def send_email(email_recipients, html_report):

    # The email subject
    email_subject = f"{tenant_name.upper()}: ExaCC status report"

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = email_subject
    msg['From']    = email.utils.formataddr((email_sender_name, email_sender_address))
    msg['To']      = email_recipients

    # The email body for recipients with non-HTML email clients.
    # email_body_text = ( "The quarterly maintenance for Exadata Cloud @ Customer group  just COMPLETED.\n\n" 
    #                     f"The maintenance report is stored as object \n" )

    # The email body for recipients with HTML email clients.
    email_body_html = html_report

    # Record the MIME types: text/plain and html
    # part1 = MIMEText(email_body_text, 'plain')
    part2 = MIMEText(email_body_html, 'html')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case the HTML message, is best and preferred.
    # msg.attach(part1)
    msg.attach(part2)

    # send the EMAIL
    email_recipients_list = email_recipients.split(",")
    server = smtplib.SMTP(email_smtp_host, email_smtp_port)
    server.ehlo()
    server.starttls()
    #smtplib docs recommend calling ehlo() before & after starttls()
    server.ehlo()
    server.login(email_smtp_user, email_smtp_password)
    server.sendmail(email_sender_address, email_recipients_list, msg.as_string())
    server.close()

# ---- get the email configuration from environment variables:
#      EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SENDER_NAME, EMAIL_SENDER_ADDRESS 
def get_email_configuration():
    global email_smtp_user
    global email_smtp_password
    global email_smtp_host
    global email_smtp_port
    global email_sender_name
    global email_sender_address

    try:
        email_smtp_user      = os.environ['EMAIL_SMTP_USER']
        email_smtp_password  = os.environ['EMAIL_SMTP_PASSWORD']
        email_smtp_host      = os.environ['EMAIL_SMTP_HOST']
        email_smtp_port      = os.environ['EMAIL_SMTP_PORT']
        email_sender_name    = os.environ['EMAIL_SENDER_NAME']
        email_sender_address = os.environ['EMAIL_SENDER_ADDRESS']
    except:
        print ("ERROR: the following environments variables must be set for emails: EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD, EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, EMAIL_SENDER_NAME, EMAIL_SENDER_ADDRESS !")
        exit (3)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List ExaCC VM clusters in HTML format")
parser.add_argument("-a", "--all_regions", help="Do this for all regions", action="store_true")
parser.add_argument("-e", "--email", help="email the HTML report to a list of comma separated email addresses")
args = parser.parse_args()

all_regions = args.all_regions

if args.email:
    get_email_configuration()

# -- authentication using instance principal
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
IdentityClient = oci.identity.IdentityClient(config={}, signer=signer)
RootCompartmentID = signer.tenancy_id

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
        signer.region=region.region_name
        search_exadatainfrastructures()

# -- Run the search query/queries for ExaCC VM clusters and save results in vmclusters list
if not(all_regions):
    search_vmclusters()
else:
    for region in regions:
        signer.region=region.region_name
        search_vmclusters()

# -- Run the search query/queries for ExaCC autonomous VM clusters and save results in autonomousvmclusters list
if not(all_regions):
    search_autonomousvmclusters()
else:
    for region in regions:
        signer.region=region.region_name
        search_autonomousvmclusters()

# -- Generate HTML page with results
html_report = generate_html_report()

# -- Display HTML report 
print(html_report)

# -- Send email if requested
if args.email:
    send_email(args.email, html_report)

# -- the end
exit (0)
