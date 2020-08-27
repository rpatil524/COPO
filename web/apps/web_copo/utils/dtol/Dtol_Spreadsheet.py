# Created by fshaw at 03/04/2020
import math

import json
import jsonpath_rw_ext as jp
import pandas
from django_tools.middlewares import ThreadLocal

import web.apps.web_copo.schemas.utils.data_utils as d_utils
from api.utils import map_to_dict
from dal.copo_da import Sample
from submission.helpers.generic_helper import notify_sample_status
from web.apps.web_copo.lookup import dtol_lookups as  lookup
from web.apps.web_copo.lookup import lookup as lk
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS


class DtolSpreadsheet:
    # list of strings in spreadsheet to be considered NaN by Pandas....N.B. "NA" is allowed
    na_vals = ['', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A',
               'NULL', 'NaN', 'n/a', 'nan', 'null']
    na_vals = ['N/A']

    validation_msg_missing_data = "Missing data detected in column <strong>%s</strong> at row <strong>%s</strong>. All required fields must have a value. There must be no empty rows. Values of 'NA' and 'none' are allowed."
    validation_msg_invalid_data = "Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row <strong>%s</strong>. Allowed values are <strong>%s</strong>"

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


    def loadManifest(self, type):

        if self.profile_id is not None:
            notify_sample_status(profile_id=self.profile_id, msg="Loading..", action="info", html_id="sample_info")
            try:
                # read excel and convert all to string
                if type == "xls":
                    self.data = pandas.read_excel(self.file, keep_default_na=False, na_values=self.na_vals)
                elif type == "csv":
                    self.data = pandas.read_csv(self.file, keep_default_na=False, na_values=self.na_vals)
                self.data = self.data.apply(lambda x: x.astype(str).str.upper())
            except:
                # if error notify via web socket
                notify_sample_status(profile_id=self.profile_id, msg="Unable to load file.", action="info",
                                     html_id="sample_info")
                return False

    def validate(self):
        # need to load validation field set
        with open(lk.WIZARD_FILES["sample_details"]) as json_data:

            try:
                # get definitive list of DTOL fields from schema
                s = json.load(json_data)
                self.fields = jp.match(
                    '$.properties[?(@.specifications[*] == "dtol" & @.required=="true")].versions[0]', s)
                columns = list(self.data.columns)
                # check required fields are present in spreadsheet
                for item in self.fields:
                    notify_sample_status(profile_id=self.profile_id, msg="Checking - " + item,
                                         action="info",
                                         html_id="sample_info")
                    if item not in columns:
                        # invalid or missing field, inform user and return false
                        notify_sample_status(profile_id=self.profile_id, msg="Field not found - " + item,
                                             action="error",
                                             html_id="sample_info")
                        return False
                # if we have a required fields, check that there are no missing values
                for header, cells in self.data.iteritems():
                    # here we need to check if the column is required, and if so, that there are not missinnng values in its cells
                    if header in self.fields:
                        # check if there is an enum for this header
                        allowed_vals = lookup.DTOL_ENUMS.get(header, "")
                        cellcount = 0
                        for c in cells:
                            cellcount += 1

                            # check for missing data in cell
                            if not c:
                                # we have missing data in required cells
                                notify_sample_status(profile_id=self.profile_id,
                                                     msg=(self.validation_msg_missing_data % (header, str(cellcount + 1))),
                                                     action="error",
                                                     html_id="sample_info")
                                return False
                            # check for allowed values in cell
                            if allowed_vals:
                                if c not in allowed_vals:
                                    notify_sample_status(profile_id=self.profile_id,
                                                         msg=(self.validation_msg_invalid_data % (
                                                         c, header, str(cellcount + 1), allowed_vals)),
                                                         action="error",
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
            s = (map_to_dict(sample_data[0], sample_data[p]))
            s["sample_type"] = "dtol"
            s["biosample_accession"] = []
            notify_sample_status(profile_id=self.profile_id, msg="Creating Sample with ID: " + s["SPECIMEN_ID"],
                                 action="info",
                                 html_id="sample_info")
            obj_id = Sample(profile_id=self.profile_id).save_record(auto_fields={}, **s)
            print("sample created: " + str(p))
            # obj = Sample(profile_id=self.profile_id).get_record(obj_id['_id']) #would retrieve same as 133
