#!/bin/bash

# --------------------------------------------------------------------------------------------------------------------------
# This script executes IDCS operations on IDCS users and groups using REST APIs
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
#
# Prerequisites: 
# - jq JSON PARSER installed
# - IDCS OAuth2 application created with Client ID and Client secret available
#
# Versions
#    2020-01-06: Initial Version
#    2020-01-07: Optimize requests for list_users_in_group() and list_groups_of_user()
# --------------------------------------------------------------------------------------------------------------------------

usage()
{
cat << EOF
Usage: $0 operation [parameters]

Supported operations:
- set_credentials idcs_instance client_ID client_secret        (prerequisite to all operations)
- list_users
- list_groups
- list_users_in_group groupname
- list_groups_of_user username
- show_user username
- show_group groupname
- add_user username first_name last_name email_address
- add_group groupname description
- add_user_to_group username groupname
- remove_user_from_group username groupname
- deactivate_user username
- activate_user username
- delete_user username [--confirm]                
- delete_group groupname [--confirm]

Notes:
  If --confirm is provided in delete_user or delete_group operation, then deletion is done without asking for confirmation

Examples:
  $0 set_credentials idcs-f0f03632a0e346fdaccfaf527c88dcb7 xxxxxxxxx xxxxxxxxxxx

EOF

exit 1
}

# -------- variables
CREDENTIALS_FILE=~/.oci/idcs_credentials
TOKEN_FILE=/tmp/idcs_auth_token.tmp
TMP_JSON_FILE=/tmp/tmp_request_body.json
MAX_OBJECTS=200

# -------- functions
fatal_error()
{
  error_number=$1

  case $error_number in 
  2)  echo "ERROR 2: unsupported operating system $OS" >&2
      ;;
  3)  echo "ERROR 3: credentials file $CREDENTIALS_FILE not found !" >&2
      echo "         Run the script with set_credentials operation" >&2
      ;;
  4)  echo "ERROR 4: syntax error in credentials file $CREDENTIALS_FILE" >&2
      ;; 
  5)  echo "ERROR 5: user name not found !" >&2
      ;; 
  6)  echo "ERROR 6: group name not found !" >&2
      ;; 
  99) echo "ERROR 99: jq not installed !" >&2
      ;;
  esac
  exit $error_number
}

# ---- create credentials file
set_credentials()
{
  if [ $# -ne 3 ]; then usage; fi

  idcs_instance=$1
  client_id=$2
  client_secret=$3

  OS=`uname -s``
`
  case $OS in
  # MacOS
  "Darwin")  base64code=`echo -n "$client_id:$client_secret" | base64`
             ;;
  "Linux")   base64code=`echo -n "$client_id:$client_secret" | base64 -w 0`
             ;;
  *)         fatal_error 2 ;;
  esac

  echo "IDCS_INSTANCE=$idcs_instance" > $CREDENTIALS_FILE
  echo "BASE64CODE=$base64code" >> $CREDENTIALS_FILE
}

# ---- get auth_token
get_auth_token()
{
  curl -i -X POST \
     -H "Authorization: Basic $BASE64CODE" \
     -H "Content-Type: application/x-www-form-urlencoded;charset=UTF-8" \
      $IDCS_END_POINT/oauth2/v1/token \
     -d "grant_type=client_credentials&scope=urn:opc:idm:__myscopes__" 2>/dev/null | tail -1 | jq -r '.access_token' > $TOKEN_FILE
}

# ---- initialize script
init()
{
  mkdir -p `dirname $CREDENTIALS_FILE`
  if [ ! -f $CREDENTIALS_FILE ]; then fatal_error 3; fi

  IDCS_INSTANCE=`grep IDCS_INSTANCE $CREDENTIALS_FILE | awk -F'=' '{ print $2 }'`
  BASE64CODE=`grep BASE64CODE $CREDENTIALS_FILE | awk -F'=' '{ print $2 }'`

  IDCS_END_POINT=https://${IDCS_INSTANCE}.identity.oraclecloud.com

  if [ "$BASE64CODE" == "" ] || [ "$IDCS_INSTANCE" == "" ]; then fatal_error 4; fi

  # get a new Authentication token  
  get_auth_token
}

