#!/bin/bash

# generate OCI API key pair
if [ $# -ne 1 ]; then echo "Usage: $0 key_name"; exit 1; fi

myname=$1

# ---- API key pair (will create files apikey.pem and apikey_public.pem)
# ---- see doc on https://docs.cloud.oracle.com/iaas/Content/API/Concepts/apisigningkey.htm
openssl genrsa -out ./apikey_${myname}.pem 2048
chmod 600 ./apikey_${myname}.pem
openssl rsa -pubout -in ./apikey_${myname}.pem -out ./apikey_${myname}_public.pem 

openssl rsa -pubout -outform DER -in ./apikey_${myname}.pem | openssl md5 -c > ./apikey_${myname}_fingerprint
