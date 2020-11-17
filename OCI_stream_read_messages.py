#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script read messages from an OCI stream
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2020-11-17: Initial Version
# --------------------------------------------------------------------------------------------------------------

# -- import
import oci
import sys
from base64 import b64encode, b64decode

# ---------- Colors for output
COLOR_YELLOW="\033[93m"
COLOR_RED="\033[91m"
COLOR_GREEN="\033[32m"
COLOR_NORMAL="\033[39m"
COLOR_CYAN="\033[96m"
COLOR_BLUE="\033[94m"
COLOR_GREY="\033[90m"

# ---------- variables
configfile  = "~/.oci/config"    # OCI config file to be used
nb_messages = 300                # Max nb of message to be read

# ---------- functions
def usage():
    print ("Usage: {} OCI_PROFILE stream-id partition offset".format(sys.argv[0]))
    print ("")
    print ("Notes: ")
    print ("- Use offset \"all\" to list all messages in the stream partition")
    print ("- OCI_PROFILE must exist in {} file (see example below)".format(configfile))
    print ("")
    print ("[EMEAOSCf]")
    print ("tenancy     = ocid1.tenancy.oc1..aaaaaaaaw7e6nkszrry6d5hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("user        = ocid1.user.oc1..aaaaaaaayblfepjieoxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print ("fingerprint = 19:1d:7b:3a:17:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx:xx")
    print ("key_file    = /Users/cpauliat/.oci/api_key.pem")
    print ("region      = eu-frankfurt-1")
    exit (1)

# ---------- main

# -- parsing arguments
if (len(sys.argv) != 5):
    usage()

profile   = sys.argv[1] 
stream_id = sys.argv[2]
partition = sys.argv[3]
offset    = sys.argv[4]

# -- get OCI Config
try:
    config = oci.config.from_file(configfile,profile)
except:
    print ("ERROR: profile '{}' not found in config file {} !".format(profile,configfile))
    exit (2)

# -- Stream client
endpoint = "https://cell-1.streaming."+config["region"]+".oci.oraclecloud.com"
StreamClient = oci.streaming.StreamClient(config, endpoint)

# -- Create a cursor
print(COLOR_RED+"==== Creating a cursor ",end="")
if offset == "all":
    print ("of type = "+COLOR_CYAN+"TRIM_HORIZON"+COLOR_NORMAL)
    cursor_details = oci.streaming.models.CreateCursorDetails(
        partition=partition,
        type=oci.streaming.models.CreateCursorDetails.TYPE_TRIM_HORIZON)
else:
    print ("of type = "+COLOR_CYAN+"AT_OFFSET"+COLOR_NORMAL)
    cursor_details = oci.streaming.models.CreateCursorDetails(
        partition=partition,
        type=oci.streaming.models.CreateCursorDetails.TYPE_AT_OFFSET,
        offset=int(offset))
response = StreamClient.create_cursor(stream_id, cursor_details)
cursor = response.data.value

# -- Read messages from the stream
response = StreamClient.get_messages(stream_id, cursor, limit=nb_messages)
if len(response.data) > 0:
    print(COLOR_RED+"==== Reading "+COLOR_CYAN+"{}".format(len(response.data))+COLOR_RED+" messages"+COLOR_NORMAL)
    for message in response.data:
        # print raw JSON message
        # print (message)
        if message.key:
            decoded_key = b64decode(message.key.encode()).decode()
        else:
            decoded_key = "null"
        decoded_value = b64decode(message.value.encode()).decode()

        print (COLOR_GREEN+"PARTITION : "+COLOR_YELLOW,message.partition)
        print (COLOR_GREEN+"OFFSET    : "+COLOR_YELLOW,message.offset)
        print (COLOR_GREEN+"DATE      : "+COLOR_CYAN,message.timestamp)
        print (COLOR_GREEN+"KEY       : "+COLOR_CYAN,decoded_key)
        print (COLOR_GREEN+"MESSAGE   : "+COLOR_NORMAL,decoded_value)
        print (COLOR_YELLOW+"----------"+COLOR_NORMAL)

# -- happy end
exit (0)
