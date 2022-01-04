#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------------------------
# This script lists the candidate responder rules for each detector rule from a backup file
#  
# Note: OCI tenant given by an OCI CLI PROFILE
#
# Author        : Christophe Pauliat
# Platforms     : MacOS / Linux
# prerequisites : - Python 3 with OCI Python SDK installed
#                 - OCI config file configured with profiles
# Versions
#    2021-11-19: Initial Version
#    2022-01-03: use argparse to parse arguments
# --------------------------------------------------------------------------------------------------------------

# -------- import
import sys
import json
import argparse
from pathlib import Path
from operator import itemgetter

# -------- functions
def usage():
    print (f"Usage: {sys.argv[0]} -f input_backup_file.json")
    print ("")
    exit (1)

# -------- main

# -- parse arguments
parser = argparse.ArgumentParser(description = "List Cloud Guard problems in an OCI tenant")
parser.add_argument("-f", "--file", help="backup input file", required=True)
args = parser.parse_args()
    
input_file = args.file

# -- If the backup file does not exist, exit in error 
my_file = Path(input_file)
if not(my_file.is_file()):
    print (f"ERROR: the input backup file {input_file} does not exist or is not readable !")
    exit (3)

# -- Read detailed configuration from backup file
try:
    with open(input_file, 'r') as filein:
        detector_recipe = json.load(filein)
        print (f"Configuration successfully read from backup file {input_file} !")
except OSError as err:
    print (f"ERROR: {err.strerror}")
    exit (3)
except json.decoder.JSONDecodeError as err:
    print (f"ERROR in JSON input file: {err}")
    exit (4)

# -- Display main characteristics of the detector recipe in the backup file
print (f"Detector recipe type               : {detector_recipe['detector']}")
print (f"Number of effective detector rules : {len(detector_recipe['effective_detector_rules'])}")
print ("")

# -- Extract results
max_len_det  = 0
max_len_resp = 0
detector_rules = []
for detector_rule in detector_recipe['effective_detector_rules']:
    candidate_responder_rules = []
    if len(detector_rule['detector_rule_id']) > max_len_det:
        max_len_det = len(detector_rule['detector_rule_id'])
    if detector_rule['candidate_responder_rules'] != None:
        for candidate_responder_rule in detector_rule['candidate_responder_rules']:
            candidate_responder_rules.append(candidate_responder_rule['id'])
            if len(candidate_responder_rule['id']) > max_len_resp:
                max_len_resp = len(candidate_responder_rule['id'])
    detector_rules.append({
        "detector_rule_id" : detector_rule['detector_rule_id'],
        "candidate_responder_rules" : candidate_responder_rules })

# -- Sort results
detector_rules_sorted = sorted(detector_rules, key=itemgetter('detector_rule_id')) 

# -- Display results
header_detector_rule   = "---- DETECTOR RULE ----"
header_responder_rules = "---- CANDIDATE RESPONDER RULES ----"
print (f"{header_detector_rule:{max_len_det}s} : {header_responder_rules}")

for detector_rule in detector_rules_sorted:
    print (f"{detector_rule['detector_rule_id']:{max_len_det}s} : ",end="")
    if detector_rule['candidate_responder_rules'] != None:
        for candidate_responder_rule in detector_rule['candidate_responder_rules']:
            print (f"{candidate_responder_rule:{max_len_resp}s} ",end="")
    print ("")

# -- the end
exit (0)
