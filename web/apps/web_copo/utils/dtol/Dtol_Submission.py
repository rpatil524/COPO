import json
import subprocess
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime

from celery.utils.log import get_task_logger

import web.apps.web_copo.schemas.utils.data_utils as d_utils
from dal.copo_da import Submission, Sample
from submission.helpers.generic_helper import notify_dtol_status
from tools import resolve_env
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS as settings
from web.apps.web_copo.lookup.lookup import SRA_SUBMISSION_TEMPLATE, SRA_SAMPLE_TEMPLATE

with open(settings, "r") as settings_stream:
    sra_settings = json.loads(settings_stream.read())["properties"]

logger = get_task_logger(__name__)

exclude_from_sample_xml = []  # list of keys that shouldn't end up in the sample.xml file
ena_service = resolve_env.get_env('ENA_SERVICE')
pass_word = resolve_env.get_env('WEBIN_USER_PASSWORD')
user_token = resolve_env.get_env('WEBIN_USER').split("@")[0]

submission_id = ""

def process_pending_dtol_samples():
    '''
    method called from celery to initiate transfers to ENA, see celery.py for timings
    :return:
    '''

    # get all pending dtol submissions
    sample_id_list = Submission().get_pending_dtol_samples()
    # send each to ENA for Biosample ids
    for submission in sample_id_list:
        for s_id in submission["dtol_samples"]:
            sam = Sample().get_record(s_id)
            build_xml(sample=sam, sub_id=s_id, p_id=submission["profile_id"])
            # store accessions, remove sample id from bundle and on last removal, set status of submission
            Submission().dtol_sample_processed(sub_id=submission["_id"], sam_id=s_id)


def build_xml(sample, sub_id, p_id):
    notify_dtol_status(msg="Creating Sample: " + sample["collectorSampleName"], action="info",
                         html_id="dtol_sample_info")
    build_sample_xml(sample)
    object_id = str(sample['_id'])
    build_validate_xml(object_id)
    build_submission_xml(object_id)
    notify_dtol_status(msg="Communicating with ENA", action="info",
                         html_id="dtol_sample_info")
    accessions = submit_biosample(object_id, Sample(), sub_id)
    print(accessions)
    if accessions["status"] == "ok":
        msg = "Last Sample Submitted: " + sample["collectorSampleName"] + " - ENA ID: " + accessions["submission_accession"] + " - Biosample ID: " + accessions["biosample_accession"]
        notify_dtol_status(msg=msg, action="info",
                             html_id="dtol_sample_info")
    else:
        msg = "Submission Rejected: " + sample["collectorSampleName"] + "<p>" + accessions["msg"] + "</p>"
        notify_dtol_status(msg=msg, action="info",
                           html_id="dtol_sample_info")


def build_sample_xml(obj_id):
    # build sample XML
    tree = ET.parse(SRA_SAMPLE_TEMPLATE)
    root = tree.getroot()
    sample_alias = ET.SubElement(root, 'SAMPLE')
    sample_alias.set('alias', str(uuid.uuid4()))  # Todo this is for testing only
    sample_alias.set('center_name', 'EarlhamInstitute')  ####mandatory for broker account
    # title = str(obj_id['_id'])  ######for time being using COPO id as title
    title = str(uuid.uuid4())

    title_block = ET.SubElement(sample_alias, 'TITLE')
    title_block.text = title
    sample_name = ET.SubElement(sample_alias, 'SAMPLE_NAME')
    taxon_id = ET.SubElement(sample_name, 'TAXON_ID')
    taxon_id.text = obj_id.get('taxonid', "")
    sample_attributes = ET.SubElement(sample_alias, 'SAMPLE_ATTRIBUTES')
    ##### for item in obj_id: if item in checklist (or similar according to some criteria).....
    for item in obj_id.items():
        if item[0] not in exclude_from_sample_xml:  #####this still miss the checklist validation
            sample_attribute = ET.SubElement(sample_attributes, 'SAMPLE_ATTRIBUTE')
            tag = ET.SubElement(sample_attribute, 'TAG')
            tag.text = item[0]
            value = ET.SubElement(sample_attribute, 'VALUE')
            value.text = str(item[1])

    ET.dump(tree)
    tree.write(open("sample.xml", 'w'),
               encoding='unicode')  # overwriting at each run, i don't think we need to keep it TODO - what if there are multiple calls simultaneously?


