# Created by fshaw at 03/04/2020
from django.http import HttpResponse
import pandas, json
from web.apps.web_copo.lookup import lookup
import jsonpath_rw_ext as jp
from submission.helpers.generic_helper import notify_sample_status
from django_tools.middlewares import ThreadLocal
from asgiref.sync import async_to_sync
import math
import time
from dal.copo_da import Sample, Profile
from bson.json_util import dumps, loads
from numpy import datetime64
from api.utils import map_to_dict
from submission import enareadSubmission
from lxml import etree
import xml.etree.ElementTree as ET
from web.apps.web_copo.lookup.lookup import SRA_SUBMISSION_TEMPLATE, SRA_EXPERIMENT_TEMPLATE, SRA_RUN_TEMPLATE, \
    SRA_PROJECT_TEMPLATE, SRA_SAMPLE_TEMPLATE, \
    SRA_SUBMISSION_MODIFY_TEMPLATE, ENA_CLI
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from datetime import datetime
from submission.helpers.ena_helper import SubmissionHelper
from tools import resolve_env
import subprocess






class DtolSpreadsheet:


    # list of strings in spreadsheet to be considered NaN by Pandas....N.B. "NA" is allowed
    na_vals = ['', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A',
               'NULL', 'NaN', 'n/a', 'nan', 'null']
    na_vals = ['N/A']

    exclude_from_sample_xml = [] #list of keys that shouldn't end up in the sample.xml file

    validation_msg_missing_data = "Missing data detected in column <strong>%s</strong>. All required fields must have a value. There must be no empty rows. Values of 'NA' and 'none' are allowed."

    fields = ""

    sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())


    def __init__(self, file=None):
        self.req = ThreadLocal.get_current_request()
        self.profile_id = self.req.session.get("profile_id", None)
        # if a file is passed in, then this is the first time we have seen the spreadsheet,
        # if not then we are looking at creating samples having previously validated
        if file:
            self.file = file
        else:
            self.sample_data = self.req.session["sample_data"]

        self.ena_service = resolve_env.get_env('ENA_SERVICE')
        self.pass_word = resolve_env.get_env('WEBIN_USER_PASSWORD')
        self.user_token = resolve_env.get_env('WEBIN_USER').split("@")[0]

    def loadCsv(file):
        raise NotImplementedError

    def loadExcel(self):

        if self.profile_id is not None:
            notify_sample_status(profile_id=self.profile_id, msg="Loading..", action="info", html_id="sample_info")
            try:
                # read excel and convert all to string
                self.data = pandas.read_excel(self.file, keep_default_na=False, na_values=self.na_vals)
                self.data = self.data.astype(str)
            except :
                # if error notify via web socket
                notify_sample_status(profile_id=self.profile_id, msg="Unable to load file.", action="info",
                                     html_id="sample_info")
                return False

    def validate(self):
        # need to load validation field set
        with open(lookup.WIZARD_FILES["sample_details"]) as json_data:

            try:
                # get definitive list of DTOL fields from schema
                s = json.load(json_data)
                self.fields = jp.match('$.properties[?(@.specifications[*] == "dtol" & @.required=="true")].versions[0]', s)
                columns = list(self.data.columns)
                # check required fields are present in spreadsheet
                for item in self.fields:
                    notify_sample_status(profile_id=self.profile_id, msg="Checking - " + item,
                                         action="info",
                                         html_id="sample_info")
                    print(item)
                    #time.sleep(0.1)
                    if item not in columns:
                        # invalid or missing field, inform user and return false
                        notify_sample_status(profile_id=self.profile_id, msg="Field not found - " + item,
                                             action="info",
                                             html_id="sample_info")
                        return False
                    # if we have a required field and it has null data
                    if self.data[item].isnull().values.any():
                        # we have missing data in required cells
                        notify_sample_status(profile_id=self.profile_id,
                                             msg=(self.validation_msg_missing_data % item),
                                             action="info",
                                             html_id="sample_info")
                        return False
            except Exception as e:
                print(e)
                notify_sample_status(profile_id=self.profile_id, msg="Server Error - " + str(e), action="info",
                                     html_id="sample_info")
                return False

            # if we get here we have a valid spreadsheet
            notify_sample_status(profile_id=self.profile_id, msg="Spreadsheet is Valid", action="info",
                                 html_id="sample_info")
            notify_sample_status(profile_id=self.profile_id, msg="", action="close", html_id="upload_controls")
            notify_sample_status(profile_id=self.profile_id, msg="", action="make_valid", html_id="sample_info")

            return True

    def collect(self):

        sample_data = []
        headers = list()
        for col in list(self.data.columns):
            headers.append(col)
        sample_data.append(headers)
        for index, row in self.data.iterrows():
            r = list(row)
            for idx, x in enumerate(r):
                if x is math.nan:
                    r[idx] = ""
            sample_data.append(r)
        self.req.session["sample_data"] = sample_data

        notify_sample_status(profile_id=self.profile_id, msg=sample_data, action="make_table", html_id="sample_table")

    def save_records(self):
        sample_data = self.sample_data


        for p in range(1, len(sample_data)):

            to_mongo = (map_to_dict(sample_data[0], sample_data[p]))
            notify_sample_status(profile_id=self.profile_id, msg="Creating Sample with ID: " + to_mongo["SPECIMEN_ID"], action="info",
                                 html_id="sample_info")
            obj_id = Sample(profile_id=self.profile_id).save_record(auto_fields={}, **to_mongo)
            print("sample created: " + str(p))
            #obj = Sample(profile_id=self.profile_id).get_record(obj_id['_id']) #would retrieve same as 133

            self.build_sample_xml(obj_id)
            object_id = str(obj_id['_id'])
            #print(object_id)
            self.build_validate_xml(object_id)
            self.build_submission_xml(object_id)

            # register project to the ENA service
            curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                       + ' -F "SUBMISSION=@' \
                       + "submission.xml" \
                       + '" -F "SAMPLE=@' \
                       + "sample.xml" \
                       + '" "' + self.ena_service \
                       + '"'

            try:
                receipt = subprocess.check_output(curl_cmd, shell=True)
                #print(receipt)
            except Exception as e:
                message = 'API call error ' + "Submitting project xml to ENA via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx")
                print(message)

            print(receipt)
            '''if root.get('success') == 'false':
                result['status'] = False
                result['message'] = "Couldn't register STUDY due to the following errors: "
                errors = root.findall('.//ERROR')
                if errors:
                    error_text = str()
                    for e in errors:
                        error_text = error_text + " \n" + e.text
    
                    result['message'] = result['message'] + error_text   '''
                
            # retrieve id and update record
            self.get_biosampleId(receipt, object_id)


            #print(sample_id)

            ####retrieve id and update record
            # obj = self.get_biosampleId(obj_id)


        '''print(sample_data[0])
        for p in range(1, len(sample_data)):

            ######submit sample to ENA
            #print(sample_data[p]) #create XML with this is [0] the header?
            #get sample from mongo
            s = Sample().get_from_profile_id(profile_id=Profile().get_for_user())
            print(s)'''

    def build_sample_xml(self, obj_id):
        # build sample XML
        tree = ET.parse(SRA_SAMPLE_TEMPLATE)
        root = tree.getroot()

        # sample = {'alias' : obj_id['_id']}
        sample_alias = ET.SubElement(root, 'SAMPLE')
        sample_alias.set('alias', str(obj_id['_id']))
        sample_alias.set('center_name', 'EI')   ####mandatory for broker account
        title = '' ######what do i use as a title?
        title_block = ET.SubElement(sample_alias, 'TITLE')
        title_block.text = title
        sample_name = ET.SubElement(sample_alias, 'SAMPLE_NAME')
        taxon_id = ET.SubElement(sample_name, 'TAXON_ID')
        taxon_id.text = obj_id['taxonid']
        sample_attributes = ET.SubElement(sample_alias, 'SAMPLE_ATTRIBUTES')
        ##### for item in obj_id: if item in checklist (or similar according to some criteria).....
        for item in obj_id.items():
            if item[0] not in self.exclude_from_sample_xml: #####this still miss the checklist validation
                sample_attribute = ET.SubElement(sample_attributes, 'SAMPLE_ATTRIBUTE')
                tag = ET.SubElement(sample_attribute, 'TAG')
                tag.text = item[0]
                value = ET.SubElement(sample_attribute, 'VALUE')
                value.text = str(item[1])

        ET.dump(tree)
        tree.write(open("sample.xml", 'w'), encoding='unicode') #overwriting at each run, i don't think we need to keep it

    def build_submission_xml(self, object_id):
        # build submission XML
        tree = ET.parse(SRA_SUBMISSION_TEMPLATE)
        root = tree.getroot()
        #print(root)
        #print(root.tag)
        #print(root.attrib)

        #from toni's code below
        # set submission attributes
        root.set("submission_date", datetime.utcnow().replace(tzinfo=d_utils.simple_utc()).isoformat())

        # set SRA contacts
        contacts = root.find('CONTACTS')

        # set copo sra contacts
        copo_contact = ET.SubElement(contacts, 'CONTACT')
        copo_contact.set("name", self.sra_settings["sra_broker_contact_name"])
        copo_contact.set("inform_on_error", self.sra_settings["sra_broker_inform_on_error"])
        copo_contact.set("inform_on_status", self.sra_settings["sra_broker_inform_on_status"])

        # set user contacts
        sra_map = {"inform_on_error": "SRA Inform On Error", "inform_on_status": "SRA Inform On Status"}
        #submission_helper = SubmissionHelper(submission_id=object_id) #####what is it submission id? #self.submission_id)
        #user_contacts = submission_helper.get_sra_contacts()
        #for k, v in user_contacts.items():
        #    user_sra_roles = [x for x in sra_map.keys() if sra_map[x].lower() in v]
        #    if user_sra_roles:
        #        user_contact = ET.SubElement(contacts, 'CONTACT')
        #        user_contact.set("name", ' '.join(k[1:]))
        #        for role in user_sra_roles:
        #            user_contact.set(role, k[0])
        ET.dump(tree)
        tree.write(open("submission.xml", 'w'), encoding='unicode')  # overwriting at each run, i don't think we need to keep it

    def build_validate_xml(self, object_id):
        # build submission XML
        tree = ET.parse(SRA_SUBMISSION_TEMPLATE)
        root = tree.getroot()
        # set submission attributes
        root.set("submission_date", datetime.utcnow().replace(tzinfo=d_utils.simple_utc()).isoformat())
        # set SRA contacts
        contacts = root.find('CONTACTS')
        # set copo sra contacts
        copo_contact = ET.SubElement(contacts, 'CONTACT')
        copo_contact.set("name", self.sra_settings["sra_broker_contact_name"])
        copo_contact.set("inform_on_error", self.sra_settings["sra_broker_inform_on_error"])
        copo_contact.set("inform_on_status", self.sra_settings["sra_broker_inform_on_status"])
        # set user contacts
        sra_map = {"inform_on_error": "SRA Inform On Error", "inform_on_status": "SRA Inform On Status"}
        #change ADD to VALIDATE
        root.find('ACTIONS').find('ACTION').clear()
        action = root.find('ACTIONS').find('ACTION')
        ET.SubElement(action, 'VALIDATE')
        ET.dump(tree)
        tree.write(open("submission_validate.xml", 'w'), encoding='unicode')  # overwriting at each run, i don't think we need to keep it

    def get_biosampleId(self, receipt, sample_id): #####todo: put this in a thread
        #raise NotImplementedError()
        tree = ET.fromstring(receipt)
        sampleinreceipt = tree.find('SAMPLE')
        sra_accession = sampleinreceipt.get('accession')
        print(sra_accession)
        biosample_accession = sampleinreceipt.find('EXT_ID').get('accession')
        print(biosample_accession)
        submission_accession = tree.find('SUBMISSION').get('accession')
        print(submission_accession)
        #s = Sample().get_record(sample_id)
        #print(s)
        Sample().add_accession(biosample_accession, sra_accession, submission_accession, sample_id)
        #s =  Sample().get_record(sample_id)
        #print(s)