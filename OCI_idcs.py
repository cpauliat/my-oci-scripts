#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------------------
# This Python 3 script executes IDCS operations on IDCS users and groups using REST APIs
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# Prerequisites: 
# - Python 3 installed
# - IDCS OAuth2 application created with Client ID and Client secret available
#
# Versions
#    2020-01-08: Initial Version
# --------------------------------------------------------------------------------------------------------------------------

# -- import
import sys
import base64
import json
import requests
from pathlib import Path
from pprint import pprint
from columnar import columnar
from operator import itemgetter, attrgetter

# -- Usage
def usage():
    print ("Usage: python3 {} operation [parameters]".format(sys.argv[0]))
    print ("")
    print ("Supported operations:")
    print ("- set_credentials idcs_instance client_ID client_secret        (prerequisite to all operations)")
    print ("- list_users")
    print ("- list_users_long")
    print ("- list_groups")
    print ("- list_users_in_group groupname")
    print ("- list_groups_of_user username")
    print ("- show_user username")
    print ("- show_group groupname")
    print ("- add_user username first_name last_name email_address")
    print ("- add_group groupname description")
    print ("- add_user_to_group username groupname")
    print ("- remove_user_from_group username groupname")
    print ("- deactivate_user username")
    print ("- activate_user username")
    print ("- delete_user username [--confirm]")
    print ("- delete_group groupname [--confirm]")
    print ("")
    print ("Notes:")
    print ("  If --confirm is provided in delete_user or delete_group operation, then deletion is done without asking for confirmation")
    print ("")
    print ("Examples:")
    print ("  python3 {} set_credentials idcs-f0f03632a0e346fdaccfaf527xxxxxx xxxxxxxxx xxxxxxxxxxx".format(sys.argv[0]))
    exit (1)


# -------- variables
CREDENTIALS_FILE=str(Path.home())+"/.oci/idcs_credentials.python3"
TOKEN_FILE="/tmp/idcs_auth_token.tmp"
TMP_JSON_FILE="/tmp/tmp_request_body.json"
MAX_OBJECTS="200"
IDCS_END_POINT="xx"
TOKEN="xx"

# -------- functions
def fatal_error(error_number):
  if   (error_number == 2):    print ("ERROR 2: cannot create credentials file {} !".format(CREDENTIALS_FILE))
  elif (error_number == 3):    print ("ERROR 3: credentials file {} not found !".format(CREDENTIALS_FILE))
  elif (error_number == 4):    print ("ERROR 4: syntax error in credentials file {} !".format(CREDENTIALS_FILE))
  elif (error_number == 5):    print ("ERROR 5: user name not found !")
  elif (error_number == 6):    print ("ERROR 6: group name not found !")
  elif (error_number == 7):    print ("ERROR 7: API request error !")
  exit (error_number)

# ---- create credentials file
def set_credentials(argv):
    if len(argv) != 5: usage()
    idcs_instance=argv[2]
    client_id=argv[3]
    client_secret=argv[4]

    try:
        f=open(CREDENTIALS_FILE,"w+")
    except:
        fatal_error(2)
    finally:
        f.write (idcs_instance+"\n")
        data=client_id+":"+client_secret
        f.writelines (str(base64.b64encode(data.encode("utf-8")),"utf-8")+"\n")
        f.close ()

# ---- get auth_token
def get_auth_token():
    global TOKEN

    api_url=IDCS_END_POINT+"/oauth2/v1/token"
    headers = { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'Authorization': 'Basic '+BASE64CODE }
    payload = "grant_type=client_credentials&scope=urn:opc:idm:__myscopes__"

    r = requests.post(api_url, headers=headers, data=payload)
    TOKEN = json.loads(r.text)['access_token']

# ---- initialize script
def init():
    global IDCS_END_POINT
    global BASE64CODE

    try:
        f = open(CREDENTIALS_FILE,"r")
    except IOError:
        fatal_error(3)
    finally:
        IDCS_INSTANCE=f.readline().rstrip('\n')
        BASE64CODE=f.readline().rstrip('\n')
        f.close()

    IDCS_END_POINT="https://"+IDCS_INSTANCE+".identity.oraclecloud.com"

    # get a new Authentication token  
    get_auth_token()

# ---- get user id from user name
def get_user_id_from_name(name):
    api_url=IDCS_END_POINT+"/admin/v1/Users?count="+MAX_OBJECTS
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    list=dict['Resources']
    for i in range(len(list)):
        if (list[i]['userName'] == name):
            return(list[i]['id'])
    fatal_error(5)

# ---- get group id from group name
def get_group_id_from_name(name):
    api_url=IDCS_END_POINT+"/admin/v1/Groups?count="+MAX_OBJECTS
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    list=dict['Resources']
    for i in range(len(list)):
        if (list[i]['displayName'] == name):
            return(list[i]['id'])
    fatal_error(6)

