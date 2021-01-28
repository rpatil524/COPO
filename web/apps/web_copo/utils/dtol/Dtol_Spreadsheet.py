# Created by fshaw at 03/04/2020
import datetime
import json
import math
import os
import re
import uuid
from os.path import join, isfile
from pathlib import Path
from shutil import rmtree
from urllib.error import HTTPError
import subprocess

import jsonpath_rw_ext as jp
import pandas
from Bio import Entrez
from django.conf import settings
from django.core.files.storage import default_storage
from django_tools.middlewares import ThreadLocal

import web.apps.web_copo.schemas.utils.data_utils as d_utils
from api.utils import map_to_dict
from dal.copo_da import Sample, DataFile, Profile
from submission.helpers.generic_helper import notify_dtol_status
from web.apps.web_copo.copo_email import CopoEmail
from web.apps.web_copo.lookup import dtol_lookups as lookup
from web.apps.web_copo.lookup import lookup as lk
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
from .Dtol_Helpers import make_tax_from_sample


class DtolSpreadsheet:
    # list of strings in spreadsheet to be considered NaN by Pandas....N.B. "NA" is allowed
    na_vals = ['#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN', '<NA>', 'N/A',
               'NULL', 'NaN', 'n/a', 'nan']
    blank_vals = ['NOT_COLLECTED', 'NOT_PROVIDED', 'NOT_APPLICABLE']
    symbiont_vals = ["TARGET", "SYMBIONT"]
    validation_msg_missing_data = "Missing data detected in column <strong>%s</strong> at row <strong>%s</strong>. All required fields must have a value. There must be no empty rows. Values of <strong>{allowed}</strong> are allowed.".format(
        allowed=str(blank_vals))
    validation_msg_missing_symbiont = "Missing data detected in column <strong>%s</strong> at row <strong>%s</strong>. All required fields must have a value. There must be no empty rows. Values of <strong>{allowed}</strong> are allowed.".format(
        allowed=str(symbiont_vals))
    validation_msg_invalid_data = "Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row <strong>%s</strong>. Allowed values are <strong>%s</strong>"
    validation_msg_invalid_list = "Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row <strong>%s</strong>. If this is a location, start with the Country, adding more specific details separated with '|'. See list of allowed Country entries at <a href='https://www.ebi.ac.uk/ena/browser/view/ERC000053'>https://www.ebi.ac.uk/ena/browser/view/ERC000053</a>"
    validation_msg_invalid_taxonomy = "Invalid data: <strong>%s</strong> in column <strong>%s</strong> at row <strong>%s</strong>. Expected value is <strong>%s</strong>"
    validation_msg_synonym = "Invalid scientific name: <strong>%s</strong> at row <strong>%s</strong> is a synonym of <strong>%s</strong>. Please provide the official scientific name."
    validation_msg_missing_taxon = "Missing TAXON_ID at row <strong>%s</strong>. For <strong>%s</strong> TAXON_ID should be <strong>%s</strong>"
    validation_msg_duplicate_tube_or_well_id = "Duplicate RACK_OR_PLATE_ID and TUBE_OR_WELL_ID found in this Manifest: <strong>%s</strong>"
    validation_msg_used_whole_organism = "Duplicate SPECIMEN_ID and ORGANISM_PART <strong>'WHOLE ORGANISM'</strong> pair found for specimen: <strong>%s</strong>"
    validation_warning_synonym = "Synonym warning: <strong>%s</strong> at row <strong>%s</strong> is a synonym of <strong>%s</strong>. COPO will substitute the official scientific name."
    validation_warning_field = "Missing <strong>%s</strong>: row <strong>%s</strong> - <strong>%s</strong> for <strong>%s</strong> will be filled with <strong>%s</strong>"
    validation_msg_invalid_rank = "Invalid scientific name or taxon ID: row <strong>%s</strong> - rank of scientific name and taxon id should be species."
    validation_msg_duplicate_tube_or_well_id_in_copo = "Duplicate RACK_OR_PLATE_ID and TUBE_OR_WELL_ID already in COPO: <strong>%s</strong>"
    validation_msg_invalid_date = "Invalid date: <strong>%s</strong> in column <strong>%s</strong> at row <strong>%s</strong>. Dates should be in format YYYY-MM-DD"
    validation_msg_rack_tube_both_na = "NOT_APPLICABLE, NOT_PROVIDED or NOT_COLLECTED found in both RACK_OR_PLATE_ID and TUBE_OR_WELL_ID at row <strong>%s</strong>."
    validation_msg_duplicate_without_target = "Duplicate RACK_OR_PLATE_ID and TUBE_OR_WELL_ID <strong>%s</strong> found without TARGET in SYMBIONT field. One of these duplicates must be listed as TARGET"

    fields = ""
    sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())

    def __init__(self, file=None):
        self.req = ThreadLocal.get_current_request()
        self.profile_id = self.req.session.get("profile_id", None)
        sample_images = Path(settings.MEDIA_ROOT) / "sample_images"
        display_images = Path(settings.MEDIA_ROOT) / "img" / "sample_images"
        self.these_images = sample_images / self.profile_id
        self.display_images = display_images / self.profile_id
        self.taxonomy_dict = {}
        self.whole_used_specimens = set()
        self.date_fields = ["DATE_OF_COLLECTION", "DATE_OF_PRESERVATION"]
        self.symbiont_list = []
        # if a file is passed in, then this is the first time we have seen the spreadsheet,
        # if not then we are looking at creating samples having previously validated
        if file:
            self.file = file
        else:
            self.sample_data = self.req.session.get("sample_data", "")

        # get type of manifest
        t = Profile().get_type(self.profile_id)
        if "ASG" in t:
            self.type = "ASG"
        else:
            self.type = "DTOL"

    def loadManifest(self, type):

        if self.profile_id is not None:
            notify_dtol_status(data={"profile_id": self.profile_id}, msg="Loading..", action="info",
                               html_id="sample_info")
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
                # self.data.fillna(value="")
                self.data = self.data.apply(lambda x: x.astype(str))
                self.data = self.data.apply(lambda x: x.strip())
                # print(self.data.size)
            except:
                # if error notify via web socket
                notify_dtol_status(data={"profile_id": self.profile_id}, msg="Unable to load file.", action="info",
                                   html_id="sample_info")
                return False

    def validate(self):
        flag = True
        errors = []
        # need to load validation field set



        with open(lk.WIZARD_FILES["sample_details"]) as json_data:

            try:
                # get definitive list of mandatory DTOL fields from schema
                s = json.load(json_data)
                self.fields = jp.match(
                    '$.properties[?(@.specifications[*] == "' + self.type.lower() + '" & @.required=="true")].versions[0]',
                    s)
                columns = list(self.data.columns)
                # check required fields are present in spreadsheet
                for item in self.fields:
                    notify_dtol_status(data={"profile_id": self.profile_id}, msg="Checking - " + item,
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
                        if header == "SYMBIONT" and self.type == "DTOL":
                            # dtol manifests are allowed to have blank field in SYMBIONT
                            pass
                        else:
                            cellcount = 0
                            for c in cells:
                                cellcount += 1
                                if not c.strip():
                                    # we have missing data in required cells
                                    if header == "SYMBIONT":
                                        errors.append(self.validation_msg_missing_symbiont % (
                                            header, str(cellcount + 1)))
                                    else:
                                        errors.append(self.validation_msg_missing_data % (
                                            header, str(cellcount + 1)))
                                    flag = False

                for index, row in self.data.iterrows():
                    if row["RACK_OR_PLATE_ID"] in self.blank_vals and row["TUBE_OR_WELL_ID"] in self.blank_vals:
                        errors.append(self.validation_msg_rack_tube_both_na % (str(index + 1)))
                        flag = False

                # check for uniqueness of RACK_OR_PLATE_ID and TUBE_OR_WELL_ID in this manifest
                rack_tube = self.data["RACK_OR_PLATE_ID"] + "/" + self.data["TUBE_OR_WELL_ID"]

                # duplicated returns a boolean array, false for not duplicate, true for duplicate
                u = list(rack_tube[rack_tube.duplicated()])

                # now check for uniqueness across all Samples
                if self.type != "ASG":
                    dup = Sample().check_dtol_unique(rack_tube)
                    if len(dup) > 0:
                        # errors = list(map(lambda x: "<li>" + x + "</li>", errors))
                        err = list(map(lambda x: x["RACK_OR_PLATE_ID"] + "/" + x["TUBE_OR_WELL_ID"], dup))
                        errors.append(self.validation_msg_duplicate_tube_or_well_id_in_copo % (err))
                        flag = False
                else:
                    # duplicates are allowed for asg but one element of duplicate set must have target in sybiont fields
                    for i in u:
                        rack, tube = i.split('/')
                        rows = self.data.loc[
                            (self.data["RACK_OR_PLATE_ID"] == rack) & (self.data["TUBE_OR_WELL_ID"] == tube)]
                        if "TARGET" not in rows["SYMBIONT"].values:
                            errors.append(self.validation_msg_duplicate_without_target % (
                                    rows["RACK_OR_PLATE_ID"][0] + "/" + rows["TUBE_OR_WELL_ID"][0]))
                            flag = False

                # get list of DTOL fields from schemas
                self.fields = jp.match(
                    '$.properties[?(@.specifications[*] == ' + self.type.lower() + ')].versions[0]', s)
                for header, cells in self.data.iteritems():

                    notify_dtol_status(data={"profile_id": self.profile_id}, msg="Checking - " + header,
                                       action="info",
                                       html_id="sample_info")
                    if header in self.fields:
                        if header == "SYMBIONT" and self.type == "DTOL":
                            # dtol manifests are allowed to have blank field in SYMBIONT
                            pass
                        else:
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
                                        if c_value.upper() not in allowed_vals or not location_2part:
                                            errors.append(self.validation_msg_invalid_list % (
                                                c_value, header, str(cellcount + 1)))
                                            flag = False
                                    elif header == "ORGANISM_PART":
                                        # special check for piped values
                                        for part in str(c).split('|'):
                                            if part.strip() not in allowed_vals:
                                                errors.append(self.validation_msg_invalid_data % (
                                                    part, header, str(cellcount + 1), allowed_vals
                                                ))
                                                flag = False
                                    elif c_value.strip() not in allowed_vals:
                                        # check value is in allowed enum
                                        errors.append(self.validation_msg_invalid_data % (
                                            c_value, header, str(cellcount + 1), allowed_vals))
                                        flag = False
                                    if header == "ORGANISM_PART" and c_value.strip() == "WHOLE_ORGANISM":
                                        # send specimen in used whole specimens set
                                        # print(c_value)
                                        current_specimen = self.data.at[cellcount - 1, "SPECIMEN_ID"]
                                        # print(current_specimen)
                                        if current_specimen in self.whole_used_specimens:
                                            errors.append(self.validation_msg_used_whole_organism % (current_specimen))
                                            flag = False
                                        else:
                                            self.whole_used_specimens.add(current_specimen)
                                if regex_rule:
                                    # handle any regular expressions provided for valiation

                                    if c and not re.match(regex_rule, c.replace("_", " "), re.IGNORECASE):
                                        errors.append(self.validation_msg_invalid_data % (
                                            c, header, str(cellcount + 1), regex_human_readable))
                                        flag = False
                                # validation checks for SERIES
                                if header == "SERIES":
                                    try:
                                        int(c)
                                    except ValueError:
                                        errors.append(self.validation_msg_invalid_data % (
                                            c, header, str(cellcount + 1), "integers"))
                                        flag = False
                                elif header == "TIME_ELAPSED_FROM_COLLECTION_TO_PRESERVATION":
                                    # check this is either a NOT_* or an integer
                                    if c_value.strip() not in self.blank_vals:
                                        try:
                                            float(c_value)
                                        except ValueError:
                                            errors.append(self.validation_msg_invalid_data % (
                                                c_value, header, str(cellcount + 1),
                                                "integer or " + ", ".join(self.blank_vals)
                                            ))
                                            flag = False
                                # validation checks for date types
                                if header in self.date_fields and c_value.strip() not in self.blank_vals:
                                    try:
                                        validate_date(c)
                                    except ValueError as e:
                                        errors.append(
                                            self.validation_msg_invalid_date % (c, str(cellcount + 1), header))
                                        flag = False

                if not flag:
                    errors = list(map(lambda x: "<li>" + x + "</li>", errors))
                    errors = "".join(errors)

                    notify_dtol_status(data={"profile_id": self.profile_id},
                                       msg="<h4>" + self.file.name + "</h4><ol>" + errors + "</ol>",
                                       action="error",
                                       html_id="sample_info")
                    return False



            except Exception as e:
                error_message = str(e).replace("<", "").replace(">", "")
                notify_dtol_status(data={"profile_id": self.profile_id}, msg="Server Error - " + error_message,
                                   action="info",
                                   html_id="sample_info")
                return False

            # if we get here we have a valid spreadsheet
            notify_dtol_status(data={"profile_id": self.profile_id}, msg="Spreadsheet is Valid", action="info",
                               html_id="sample_info")
            notify_dtol_status(data={"profile_id": self.profile_id}, msg="", action="close", html_id="upload_controls")
            notify_dtol_status(data={"profile_id": self.profile_id}, msg="", action="make_valid", html_id="sample_info")

            return True

    def make_target_sample(self, sample):
        # need to pop taxon info, and add back into sample_list
        if not "species_list" in sample:
            sample["species_list"] = list()
        out = dict()
        out["SYMBIONT"] = "target"
        out["TAXON_ID"] = sample.pop("TAXON_ID")
        out["ORDER_OR_GROUP"] = sample.pop("ORDER_OR_GROUP")
        out["FAMILY"] = sample.pop("FAMILY")
        out["GENUS"] = sample.pop("GENUS")
        out["SCIENTIFIC_NAME"] = sample.pop("SCIENTIFIC_NAME")
        out["INFRASPECIFIC_EPITHET"] = sample.pop("INFRASPECIFIC_EPITHET")
        out["CULTURE_OR_STRAIN_ID"] = sample.pop("CULTURE_OR_STRAIN_ID")
        out["COMMON_NAME"] = sample.pop("COMMON_NAME")
        out["TAXON_REMARKS"] = sample.pop("TAXON_REMARKS")
        sample["species_list"].append(out)
        return sample

    def check_taxon_ena_submittable(self, taxon):
        errors = []
        curl_cmd = "curl " + "https://www.ebi.ac.uk/ena/taxonomy/rest/tax-id/" + taxon
        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
            print(receipt)
            taxinfo = json.loads(receipt.decode("utf-8"))
            if taxinfo["submittable"] != 'true':
                errors.append("TAXON_ID " + taxon + " is not submittable to ENA")
        except Exception as e:
            if receipt:
                try:
                    errors.append("ENA returned - " + taxinfo.get("error", "no error returned") + " - for TAXON_ID " + taxon)
                except NameError:
                    errors.append(
                        "ENA returned - " + receipt.decode("utf-8") + " - for TAXON_ID " + taxon)
            else:
                errors.append("No response from ENA taxonomy for taxon " + taxon)
        return errors


    def validate_taxonomy(self):
        ''' check if provided scientific name, TAXON ID,
        family and order are consistent with each other in known taxonomy'''
        Entrez.api_key = lookup.NIH_API_KEY

        errors = []
        warnings = []
        flag = True

        with open(lk.WIZARD_FILES["sample_details"]) as json_data:

            try:
                s = json.load(json_data)
                # get list of DTOL fields from schemas
                # self.fields = jp.match(
                #                    '$.properties[?(@.specifications[*] == "dtol")].versions[0]', s)
                # rows = list(self.data.rows)
                '''notify_sample_status(profile_id=self.profile_id,
                                     msg="hello",
                                     action="warning",
                                     html_id="warning_info")'''
                # build dictioanry of species in this manifest  max 200 IDs per query
                taxon_id_set = set(self.data['TAXON_ID'].tolist())
                notify_dtol_status(data={"profile_id": self.profile_id},
                                   msg="Querying NCBI for TAXON_IDs in manifest ",
                                   action="info",
                                   html_id="sample_info")
                taxon_id_list = list(taxon_id_set)
                if "ASG" in Profile().get_type(self.profile_id):
                    for taxon in taxon_id_list:
                        #check if taxon is submittable
                        ena_taxon_errors = self.check_taxon_ena_submittable(taxon)
                        if ena_taxon_errors:
                            errors += ena_taxon_errors
                            flag=False

                if any(id for id in taxon_id_list):
                    i = 0
                    while i < len(taxon_id_list):
                        # print("window starting at ", i, "ending at ", i + 200)
                        window_list = taxon_id_list[i: i + 200]
                        i += 200
                        handle = Entrez.efetch(db="Taxonomy", id=window_list, retmode="xml")
                        records = Entrez.read(handle)
                        for element in records:
                            self.taxonomy_dict[element['TaxId']] = element
                for index, row in self.data[
                    ['ORDER_OR_GROUP', 'FAMILY', 'GENUS', 'TAXON_ID', 'SCIENTIFIC_NAME']].iterrows():
                    # print('validating row ', str(index + 2))
                    if all(row[header].strip() == "" for header in ['TAXON_ID', 'SCIENTIFIC_NAME']):
                        # print("row is empty")
                        errors.append(
                            "Missing data: both TAXON_ID and SCIENTIFIC_NAME missing from row <strong>%s</strong>. Provide at least one" % (
                                str(index + 2)))
                        flag = False
                        continue
                    notify_dtol_status(data={"profile_id": self.profile_id},
                                       msg="Checking taxonomy information at row <strong>%s</strong> - <strong>%s</strong>" % (
                                           str(index + 2), row['SCIENTIFIC_NAME']),
                                       action="info",
                                       html_id="sample_info")
                    scientific_name = row['SCIENTIFIC_NAME'].strip()
                    taxon_id = row['TAXON_ID'].strip()
                    # print(records['IdList'])
                    # print(type(records['IdList']))
                    # suggest TAXON_ID if not provided
                    if not taxon_id:
                        handle = Entrez.esearch(db="Taxonomy", term=scientific_name)
                        records = Entrez.read(handle)
                        # errors.append(self.validation_msg_missing_taxon % (str(index+2), scientific_name, records['IdList'][0]))
                        if not records['IdList']:
                            errors.append(
                                "Invalid data: couldn't resolve SCIENTIFIC_NAME <strong>%s</strong> at row <strong>%s</strong>" % (
                                    scientific_name, str(index + 2)))
                            flag = False
                            continue
                        warnings.append(self.validation_warning_field % (
                            "TAXON_ID", str(index + 2), "TAXON_ID", scientific_name, records['IdList'][0]))
                        self.data.at[index, "TAXON_ID"] = records['IdList'][0]
                        taxon_id = records['IdList'][0]
                        if "ASG" in Profile().get_type(self.profile_id):
                            # check if taxon is submittable
                            ena_taxon_errors = self.check_taxon_ena_submittable(taxon_id)
                            if ena_taxon_errors:
                                errors += ena_taxon_errors
                                flag = False
                        # flag = False
                        # continue
                        handle = Entrez.efetch(db="Taxonomy", id=taxon_id, retmode="xml")
                        records = Entrez.read(handle)
                        if records:
                            self.taxonomy_dict[records[0]['TaxId']] = records[0]

                    ###elif taxon_id not in records['IdList']:
                    if self.taxonomy_dict.get(taxon_id):
                        if not scientific_name:
                            errors.append(self.validation_msg_missing_data % ("SCIENTIFIC_NAME", str(index + 2),))
                            flag = False
                            continue
                        elif scientific_name.upper() != self.taxonomy_dict[taxon_id]['ScientificName'].upper():
                            handle = Entrez.esearch(db="Taxonomy", term=scientific_name)
                            records = Entrez.read(handle)
                            # check if the scientific name provided is a synonim
                            if taxon_id in records['IdList']:
                                # errors.append(self.validation_msg_synonym % (scientific_name, str(index + 2),
                                #                                             self.taxonomy_dict[taxon_id][
                                #                                                 'ScientificName']))  ###records[0]['ScientificName']))
                                warnings.append(self.validation_warning_synonym % (scientific_name, str(index + 2),
                                                                                   self.taxonomy_dict[taxon_id][
                                                                                       'ScientificName']))
                                self.data.at[index, "SCIENTIFIC_NAME"] = self.taxonomy_dict[taxon_id][
                                    'ScientificName'].upper()
                                other_info = ""
                                if self.data.at[index, "OTHER_INFORMATION"].strip():
                                    other_info = self.data.at[index, "OTHER_INFORMATION"] + " | "
                                self.data.at[index, "OTHER_INFORMATION"] = other_info + \
                                                                           "COPO substituted the scientific name synonym %s with %s" % (
                                                                               scientific_name,
                                                                               self.taxonomy_dict[taxon_id][
                                                                                   'ScientificName'].upper())
                                # flag = False
                                # continue
                            elif not records['IdList']:
                                # handle = Entrez.efetch(db="Taxonomy", id=taxon_id, retmode="xml")
                                # records = Entrez.read(handle)
                                # if records:
                                # self.taxonomy_dict[records[0]['TaxId']] = records[0]
                                expected_name = self.taxonomy_dict[taxon_id].get('ScientificName', '[unknown]')
                                errors.append(self.validation_msg_invalid_taxonomy % (
                                    scientific_name, "SCIENTIFIC_NAME", str(index + 2), expected_name))
                                # else:
                                #   errors.append("Invalid data: couldn't resolve SCIENTIFIC_NAME nor TAXON_ID at row <strong>%s</strong>" % str(index+2))
                                flag = False
                                continue
                            else:
                                errors.append(self.validation_msg_invalid_taxonomy % (
                                    taxon_id, "TAXON_ID", str(index + 2), str(records['IdList'])))
                                flag = False
                                continue

                        ###handle = Entrez.efetch(db="Taxonomy", id=taxon_id, retmode="xml")
                        ###records = Entrez.read(handle)

                        if self.taxonomy_dict[taxon_id]['Rank'] != 'species':
                            if not "ASG" in Profile().get_type(self.profile_id):  # ASG is allowed rank level ids
                                errors.append(self.validation_msg_invalid_rank % (str(index + 2)))
                                flag = False
                                continue
                        ###for element in records[0]['LineageEx']:
                        for element in self.taxonomy_dict[taxon_id]['LineageEx']:
                            # print('checking lineage')
                            rank = element.get('Rank')
                            if rank == 'genus':
                                if not row['GENUS'].strip():
                                    warnings.append(self.validation_warning_field % (
                                        "GENUS", str(index + 2), "GENUS", scientific_name,
                                        element.get('ScientificName').upper()))
                                    self.data.at[index, "GENUS"] = element.get('ScientificName').upper()
                                elif row['GENUS'].strip().upper() != element.get('ScientificName').upper():
                                    errors.append(self.validation_msg_invalid_taxonomy % (
                                        row['GENUS'], "GENUS", str(index + 2), element.get('ScientificName').upper()))
                                    flag = False
                            elif rank == 'family':
                                if not row['FAMILY'].strip():
                                    warnings.append(self.validation_warning_field % (
                                        "FAMILY", str(index + 2), "FAMILY", scientific_name,
                                        element.get('ScientificName').upper()))
                                    self.data.at[index, "FAMILY"] = element.get('ScientificName').upper()
                                elif row['FAMILY'].strip().upper() != element.get('ScientificName').upper():
                                    errors.append(self.validation_msg_invalid_taxonomy % (
                                        row['FAMILY'], "FAMILY", str(index + 2), element.get('ScientificName').upper()))
                                    flag = False
                            elif rank == 'order':
                                if not row['ORDER_OR_GROUP'].strip():
                                    warnings.append(self.validation_warning_field % (
                                        "ORDER_OR_GROUP", str(index + 2), "ORDER_OR_GROUP", scientific_name,
                                        element.get('ScientificName').upper()))
                                    self.data.at[index, "ORDER_OR_GROUP"] = element.get('ScientificName').upper()
                                elif row['ORDER_OR_GROUP'].strip().upper() != element.get('ScientificName').upper():
                                    errors.append(self.validation_msg_invalid_taxonomy % (
                                        row['ORDER_OR_GROUP'], "ORDER_OR_GROUP", str(index + 2),
                                        element.get('ScientificName').upper()))
                                    flag = False
                    else:
                        # handle = Entrez.esearch(db="Taxonomy", term=scientific_name)
                        # records = Entrez.read(handle)

                        errors.append(
                            "Invalid data: couldn't retrieve TAXON_ID <strong>%s</strong> at row <strong>%s</strong>" % (
                                row['TAXON_ID'], str(index + 2)))
                        flag = False

                # send warnings
                if warnings:
                    notify_dtol_status(data={"profile_id": self.profile_id},
                                       msg="<br>".join(warnings),
                                       action="warning",
                                       html_id="warning_info")

                if not flag:
                    errors = list(map(lambda x: "<li>" + x + "</li>", errors))
                    errors = "".join(errors)
                    notify_dtol_status(data={"profile_id": self.profile_id},
                                       msg="<h4>" + self.file.name + "</h4><ol>" + errors + "</ol>",
                                       action="error",
                                       html_id="sample_info")
                    return False

                else:
                    return True

            except HTTPError as e:

                error_message = str(e).replace("<", "").replace(">", "")
                notify_dtol_status(data={"profile_id": self.profile_id},
                                   msg="Service Error - The NCBI Taxonomy service may be down, please try again later.",
                                   action="error",
                                   html_id="sample_info")
                return False
            except Exception as e:
                error_message = str(e).replace("<", "").replace(">", "")
                notify_dtol_status(data={"profile_id": self.profile_id}, msg="Server Error - " + error_message,
                                   action="error",
                                   html_id="sample_info")
                return False

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
        notify_dtol_status(data={"profile_id": self.profile_id}, msg=output, action="make_images_table",
                           html_id="images")
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
        notify_dtol_status(data={"profile_id": self.profile_id}, msg=sample_data, action="make_table",
                           html_id="sample_table")

    def save_records(self):
        # create mongo sample objects from info parsed from manifest and saved to session variable
        sample_data = self.sample_data
        manifest_id = str(uuid.uuid4())
        request = ThreadLocal.get_current_request()
        image_data = request.session.get("image_specimen_match", [])
        for p in range(1, len(sample_data)):
            s = (map_to_dict(sample_data[0], sample_data[p]))
            s["sample_type"] = "dtol"
            s["tol_project"] = self.type
            s["biosample_accession"] = []
            s["manifest_id"] = manifest_id
            s["status"] = "pending"
            s["rack_tube"] = s["RACK_OR_PLATE_ID"] + "/" + s["TUBE_OR_WELL_ID"]
            notify_dtol_status(data={"profile_id": self.profile_id},
                               msg="Creating Sample with ID: " + s["TUBE_OR_WELL_ID"] + "/" + s["SPECIMEN_ID"],
                               action="info",
                               html_id="sample_info")

            if s["SYMBIONT"].lower() == "target":
                # transform spieces info into species list format
                s = self.make_target_sample(s)
                sampl = Sample(profile_id=self.profile_id).save_record(auto_fields={}, **s)
                Sample().timestamp_dtol_sample_created(sampl["_id"])
                self.add_from_symbiont_list(s)
            elif s["SYMBIONT"].lower() == "symbiont":
                self.check_for_target_or_add_to_symbiont_list(s)

            for im in image_data:
                # create matching DataFile object for image is provided
                if s["SPECIMEN_ID"] in im["specimen_id"]:
                    fields = {"file_location": im["file_name"]}
                    df = DataFile().save_record({}, **fields)
                    DataFile().insert_sample_id(df["_id"], sampl["_id"])
                    break;

            uri = request.build_absolute_uri('/')
        profile_id = request.session["profile_id"]
        profile = Profile().get_record(profile_id)
        title = profile["title"]
        description = profile["description"]
        CopoEmail().notify_new_manifest(uri + 'copo/accept_reject_sample/', title=title, description=description)

    def delete_sample(self, sample_ids):
        # accept a list of ids, try to delete creating report
        report = list()
        for s in sample_ids:
            r = Sample().delete_sample(s)
            report.append(r)
        notify_dtol_status(data={"profile_id": self.profile_id}, msg=report,
                           action="info",
                           html_id="sample_info")

    def add_from_symbiont_list(self, s):
        for idx, el in enumerate(self.symbiont_list):
            if el.get("RACK_OR_PLATE_ID", "") == s.get("RACK_OR_PLATE_ID", "") \
                    and el.get("TUBE_OR_WELL_ID", "") == s.get("TUBE_OR_WELL_ID", ""):
                out = self.symbiont_list.pop(idx)
                out.pop("RACK_OR_PLATE_ID")
                out.pop("TUBE_OR_WELL_ID")
                Sample().add_symbiont(s, out)

    def check_for_target_or_add_to_symbiont_list(self, s):
        # method checks if there is an existing target sample to attach this symbiont to. If so we attach, if not,
        # we create the tax data, and append to a list of use by a later sample
        if not Sample().check_and_add_symbiont(s):
            # add to list
            out = make_tax_from_sample(s)
            self.symbiont_list.append(out)


def validate_date(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DD")
