#!/bin/bash

# --------------------------------------------------------------------------------------------------------------
# This script will list the public IP addresses ranges used by OCI in all OCI regions:
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# Versions
#    2020-07-23: Initial Version
# --------------------------------------------------------------------------------------------------------------

# -------- main

URL="https://docs.cloud.oracle.com/en-us/iaas/tools/public_ip_ranges.json"

curl $URL 2>/dev/null |egrep "region|cidr" |egrep -v "regions|cidrs" | sed -e 's#",##g' -e 's#^.*region": "##g' -e 's#^.*cidr": "#    #g'