# ---- list users
def list_users():
    api_url=IDCS_END_POINT+"/admin/v1/Users?count="+MAX_OBJECTS
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    list=dict['Resources']
    table_headers=['====== USER NAME ======','ACTIVE','====== USER ID ======']
    table_list=[]
    for i in range(len(list)): table_list.append([ list[i]['userName'], list[i]['active'], list[i]['id'] ])
    # sort by user name
    table = columnar(sorted(table_list, key=itemgetter(0)), table_headers, no_borders=True)
    print(table)

def list_users_long():
    api_url=IDCS_END_POINT+"/admin/v1/Users?count="+MAX_OBJECTS
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    list=dict['Resources']
    table_headers=['====== USER NAME ======','ACTIVE','====== USER ID ======','==== CREATION DATE ====','==== CREATED BY ====']
    table_list=[]
    for i in range(len(list)): table_list.append([ list[i]['userName'], list[i]['active'], list[i]['id'], list[i]['meta']['created'], list[i]['idcsCreatedBy']['display'] ])
    # sort by creation date (oldest first)
    table = columnar(sorted(table_list, key=itemgetter(3)), table_headers, no_borders=True)
    print(table)

# ---- list groups
def list_groups():
    api_url=IDCS_END_POINT+"/admin/v1/Groups?count="+MAX_OBJECTS
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    list=dict['Resources']
    table_headers=['==== GROUP ID ====','==== GROUP NAME ====']
    table_list=[]
    for i in range(len(list)): table_list.append([ list[i]['id'], list[i]['displayName'] ])
    table = columnar(table_list, table_headers, no_borders=True)
    print(table)
    
# ---- list users in a group
def list_users_in_group(argv):
    if len(argv) != 3: usage()
    group_name=argv[2]
    group_id=get_group_id_from_name(group_name)
    api_url=IDCS_END_POINT+"/admin/v1/Groups/"+group_id+"?attributes=members"
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    try:
        list=dict['members']
        for i in range(len(list)):
            print (list[i]['name'])
    except:
        # no user in this group: dict['members'] does not exist
        print ("")

# ---- list groups assigned to a user
def list_groups_of_user(argv):
    if len(argv) != 3: usage()
    user_name=argv[2]
    user_id=get_user_id_from_name(user_name)
    api_url=IDCS_END_POINT+"/admin/v1/Users/"+user_id+"?attributes=groups"
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    try:
        list=dict['groups']
        for i in range(len(list)):
            print (list[i]['display'])
    except:
        # no group assigned to this user: dict['groups'] does not exist
        print ("")

# ---- show user details
def show_user(argv):
    if len(argv) != 3: usage()
    user_name=argv[2]
    user_id=get_user_id_from_name(user_name)
    api_url=IDCS_END_POINT+"/admin/v1/Users/"+user_id
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    pprint(dict)

# ---- show group details
def show_group(argv):
    if len(argv) != 3: usage()
    group_name=argv[2]
    group_id=get_group_id_from_name(group_name)
    api_url=IDCS_END_POINT+"/admin/v1/Groups/"+group_id
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.get(api_url, headers=headers)
    dict=r.json()
    pprint(dict)

# ---- add a new user
def add_user(argv):
    if len(argv) != 6: usage()
    user_name=argv[2]
    first_name=argv[3]
    last_name=argv[4]
    email_address=argv[5]
    api_url=IDCS_END_POINT+"/admin/v1/Users"
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    payload = """{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": \""""+user_name+"""\",
  "name": {
    "familyName": \""""+last_name+"""\",
    "givenName": \""""+first_name+"""\"
  },
  "emails": [{
    "value": \""""+email_address+"""\",
    "type": "work",
    "primary": true
  }]
}"""

    r = requests.post(api_url, headers=headers, data=payload)
    pprint(r.json())

# ---- add a new group
def add_group(argv):
    if len(argv) != 4: usage()
    group_name=argv[2]
    group_description=argv[3]
    api_url=IDCS_END_POINT+"/admin/v1/Groups"
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    payload = """{
    "displayName": \""""+group_name+"""\",
    "urn:ietf:params:scim:schemas:oracle:idcs:extension:group:Group": {
        "creationMechanism": "api",
        "description": \""""+group_description+"""\"
    },
    "schemas": [
        "urn:ietf:params:scim:schemas:core:2.0:Group",
        "urn:ietf:params:scim:schemas:oracle:idcs:extension:group:Group"
    ]
}"""

    r = requests.post(api_url, headers=headers, data=payload)
    pprint(r.json())

# ---- add a user to a group
def add_user_to_group(argv):
    if len(argv) != 4: usage()
    user_name=argv[2]
    group_name=argv[3]
    user_id=get_user_id_from_name(user_name)
    group_id=get_group_id_from_name(group_name)
    api_url=IDCS_END_POINT+"/admin/v1/Groups/"+group_id
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    payload = """{ "schemas": [ "urn:ietf:params:scim:api:messages:2.0:PatchOp" ],
  "Operations": [
    {
      "op": "add",
      "path": "members",
      "value": [
        {
          "value": \""""+user_id+"""\",
          "type": "User"
        }
      ] } ] }"""

    r = requests.patch(api_url, headers=headers, data=payload)
    pprint(r.json())

