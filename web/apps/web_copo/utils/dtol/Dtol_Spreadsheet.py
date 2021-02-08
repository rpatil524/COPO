# Created by fshaw at 03/04/2020
import inspect
import json
import math
import os
import subprocess
import uuid
from os.path import join, isfile
from pathlib import Path
from shutil import rmtree
from urllib.error import HTTPError

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
from web.apps.web_copo.schemas.utils.data_utils import json_to_pytype
from .Dtol_Helpers import make_tax_from_sample
from .tol_validators import optional_field_dtol_validators as opt
from .tol_validators import required_field_dtol_validators as req
from .tol_validators.tol_validator import TolValidtor


class DtolSpreadsheet:
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
        self.data = None
        self.required_field_validators = list()
        self.optional_field_validators = list()
        self.opt = opt
        self.req = req
        self.symbiont_list = []
        self.validator_list = []
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

        # create list of required validators
        required = dict(globals().items())["req"]
        for element_name in dir(required):
            element = getattr(required, element_name)
            if inspect.isclass(element) and issubclass(element, TolValidtor) and not element.__name__ == "TolValidtor":
                self.required_field_validators.append(element)
        # create list of optional validators
        optional = dict(globals().items())["opt"]
        for element_name in dir(optional):
            element = getattr(optional, element_name)
            if inspect.isclass(element) and issubclass(element, TolValidtor) and not element.__name__ == "TolValidtor":
                self.optional_field_validators.append(element)

    def loadManifest(self, m_format):

        if self.profile_id is not None:
            notify_dtol_status(data={"profile_id": self.profile_id}, msg="Loading..", action="info",
                               html_id="sample_info")
            try:
                # read excel and convert all to string
                if m_format == "xls":
                    self.data = pandas.read_excel(self.file, keep_default_na=False, na_values=lookup.na_vals)
                elif m_format == "csv":
                    self.data = pandas.read_csv(self.file, keep_default_na=False, na_values=lookup.na_vals)
                '''
                for column in self.allowed_empty:
                    self.data[column] = self.data[column].fillna("")
                '''
                self.data = self.data.apply(lambda x: x.astype(str))
                self.data = self.data.apply(lambda x: x.strip())
            except:
                # if error notify via web socket
                notify_dtol_status(data={"profile_id": self.profile_id}, msg="Unable to load file.", action="info",
                                   html_id="sample_info")
                return False

    def validate(self):
        flag = True
        errors = []

        try:
            # get definitive list of mandatory DTOL fields from schema
            s = json_to_pytype(lk.WIZARD_FILES["sample_details"])
            self.fields = jp.match(
                '$.properties[?(@.specifications[*] == "' + self.type.lower() + '" & @.required=="true")].versions[0]',
                s)

            # validate for required fields
            for v in self.required_field_validators:
                errors, flag = v(profile_id=self.profile_id, fields=self.fields, data=self.data,
                                 errors=errors, flag=flag).validate()

            # get list of DTOL fields from schemas
            self.fields = jp.match(
                '$.properties[?(@.specifications[*] == ' + self.type.lower() + ')].versions[0]', s)

            # validate for optional dtol fields
            for v in self.optional_field_validators:
                errors, flag = v(profile_id=self.profile_id, fields=self.fields, data=self.data,
                                 errors=errors, flag=flag).validate()

            # if flag is false, compile list of errors
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
                    errors.append(
                        "ENA returned - " + taxinfo.get("error", "no error returned") + " - for TAXON_ID " + taxon)
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
                        # check if taxon is submittable
                        ena_taxon_errors = self.check_taxon_ena_submittable(taxon)
                        if ena_taxon_errors:
                            errors += ena_taxon_errors
                            flag = False

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
                            "Missing data: both TAXON_ID and SCIENTIFIC_NAME missing from row <strong>%s</strong>. "
                            "Provide at least one" % (
                                str(index + 2)))
                        flag = False
                        continue
                    notify_dtol_status(data={"profile_id": self.profile_id},
                                       msg="Checking taxonomy information at row <strong>%s</strong> - "
                                           "<strong>%s</strong>" % (
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
                        # errors.append(self.validation_msg_missing_taxon % (str(index+2), scientific_name,
                        # records['IdList'][0]))
                        if not records['IdList']:
                            errors.append(
                                "Invalid data: couldn't resolve SCIENTIFIC_NAME <strong>%s</strong> at row "
                                "<strong>%s</strong>" % (
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
                                #                                                 'ScientificName']))  ###records[0][
                                #                                                 'ScientificName']))
                                warnings.append(self.validation_warning_synonym % (scientific_name, str(index + 2),
                                                                                   self.taxonomy_dict[taxon_id][
                                                                                       'ScientificName']))
                                self.data.at[index, "SCIENTIFIC_NAME"] = self.taxonomy_dict[taxon_id][
                                    'ScientificName'].upper()
                                other_info = ""
                                if self.data.at[index, "OTHER_INFORMATION"].strip():
                                    other_info = self.data.at[index, "OTHER_INFORMATION"] + " | "
                                self.data.at[index, "OTHER_INFORMATION"] = other_info + \
                                                                           "COPO substituted the scientific name " \
                                                                           "synonym %s with %s" % (
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
                                #   errors.append("Invalid data: couldn't resolve SCIENTIFIC_NAME nor TAXON_ID at row
                                #   <strong>%s</strong>" % str(index+2))
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
                            "Invalid data: couldn't retrieve TAXON_ID <strong>%s</strong> at row <strong>%s</strong>"
                            % (
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
                    output.append({
                        "file_name": "None", "specimen_id": "No Image found for <strong>" + sample[
                            specimen_id_column_index] + "</strong>"
                    })
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
