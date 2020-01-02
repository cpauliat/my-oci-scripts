#!/bin/bash

# This Bash script generates OCI API key pair as described in documentation
# on https://docs.cloud.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm
# it creates 3 files (private key, public key and fingerprint) in the current directory
#
# Author: christophe.pauliat@oracle.com
# Last update: January 2, 2020

if [ $# -ne 1 ]; then echo "Usage: $0 key_name"; exit 1; fi

myname=$1

openssl genrsa -out ./apikey_${myname}.pem 2048
chmod 600 ./apikey_${myname}.pem
openssl rsa -pubout -in ./apikey_${myname}.pem -out ./apikey_${myname}_public.pem 

openssl rsa -pubout -outform DER -in ./apikey_${myname}.pem | openssl md5 -c > ./apikey_${myname}_fingerprint