# ---- remove a user from a group
def remove_user_from_group(argv):
    if len(argv) != 4: usage()
    user_name=argv[2]
    group_name=argv[3]
    user_id=get_user_id_from_name(user_name)
    group_id=get_group_id_from_name(group_name)
    api_url=IDCS_END_POINT+"/admin/v1/Groups/"+group_id
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    payload = """{ "schemas": [ "urn:ietf:params:scim:api:messages:2.0:PatchOp" ],
  "Operations": [
    {
      "op": "remove",
      "path": "members[value eq \\\""""+user_id+"""\\\"]"
    } ] }"""
    r = requests.patch(api_url, headers=headers, data=payload)
    pprint(r.json())

# ---- deactivate a user
def deactivate_user(argv):
    if len(argv) != 3: usage()
    user_name=argv[2]
    user_id=get_user_id_from_name(user_name)
    api_url=IDCS_END_POINT+"/admin/v1/UserStatusChanger/"+user_id
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    payload = """{ "active": false, "schemas": [ "urn:ietf:params:scim:schemas:oracle:idcs:UserStatusChanger" ] }"""

    r = requests.put(api_url, headers=headers, data=payload)
    pprint(r.json())

# ---- activate a user
def activate_user(argv):
    if len(argv) != 3: usage()
    user_name=argv[2]
    user_id=get_user_id_from_name(user_name)
    api_url=IDCS_END_POINT+"/admin/v1/UserStatusChanger/"+user_id
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    payload = """{ "active": true, "schemas": [ "urn:ietf:params:scim:schemas:oracle:idcs:UserStatusChanger" ] }"""

    r = requests.put(api_url, headers=headers, data=payload)
    pprint(r.json())

# ---- delete a user
def delete_user(argv):
    if (len(argv) != 3) and (len(argv) != 4): usage()
    user_name=argv[2]
    if (len(argv) == 4): 
        confirm=argv[3] 
    else: 
        confirm="xx"

    user_id=get_user_id_from_name(user_name)
    if (confirm != "--confirm"):
        response=input("Do you confirm deletion of user {} (Id {}) ? (y/n): ".format(user_name,user_id))
        if (response != "y"): print ("User deletion cancelled !"); exit (0)

    api_url=IDCS_END_POINT+"/admin/v1/Users/"+user_id+"?forceDelete=True"
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.delete(api_url, headers=headers)
    if (r.status_code == 204):
        print ("User {} (Id {}) deleted !".format(user_name,user_id))
    else:
        fatal_error (7)

# ---- delete a group
def delete_group(argv):
    if (len(argv) != 3) and (len(argv) != 4): usage()
    group_name=argv[2]
    if (len(argv) == 4): 
        confirm=argv[3] 
    else: 
        confirm="xx"

    group_id=get_group_id_from_name(group_name)
    if (confirm!="--confirm"):
        response=input("Do you confirm deletion of group {} (Id {}) ? (y/n): ".format(group_name,group_id))
        if (response != "y"): print ("Group deletion cancelled !"); exit (0)

    api_url=IDCS_END_POINT+"/admin/v1/Groups/"+group_id+"?forceDelete=True"
    headers = { 'Content-Type': 'application/scim+json', 'Authorization': 'Bearer '+TOKEN }
    r = requests.delete(api_url, headers=headers)
    if (r.status_code == 204):
        print ("Group {} (Id {}) deleted !".format(group_name,group_id))
    else:
        fatal_error (7)

# -------- main

if len(sys.argv) < 2: usage()

operation=sys.argv[1]

if   (operation == "set_credentials"):        set_credentials(sys.argv)
elif (operation == "list_users"):             init();  list_users()
elif (operation == "list_users_long"):        init();  list_users_long()
elif (operation == "list_groups"):            init();  list_groups()
elif (operation == "list_users_in_group"):    init();  list_users_in_group(sys.argv)
elif (operation == "list_groups_of_user"):    init();  list_groups_of_user(sys.argv)
elif (operation == "show_user"):              init();  show_user(sys.argv)
elif (operation == "show_group"):             init();  show_group(sys.argv)
elif (operation == "add_user"):               init();  add_user(sys.argv)
elif (operation == "add_group"):              init();  add_group(sys.argv)
elif (operation == "add_user_to_group"):      init();  add_user_to_group(sys.argv)
elif (operation == "remove_user_from_group"): init();  remove_user_from_group(sys.argv)
elif (operation == "deactivate_user"):        init();  deactivate_user(sys.argv)
elif (operation == "activate_user"):          init();  activate_user(sys.argv)
elif (operation == "delete_user"):            init();  delete_user(sys.argv)
elif (operation == "delete_group"):           init();  delete_group(sys.argv)
else: usage()

exit (0)

