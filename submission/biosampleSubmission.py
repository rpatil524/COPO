__author__ = 'minottoa'
__date__ = '19 May 2020'

import os
import glob
import shutil
import ftplib
import ntpath
import pexpect
import subprocess
import pandas as pd
from lxml import etree
from bson import ObjectId
from datetime import datetime
from tools import resolve_env
from dal import cursor_to_list
import dal.mongo_util as mutil
from contextlib import closing
from django.conf import settings
from submission.helpers import generic_helper as ghlper
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
from submission.helpers.ena_helper import SubmissionHelper
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.lookup.copo_lookup_service import COPOLookup
from web.apps.web_copo.lookup.lookup import SRA_SUBMISSION_TEMPLATE, SRA_EXPERIMENT_TEMPLATE, SRA_RUN_TEMPLATE, \
    SRA_PROJECT_TEMPLATE, SRA_SAMPLE_TEMPLATE, \
    SRA_SUBMISSION_MODIFY_TEMPLATE, ENA_CLI #####
import requests
from requests.auth import HTTPBasicAuth
import json
import pymongo

#REPOSITORIES = settings.REPOSITORIES
#BASE_DIR = settings.BASE_DIR

"""
see: https://www.ebi.ac.uk/biosamples/docs/references/api/submit
"""

#REFRESH_THRESHOLD = 5 * 3600  # in hours, time to reset a potentially staled task to pending


#json header is Accept: application/json
#GET to retrive resource
#POST to create resources
#PUT to entirely replace resources
#OPTIONS to determine which verbs can be used for a resource
#HEAD returns whether a resource is available
#PATCH used to add structured data toa already existing samples

#######is there a function for this somewhere?
#myclient =  pymongo.MongoClient("mongodb://" + resolve_env.get_env('MONGO_HOST') + ":" + resolve_env.get_env('MONGO_PORT'))
#mydb = myclient[resolve_env.get_env('MONGO_DB')]




########## move root api url in env
#api_auth_url = 'https://api.aai.ebi.ac.uk/auth'
api_auth_url = 'https://explore.api.aai.ebi.ac.uk/auth'
#submission_api_root = 'https://submission.ebi.ac.uk/api/'
submission_api_root = 'https://submission-test.ebi.ac.uk/api'
r =  requests.get( api_auth_url, auth=HTTPBasicAuth(resolve_env.get_env('BIOSAMPLES_TEST_USER'), resolve_env.get_env('BIOSAMPLES_TEST_PWD')))
print(resolve_env.get_env('BIOSAMPLES_TEST_USER'), resolve_env.get_env('BIOSAMPLES_TEST_PWD'))
token = r.text

headers = { "Accept" : "application/hal+json", "Authorization" : "Bearer "+token}
r2 = requests.get( submission_api_root, headers=headers)
teams_endpoint = r2.json()['_links']['userTeams']['href']

r3 = requests.get( teams_endpoint, headers=headers)

dtol_index = next((i for i, item in enumerate(r3.json()['_embedded']['teams']) if item["name"] == "subs.test-team-81"), None) ######the name is different in prod, set in env variables
assert dtol_index is not None
copo_submission_endpoint = r3.json()['_embedded']['teams'][dtol_index]['_links']['submissions:create']['href']

headers_post = headers.copy()
headers_post[ "Content-Type" ] = "application/json;charset=UTF-8"
#submitting empty document - can add name here -
r4 = requests.post( copo_submission_endpoint, headers = headers, json={})

# add content to submission
submission_contents_url = r4.json()['_links']['contents']['href']
r5 =  requests.get( submission_contents_url, headers = headers)
samples_create_url = r5.json()['_links']['samples:create']['href']

with open("/usr/users/TSL_20/minottoa/copotestfiles/biosampleschema.json") as json_file: ####grab this from mongo later - add alias to be the same as name'
   data=json.load(json_file)

datasubmission = requests.post( samples_create_url, headers = headers_post, json = data)

