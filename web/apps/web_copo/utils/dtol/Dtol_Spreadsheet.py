# Created by fshaw at 03/04/2020
import math
import os
from os.path import join, isfile
from pathlib import Path
from shutil import rmtree
import json
import jsonpath_rw_ext as jp
import pandas
from django_tools.middlewares import ThreadLocal
from django.core.files.storage import default_storage
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from api.utils import map_to_dict
from dal.copo_da import Sample, DataFile
from submission.helpers.generic_helper import notify_sample_status
from web.apps.web_copo.lookup import dtol_lookups as  lookup
from web.apps.web_copo.lookup import lookup as lk
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
from django.conf import settings
import uuid
import re
import numpy as np


class DtolSpreadsheet:
    # list of strings in spreadsheet to be considered NaN by Pandas....N.B. "NA" is allowed
    na_vals = ['#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A',
               'NULL', 'NaN', 'n/a', 'nan', 'null']
    # na_vals = ['NOT COLLECTED', 'NOT PROVIDED', 'NOT APPLICABLE']
    # fields which are allowed to be empty should be here....if not and they are parsed whilst empty, they will produce NAN in pandas
    # allowed_empty = ["ELEVATION", "DEPTH", "TAXON_REMARKS", "INFRASPECIFIC_EPITHET", "CULTURE_OR_STRAIN_ID", "SYMBIONT", "PRESERVATIVE_SOLUTION", "RELATIONSHIP"]
    validation_msg_missing_data = "Missing data detected in column <strong>%s</strong> at row <strong>%s</strong>. All required fields must have a value. There must be no empty rows. Values of <strong>{allowed}</strong> are allowed.".format(
        allowed=str(na_vals))
    validation_msg_invalid_data = "Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row <strong>%s</strong>. Allowed values are <strong>%s</strong>"
    validation_msg_invalid_list = "Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row <strong>%s</strong>. If this is a location, start with the Country, adding more specific details separated with '|'. See list of allowed Country entries at <a href='https://www.ebi.ac.uk/ena/browser/view/ERC000053'>https://www.ebi.ac.uk/ena/browser/view/ERC000053</a>"
    fields = ""

    sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())

    def __init__(self, file=None):
        self.req = ThreadLocal.get_current_request()
        self.profile_id = self.req.session.get("profile_id", None)
        sample_images = Path(settings.MEDIA_ROOT) / "sample_images"
        display_images = Path(settings.MEDIA_ROOT) / "img" / "sample_images"
        self.these_images = sample_images / self.profile_id
        self.display_images = display_images / self.profile_id
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
                '''
                for column in self.allowed_empty:
                    self.data[column] = self.data[column].fillna("")
                '''
                self.data = self.data.apply(lambda x: x.astype(str).str.upper())
            except:
                # if error notify via web socket
                notify_sample_status(profile_id=self.profile_id, msg="Unable to load file.", action="info",
                                     html_id="sample_info")
                return False

    def validate(self):
        flag=True
        errors = []
        # need to load validation field set
        with open(lk.WIZARD_FILES["sample_details"]) as json_data:

            try:
                # get definitive list of mandatory DTOL fields from schema
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
                        errors.append("Field not found - " + item)
                        flag = False
                        # if we have a required fields, check that there are no missing values
                    for header, cells in self.data.iteritems():
                        # here we need to check if there are not missing values in its cells
                        if header in self.fields:
                            cellcount = 0
                            for c in cells:
                                cellcount += 1
                                if not c:
                                    # we have missing data in required cells
                                    errors.append(self.validation_msg_missing_data % (
                                                             header, str(cellcount + 1)))
                                    flag = False

                # get list of DTOL fields from schemas
                self.fields = jp.match(
                    '$.properties[?(@.specifications[*] == "dtol")].versions[0]', s)
                for header, cells in self.data.iteritems():
                    if header in self.fields:

                        # check if there is an enum for this header
                        allowed_vals = lookup.DTOL_ENUMS.get(header, "")

                        # check if there's a regex rule for the header and exceptional handling
                        if lookup.DTOL_RULES.get(header, ""):
                            regex_rule = lookup.DTOL_RULES[header].get("ena_regex", "")
                            regex_human_readable = lookup.DTOL_RULES[header].get("human_readable", "")
                        else:
                            regex_rule = ""
                        cellcount = 0
                        for c in cells:
                            cellcount += 1

                            c_value = c
                            if allowed_vals:
                                if header == "COLLECTION_LOCATION":
                                    # special check for COLLETION_LOCATION as this needs invalid list error for feedback
                                    c_value = str(c).split('|')[0].strip()
                                    location_2part = str(c).split('|')[1:]
                                    if c_value not in allowed_vals or not  location_2part:
                                        errors.append(self.validation_msg_invalid_list % (
                                                                 c_value, header, str(cellcount + 1)))
                                        flag = False
                                elif c_value not in allowed_vals:
                                    # check value is in allowed enum
                                    errors.append(self.validation_msg_invalid_data % (
                                                             c_value, header, str(cellcount + 1), allowed_vals))
                                    flag = False
                            if regex_rule:
                                # handle any regular expressions provided for valiation

                                if c and not re.match(regex_rule, c):
                                    errors.append(self.validation_msg_invalid_data % (
                                                             c, header, str(cellcount + 1), regex_human_readable))
                                    flag = False
                            elif header == "SERIES":
                                try:
                                    int(c)
                                except ValueError:
                                    errors.append(self.validation_msg_invalid_data % (
                                                             c, header, str(cellcount + 1), "integers"))
                                    flag = False

                if not flag:
                    notify_sample_status(profile_id=self.profile_id,
                                         msg="<br>".join(errors),
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

    def check_image_names(self, files):
        # compare list of sample names with specimen ids already uploaded
        samples = self.sample_data
        # get list of specimen_ids in sample
        specimen_id_column_index = 0
        output = list()
        for num, col_name in enumerate(samples[0]):
            if col_name == "SPECIMEN_ID":
                specimen_id_column_index = num
                break
        if os.path.isdir(self.these_images):
            rmtree(self.these_images)
        self.these_images.mkdir(parents=True)

        write_path = Path(self.these_images)
        display_write_path = Path(self.display_images)
        for f in files:
            file = files[f]

            file_path = write_path / file.name
            # write full sized image to large storage
            file_path = Path(settings.MEDIA_ROOT) / "sample_images" / self.profile_id / file.name
            with default_storage.open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            filename = os.path.splitext(file.name)[0].upper()
            # now iterate through samples data to see if there is a match between specimen_id and image name
        image_path = Path(settings.MEDIA_ROOT) / "sample_images" / self.profile_id
        for num, sample in enumerate(samples):
            found = False
            if num != 0:
                specimen_id = sample[specimen_id_column_index].upper()

                file_list = [f for f in os.listdir(image_path) if isfile(join(image_path, f))]
                for filename in file_list:
                    if specimen_id in filename.upper():
                        # we have a match
                        p = Path(settings.MEDIA_URL) / "sample_images" / self.profile_id / filename

                        output.append({"file_name": str(p), "specimen_id": sample[specimen_id_column_index]})
                        found = True
                        break
                if not found:
                    output.append({"file_name": "None", "specimen_id": "No Image found for <strong>" + sample[
                        specimen_id_column_index] + "</strong>"})
        # save to session
        request = ThreadLocal.get_current_request()
        request.session["image_specimen_match"] = output
        notify_sample_status(profile_id=self.profile_id, msg=output, action="make_images_table", html_id="images")
        return output

    def collect(self):
        # create table data to show to the frontend from parsed manifest
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
        # store sample data in the session to be used to create mongo objects
        self.req.session["sample_data"] = sample_data
        notify_sample_status(profile_id=self.profile_id, msg=sample_data, action="make_table", html_id="sample_table")

    def save_records(self):
        # create mongo sample objects from info parsed from manifest and saved to session variable
        sample_data = self.sample_data
        manifest_id = str(uuid.uuid4())
        request = ThreadLocal.get_current_request()
        image_data = request.session.get("image_specimen_match", [])
        for p in range(1, len(sample_data)):
            s = (map_to_dict(sample_data[0], sample_data[p]))
            s["sample_type"] = "dtol"
            s["biosample_accession"] = []
            s["manifest_id"] = manifest_id
            s["status"] = "pending"
            notify_sample_status(profile_id=self.profile_id, msg="Creating Sample with ID: " + s["SPECIMEN_ID"],
                                 action="info",
                                 html_id="sample_info")
            sampl = Sample(profile_id=self.profile_id).save_record(auto_fields={}, **s)
            for im in image_data:
                # create matching DataFile object for image is provided
                if s["SPECIMEN_ID"] in im["specimen_id"]:
                    fields = {"file_location": im["file_name"]}
                    df = DataFile().save_record({}, **fields)
                    DataFile().insert_sample_id(df["_id"], sampl["_id"])
                    break;
            Sample().timestamp_dtol_sample_created(sampl["_id"])
            # obj = Sample(profile_id=self.profile_id).get_record(obj_id['_id']) #would retrieve same as 133
