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
from dal.copo_da import Sample
from bson.json_util import dumps, loads
from numpy import datetime64


class DtolSpreadsheet:
    # list of strings in spreadsheet to be considered NaN by Pandas....N.B. "NA" is allowed
    na_vals = ['', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A',
               'NULL', 'NaN', 'n/a', 'nan', 'null']
    na_vals = ['N/A']

    validation_msg_missing_data = "Missing data detected in column <strong>%s</strong>. All required fields must have a value. There must be no empty rows. Values of 'NA' and 'none' are allowed."

    fields = ""

    def __init__(self, file):
        self.file = file
        self.req = ThreadLocal.get_current_request()
        self.profile_id = self.req.session.get("profile_id", None)

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
        for index, row in self.data.iterrows():
            r = list(row)
            for idx, x in enumerate(r):
                if x is math.nan:
                    r[idx] = ""
            sample_data.append(r)
        self.req.session["sample_data"] = sample_data

        notify_sample_status(profile_id=self.profile_id, msg=sample_data, action="make_table", html_id="sample_table")

    def save_records(self):
        sample_data = self.req.session["sample_data"]
        Sample(profile_id=self.profile_id).save_record(auto_fields={}, **sample_data)


    def get_biosampleId(self):
        raise NotImplementedError()