def build_submission_xml(object_id):
    # build submission XML
    tree = ET.parse(SRA_SUBMISSION_TEMPLATE)
    root = tree.getroot()
    # from toni's code below
    # set submission attributes
    root.set("submission_date", datetime.utcnow().replace(tzinfo=d_utils.simple_utc()).isoformat())

    # set SRA contacts
    contacts = root.find('CONTACTS')

    # set copo sra contacts
    copo_contact = ET.SubElement(contacts, 'CONTACT')
    copo_contact.set("name", sra_settings["sra_broker_contact_name"])
    copo_contact.set("inform_on_error", sra_settings["sra_broker_inform_on_error"])
    copo_contact.set("inform_on_status", sra_settings["sra_broker_inform_on_status"])
    ET.dump(tree)
    tree.write(open("submission.xml", 'w'),
               encoding='unicode')  # overwriting at each run, i don't think we need to keep it


def build_validate_xml(object_id):
    # TODO do we need this method at all? Its never actually used right?
    # build submission XML
    tree = ET.parse(SRA_SUBMISSION_TEMPLATE)
    root = tree.getroot()
    # set submission attributes
    root.set("submission_date", datetime.utcnow().replace(tzinfo=d_utils.simple_utc()).isoformat())
    # set SRA contacts
    contacts = root.find('CONTACTS')
    # set copo sra contacts
    copo_contact = ET.SubElement(contacts, 'CONTACT')
    copo_contact.set("name", sra_settings["sra_broker_contact_name"])
    copo_contact.set("inform_on_error", sra_settings["sra_broker_inform_on_error"])
    copo_contact.set("inform_on_status", sra_settings["sra_broker_inform_on_status"])
    # set user contacts
    sra_map = {"inform_on_error": "SRA Inform On Error", "inform_on_status": "SRA Inform On Status"}
    # change ADD to VALIDATE
    root.find('ACTIONS').find('ACTION').clear()
    action = root.find('ACTIONS').find('ACTION')
    ET.SubElement(action, 'VALIDATE')
    ET.dump(tree)
    tree.write(open("submission_validate.xml", 'w'),
               encoding='unicode')  # overwriting at each run, i don't think we need to keep it - todo again I think these should have unique id attached, and then file deleted after submission


def submit_biosample(object_id, sampleobj, sub_id):
    # register project to the ENA service using XML files previously created
    curl_cmd = 'curl -u ' + user_token + ':' + pass_word \
               + ' -F "SUBMISSION=@' \
               + "submission.xml" \
               + '" -F "SAMPLE=@' \
               + "sample.xml" \
               + '" "' + ena_service \
               + '"'

    try:
        receipt = subprocess.check_output(curl_cmd, shell=True)
        #print(receipt)
    except Exception as e:
        message = 'API call error ' + "Submitting project xml to ENA via CURL. CURL command is: " + curl_cmd.replace(
            pass_word, "xxxxxx")
        #print(message)

    tree = ET.fromstring(receipt)
    success_status = tree.get('success')
    if success_status == 'false':  ####todo

        #print(receipt)
        msg = tree.find('MESSAGES').findtext('ERROR', default='Undefined error')
        status = {"status": "error","msg": msg}
        # print(status)
        sampleobj.add_rejected_status(status, object_id)

        #print('error')
        return status
    else:
        # retrieve id and update record
        return get_biosampleId(receipt, object_id)


def get_biosampleId(receipt, sample_id):
    # parsing ENA sample accessions from reciept and storing in sample object - todo these should be store in submission object
    tree = ET.fromstring(receipt)
    sampleinreceipt = tree.find('SAMPLE')
    sra_accession = sampleinreceipt.get('accession')
    # print(sra_accession)
    biosample_accession = sampleinreceipt.find('EXT_ID').get('accession')
    # print(biosample_accession)
    submission_accession = tree.find('SUBMISSION').get('accession')
    # print(submission_accession)
    Sample().add_accession(biosample_accession, sra_accession, submission_accession, sample_id)
    accessions = {"sra_accession": sra_accession, "biosample_accession": biosample_accession, "submission_accession": submission_accession, "status": "ok"}
    return accessions