# ---- list users
list_users()
{
  if [ $# -ne 0 ]; then usage; fi

  echo -e "=========== USER IDS ===========\t=========== USER NAMES ==========="
  # by default, pagination=50 users, use MAX_OBJECT here
  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      "$IDCS_END_POINT/admin/v1/Users?attributes=userName&count=$MAX_OBJECTS" 2>/dev/null | tail -1 | jq -r '.Resources[]? | "\(.id)\t\(.userName)"' | sort -k2

}

# ---- list groups
list_groups()
{
  if [ $# -ne 0 ]; then usage; fi

  echo -e "========== GROUP IDS ===========\t=========== GROUP NAMES ==========="
  # by default, pagination=50 groups, use MAX_OBJECT here
  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      "$IDCS_END_POINT/admin/v1/Groups?attributes=displayName&count=$MAX_OBJECTS" 2>/dev/null | tail -1 | jq -r '.Resources[]? | "\(.id)\t\(.displayName)"' | sort -k2
}

# ---- list users in a group
list_users_in_group()
{
  if [ $# -ne 1 ]; then usage; fi

  GROUPNAME=$1
  MYGROUP_ID=`get_groupid_from_name "$GROUPNAME"`
  if [ "$MYGROUP_ID" == "" ]; then exit 6; fi

  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Groups/$MYGROUP_ID?attributes=members 2>/dev/null | tail -1 | jq -r ".members[]?.name"
}

# ---- list groups assigned to a user
list_groups_of_user()
{
  if [ $# -ne 1 ]; then usage; fi

  USERNAME=$1
  MYUSER_ID=`get_userid_from_name "$USERNAME"`
  if [ "$MYUSER_ID" == "" ]; then exit 5; fi

  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Users/$MYUSER_ID?attributes=groups 2>/dev/null | tail -1 | jq -r ".groups[]?.display"
}

get_userid_from_name()
{
  USERNAME=$1

  TMPID=/tmp/idcs_tmp_id
  
  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Users?count=$MAX_OBJECTS 2>/dev/null | tail -1 | jq --arg U "$USERNAME" '.Resources[] | select(.userName == $U )' | jq -r ".id" > $TMPID
  
  USERID=`cat $TMPID`
  rm -f $TMPID

  if [ "$USERID" == "" ]; then fatal_error 5; fi

  echo $USERID
}

show_user()
{
  if [ $# -ne 1 ]; then usage; fi

  USERNAME=$1
  MYUSER_ID=`get_userid_from_name "$USERNAME"`
  if [ "$MYUSER_ID" == "" ]; then exit 5; fi

  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Users/$MYUSER_ID 2>/dev/null | tail -1 | jq "."
}

# ---- show group details
get_groupid_from_name()
{
  GROUPNAME=$1

  TMPID=/tmp/idcs_tmp_id
  
  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Groups?count=$MAX_OBJECTS 2>/dev/null | tail -1 | jq --arg G "$GROUPNAME" '.Resources[] | select(.displayName == $G )' | jq -r ".id" > $TMPID
  
  GROUPID=`cat $TMPID`
  rm -f $TMPID

  if [ "$GROUPID" == "" ]; then fatal_error 6; fi

  echo $GROUPID
}

show_group()
{
  if [ $# -ne 1 ]; then usage; fi

  GROUPNAME=$1
  MYGROUP_ID=`get_groupid_from_name "$GROUPNAME"`
  if [ "$MYGROUP_ID" == "" ]; then exit 6; fi

  curl -i -X GET \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Groups/$MYGROUP_ID 2>/dev/null | tail -1 | jq "."
}

# ---- add a new user
add_user()
{
  if [ $# -ne 4 ]; then usage; fi

  USERNAME=$1
  FIRST_NAME=$2
  LAST_NAME=$3
  EMAIL_ADDRESS=$4

  cat > $TMP_JSON_FILE << EOF
{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "$USERNAME",
  "name": {
    "familyName": "$LAST_NAME",
    "givenName": "$FIRST_NAME"
  },
  "emails": [{
    "value": "$EMAIL_ADDRESS",
    "type": "work",
    "primary": true
  }]
}
EOF

  curl -i -X POST \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      -d "`cat $TMP_JSON_FILE`" \
      $IDCS_END_POINT/admin/v1/Users 2>/dev/null | tail -1 | jq "."

  rm -f $TMP_JSON_FILE
}

# ---- add a new group
add_group()
{
  if [ $# -ne 2 ]; then usage; fi

  GROUP_NAME=$1
  GROUP_DESCRIPTION=$2

  cat > $TMP_JSON_FILE << EOF
{
    "displayName": "$GROUP_NAME",
    "urn:ietf:params:scim:schemas:oracle:idcs:extension:group:Group": {
        "creationMechanism": "api",
        "description": "$GROUP_DESCRIPTION"
    },
    "schemas": [
        "urn:ietf:params:scim:schemas:core:2.0:Group",
        "urn:ietf:params:scim:schemas:oracle:idcs:extension:group:Group"
    ]
}
EOF

  curl -i -X POST \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      -d "`cat $TMP_JSON_FILE`" \
      $IDCS_END_POINT/admin/v1/Groups 2>/dev/null | tail -1 | jq "."

  rm -f $TMP_JSON_FILE
}

# ---- add a user to a group
add_user_to_group()
{
  if [ $# -ne 2 ]; then usage; fi

  USERNAME=$1
  GROUPNAME=$2

  MYUSER_ID=`get_userid_from_name "$USERNAME"`
  if [ "$MYUSER_ID" == "" ]; then exit 5; fi

  MYGROUP_ID=`get_groupid_from_name "$GROUPNAME"`
  if [ "$MYGROUP_ID" == "" ]; then exit 6; fi

  cat > $TMP_JSON_FILE << EOF
{
  "schemas": [
    "urn:ietf:params:scim:api:messages:2.0:PatchOp"
  ],
  "Operations": [
    {
      "op": "add",
      "path": "members",
      "value": [
        {
          "value": "$MYUSER_ID",
          "type": "User"
        }
      ]
    }
  ]
}
EOF

  curl -i -X PATCH \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      -d "`cat $TMP_JSON_FILE`" \
      $IDCS_END_POINT/admin/v1/Groups/$MYGROUP_ID 2>/dev/null | tail -1 | jq "."

  rm -f $TMP_JSON_FILE
}

# ---- remove a user from a group
remove_user_from_group()
{
  if [ $# -ne 2 ]; then usage; fi

  USERNAME=$1
  GROUPNAME=$2

  MYUSER_ID=`get_userid_from_name "$USERNAME"`
  if [ "$MYUSER_ID" == "" ]; then exit 5; fi

  MYGROUP_ID=`get_groupid_from_name "$GROUPNAME"`
  if [ "$MYGROUP_ID" == "" ]; then exit 6; fi
  
  cat > $TMP_JSON_FILE << EOF
{
  "schemas": [
    "urn:ietf:params:scim:api:messages:2.0:PatchOp"
  ],
  "Operations": [
    {
      "op": "remove",
      "path": "members",
      "value": [
        {
          "value": "$MYUSER_ID",
          "type": "User"
        }
      ]
    }
  ]
}
EOF

  curl -i -X PATCH \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      -d "`cat $TMP_JSON_FILE`" \
      $IDCS_END_POINT/admin/v1/Groups/$MYGROUP_ID 2>/dev/null | tail -1 | jq "."

  rm -f $TMP_JSON_FILE
}

# ---- deactivate a user
deactivate_user()
{
  if [ $# -ne 1 ]; then usage; fi

  USERNAME=$1
  MYUSER_ID=`get_userid_from_name "$USERNAME"`
  if [ "$MYUSER_ID" == "" ]; then exit 5; fi

  cat > $TMP_JSON_FILE << EOF
{
  "active": false,
  "schemas": [
    "urn:ietf:params:scim:schemas:oracle:idcs:UserStatusChanger"
  ]
}
EOF

  curl -X PUT \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      -d "`cat $TMP_JSON_FILE`" \
      $IDCS_END_POINT/admin/v1/UserStatusChanger/$MYUSER_ID 2>/dev/null | tail -1 | jq "."

  rm -f $TMP_JSON_FILE
}

# ---- activate a user
activate_user()
{
  if [ $# -ne 1 ]; then usage; fi

  USERNAME=$1
  MYUSER_ID=`get_userid_from_name "$USERNAME"`
  if [ "$MYUSER_ID" == "" ]; then exit 5; fi

  cat > $TMP_JSON_FILE << EOF
{
  "active": true,
  "schemas": [
    "urn:ietf:params:scim:schemas:oracle:idcs:UserStatusChanger"
  ]
}
EOF

  curl -X PUT \
      -H "Content-Type:application/scim+json" \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      -d "`cat $TMP_JSON_FILE`" \
      $IDCS_END_POINT/admin/v1/UserStatusChanger/$MYUSER_ID 2>/dev/null | tail -1 | jq "."

  rm -f $TMP_JSON_FILE
}

# ---- delete a user
delete_user()
{
  if [ $# -ne 1 ] && [ $# -ne 2 ]; then usage; fi

  USERNAME=$1
  CONFIRM=$2

  MYUSER_ID=`get_userid_from_name "$USERNAME"`
  if [ "$MYUSER_ID" == "" ]; then exit 5; fi

  if [ "$CONFIRM" != "--confirm" ]; then 
    printf "Do you confirm deletion of user $USERNAME (Id $MYUSER_ID) ? (y/n): "
    read response
    if [ "$response" != "y" ]; then echo "User deletion cancelled !"; return; fi
  fi

  curl -X DELETE \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Users/$MYUSER_ID 2>/dev/null | tail -1 | jq "."

  echo "User $USERNAME (Id $MYUSER_ID) deleted !"
}

# ---- delete a group
delete_group()
{
  if [ $# -ne 1 ] && [ $# -ne 2 ]; then usage; fi

  GROUPNAME=$1
  CONFIRM=$2

  MYGROUP_ID=`get_groupid_from_name "$GROUPNAME"`
  if [ "$MYGROUP_ID" == "" ]; then exit 6; fi

  if [ "$CONFIRM" != "--confirm" ]; then 
    printf "Do you confirm deletion of group $GROUPNAME (Id $MYGROUP_ID) ? (y/n): "
    read response
    if [ "$response" != "y" ]; then echo "Group deletion cancelled !"; return; fi
  fi

  curl -X DELETE \
      -H "Authorization: Bearer `cat $TOKEN_FILE`" \
      $IDCS_END_POINT/admin/v1/Groups/$MYGROUP_ID 2>/dev/null | tail -1 | jq "."

  echo "Group $GROUPNAME (Id $MYGROUP_ID) deleted !"
}

# -------- main

# -- Check if jq is installed
which jq > /dev/null 2>&1
if [ $? -ne 0 ]; then fatal_error 99; fi

# -- 
operation=$1
shift

case "$operation" in 
"set_credentials")        set_credentials "$@" ;; 
"list_users")             init; list_users "$@" ;;
"list_groups")            init; list_groups "$@" ;;
"list_users_in_group")    init; list_users_in_group "$@" ;;
"list_groups_of_user")    init; list_groups_of_user "$@" ;;
"show_user")              init; show_user "$@" ;;
"show_group")             init; show_group "$@" ;;
"add_user")               init; add_user "$@" ;;
"add_group")              init; add_group "$@" ;;
"add_user_to_group")      init; add_user_to_group "$@" ;;
"remove_user_from_group") init; remove_user_from_group "$@" ;;
"deactivate_user")        init; deactivate_user "$@" ;;
"activate_user")          init; activate_user "$@" ;;
"delete_user")            init; delete_user "$@" ;;
"delete_group")           init; delete_group "$@" ;;
*)                        usage;;
esac

exit 0
