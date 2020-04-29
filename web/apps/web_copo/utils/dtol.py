# Created by fshaw at 03/04/2020
from django.http import HttpResponse
import pandas, json
from web.apps.web_copo.lookup import lookup
import jsonpath_rw_ext as jp
from submission.helpers.generic_helper import notify_sample_status
from django_tools.middlewares import ThreadLocal
from asgiref.sync import async_to_sync


class DtolSpreadsheet:

    def __init__(self, file):
        self.file = file
        req = ThreadLocal.get_current_request()
        self.profile_id = req.session.get("profile_id", None)

    def loadCsv(file):
        raise NotImplementedError

    def loadExcel(self):

        if self.profile_id is not None:
            notify_sample_status(profile_id=self.profile_id, msg="Validating..", action="info", html_id="sample_info")
            try:
                self.data = pandas.read_excel(self.file)
            except pandas.XLRDError as e:
                notify_sample_status(profile_id=self.profile_id, msg="Unable to load file.", action="info",
                                     html_id="sample_info")
                return False

    def validate(self):
        # need to load validation field set
        with open(lookup.WIZARD_FILES["sample_details"]) as json_data:
            fields = ""
            try:
                # get definitive list of DTOL fields
                s = json.load(json_data)
                fields = jp.match('$.properties[?(@.specifications[*] == "dtol" & @.required=="true")].versions', s)
                columns = list(self.data.columns)
                for item in fields:
                    if item[0] not in columns:
                        # invalid or missing field, inform user and return false
                        notify_sample_status(profile_id=self.profile_id, msg="Field not found - " + item[0], action="info",
                                             html_id="sample_info")
                        return False
            except:
                notify_sample_status(profile_id=self.profile_id, msg="Server Error - Try Again", action="info",
                                     html_id="sample_info")
                return False
            # if we get here we have a valid spreadsheet
            notify_sample_status(profile_id=self.profile_id, msg="Spreadsheet is Valid", action="info",
                                 html_id="sample_info")
            notify_sample_status(profile_id=self.profile_id, msg="", action="close", html_id="upload_controls")
            return True

    def parse(self):
        notify_sample_status(profile_id=self.profile_id, msg="Parsing", action="info",
                             html_id="sample_info")

