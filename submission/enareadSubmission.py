__author__ = 'etuka'
__date__ = '27 March 2019'

import os
from lxml import etree
from datetime import datetime
from tools import resolve_env
from django.conf import settings
from submission.helpers.ena_helper import SubmissionHelper
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype
from web.apps.web_copo.lookup.lookup import SRA_SUBMISSION_TEMPLATE, SRA_PROJECT_TEMPLATE, SRA_SAMPLE_TEMPLATE

lg = settings.LOGGER

"""
class handles read data submissions to the ENA - see: https://ena-docs.readthedocs.io/en/latest/cli_06.html
"""


class EnaReads:
    def __init__(self, submission_id=str()):
        self.submission_id = submission_id
        self.project_alias = self.submission_id

        # helper object
        self.submission_helper = None

        # submission location
        self.submission_location = None

        # sra settings
        self.sra_settings = None

    def submit(self):
        """
        function ochestrates the submission process
        :return:
        """

        # create helper object
        self.submission_helper = SubmissionHelper(submission_id=self.submission_id)

        # create submission location
        self.submission_location = self.create_submission_location()

        # retrieve sra settings
        self.sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())

        # xml paths
        xml_paths = dict()

        # create submission xml
        context = self._create_submission_xml()

        if context['status'] is False:
            return context

        xml_paths['submission'] = context['value']

        # create project xml
        context = self._create_project_xml()

        if context['status'] is False:
            return context

        xml_paths['project'] = context['value']

        # create sample xml
        context = self._create_sample_xml()

        if context['status'] is False:
            return context

        xml_paths['sample'] = context['value']

        context = self._submit_xmls(xml_paths)

        return context

    def log_error(self, message):
        try:
            lg.log('[Submission: ' + self.submission_id + '] ' + message, level=Loglvl.ERROR, type=Logtype.FILE)
        except Exception as e:
            pass

        return False

    def log_info(self, message):
        lg.log('[Submission: ' + self.submission_id + '] ' + message, level=Loglvl.INFO, type=Logtype.FILE)

    def create_submission_location(self):
        """
        function creates the location for storing submission files
        :return:
        """

        dir = os.path.join(os.path.dirname(__file__), "data")
        conv_dir = os.path.join(dir, self.submission_id)

        try:
            if not os.path.exists(conv_dir):
                os.makedirs(conv_dir)
        except Exception as e:
            message = 'Error creating submission location ' + conv_dir + ": " + str(e)
            self.log_error(message)
            raise

        message = 'Submission location is: ' + conv_dir
        self.log_info(message)

        return conv_dir

    def write_xml_file(self, doc_root, file_name):
        """
        :param doc_root:
        :param file_name:
        :return:
        """

        result = dict(status=True, value='')

        xml_file_path = os.path.join(self.submission_location, file_name)
        tree = etree.ElementTree(doc_root)

        try:
            tree.write(xml_file_path, encoding="utf8", xml_declaration=True, pretty_print=True)
        except Exception as e:
            message = '[Submission: ' + self.submission_id + ']' + 'Error writing xml file ' + file_name + ": " + str(e)
            self.log_error(message)
            result['message'] = message
            result['status'] = False

            return result

        message = file_name + ' successfully written to  ' + xml_file_path
        self.log_info(message)

        result['value'] = xml_file_path

        return result

    def _create_submission_xml(self):
        """
        function creates submission.xml
        :return:
        """

        result = dict(status=True, value='')

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.parse(SRA_SUBMISSION_TEMPLATE, parser).getroot()

        # set submission attributes
        root.set("broker_name", self.sra_settings["sra_broker"])
        root.set("center_name", self.sra_settings["sra_center"])
        root.set("submission_date", datetime.utcnow().replace(tzinfo=d_utils.simple_utc()).isoformat())

        # set SRA contacts
        contacts = root.find('CONTACTS')

        # set copo sra contacts
        copo_contact = etree.SubElement(contacts, 'CONTACT')
        copo_contact.set("name", self.sra_settings["sra_broker_contact_name"])
        copo_contact.set("inform_on_error", self.sra_settings["sra_broker_inform_on_error"])
        copo_contact.set("inform_on_status", self.sra_settings["sra_broker_inform_on_status"])

        # set user contacts
        sra_map = {"inform_on_error": "SRA Inform On Error", "inform_on_status": "SRA Inform On Status"}
        user_contacts = self.submission_helper.get_sra_contacts()
        for k, v in user_contacts.items():
            user_sra_roles = [x for x in sra_map.keys() if sra_map[x].lower() in v]
            if user_sra_roles:
                user_contact = etree.SubElement(contacts, 'CONTACT')
                user_contact.set("name", ' '.join(k[1:]))
                for role in user_sra_roles:
                    user_contact.set(role, k[0])

        # set release action
        release_date = self.submission_helper.get_study_release()

        if release_date:
            # set SRA actions
            actions = root.find('ACTIONS')
            action = etree.SubElement(actions, 'ACTION')

            if release_date["in_the_past"] is False:
                action_type = etree.SubElement(action, 'HOLD')
                action_type.set("HoldUntilDate", release_date["release_date"])
            else:
                etree.SubElement(action, 'RELEASE')

        return self.write_xml_file(root, "submission.xml")

    def _create_project_xml(self):
        """
        function creates project (study) xml
        :return:
        """

        result = dict(status=True, value='')

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.parse(SRA_PROJECT_TEMPLATE, parser).getroot()

        # set SRA contacts
        project = root.find('PROJECT')

        # set project descriptors
        project.set("alias", self.project_alias)
        project.set("center_name", self.sra_settings["sra_center"])

        study_attributes = self.submission_helper.get_study_descriptors()

        if study_attributes.get("name", str()):
            etree.SubElement(project, 'NAME').text = study_attributes.get("name")

        if study_attributes.get("title", str()):
            etree.SubElement(project, 'TITLE').text = study_attributes.get("title")

        if study_attributes.get("description", str()):
            etree.SubElement(project, 'DESCRIPTION').text = study_attributes.get("description")

        # set project type - sequencing project
        submission_project = etree.SubElement(project, 'SUBMISSION_PROJECT')
        etree.SubElement(submission_project, 'SEQUENCING_PROJECT')

        return self.write_xml_file(root, "project.xml")

    def _create_sample_xml(self):
        """
        function creates sample xml
        :return:
        """

        result = dict(status=True, value='')

        # reset error object
        self.submission_helper.flush_converter_errors()

        parser = etree.XMLParser(remove_blank_text=True)

        # root element is  SAMPLE_SET
        root = etree.parse(SRA_SAMPLE_TEMPLATE, parser).getroot()

        # get samples and create sample nodes
        samples = self.submission_helper.get_study_samples()

        # get errors
        converter_errors = self.submission_helper.get_converter_errors()

        if converter_errors:
            result['status'] = False
            result['message'] = converter_errors

            return result

        # add samples
        for sample in samples:
            sample_alias = self.project_alias + ":sample:" + sample.get("name", str())
            sample_node = etree.SubElement(root, 'SAMPLE')
            sample_node.set("alias", sample_alias)
            sample_node.set("center_name", self.sra_settings["sra_center"])
            sample_node.set("broker_name", self.sra_settings["sra_broker"])

            etree.SubElement(sample_node, 'TITLE').text = sample_alias
            sample_name_node = etree.SubElement(sample_node, 'SAMPLE_NAME')
            etree.SubElement(sample_name_node, 'TAXON_ID').text = sample.get("taxon_id", str())
            etree.SubElement(sample_name_node, 'SCIENTIFIC_NAME').text = sample.get("scientific_name", str())

            # add sample attributes
            sample_attributes_node = etree.SubElement(sample_node, 'SAMPLE_ATTRIBUTES')
            for atr in sample.get("attributes", list()):
                sample_attribute_node = etree.SubElement(sample_attributes_node, 'SAMPLE_ATTRIBUTE')
                etree.SubElement(sample_attribute_node, 'TAG').text = atr.get("tag", str())
                etree.SubElement(sample_attribute_node, 'VALUE').text = atr.get("value", str())

                if atr.get("unit", str()):
                    etree.SubElement(sample_attribute_node, 'UNITS').text = atr.get("unit", str())

        result['value'] = self.write_xml_file(root, "sample.xml")

        return self.write_xml_file(root, "sample.xml")


    def _submit_xmls(self, xml_paths):
        """
        function submits xml files to ENA
        :param xml_paths: contains paths to the xml files to be submitted
        :return:
        """

        message = "Submitting XMLS to ENA via CURL"
        self.log_info(message)

        pass_word = resolve_env.get_env('WEBIN_USER_PASSWORD')
        user_token = resolve_env.get_env('WEBIN_USER')
        ena_service = resolve_env.get_env('ENA_SERVICE')
        user_token = user_token.split("@")[0]
        ena_uri = "{ena_service!s}/ena/submit/drop-box/submit/?auth=ENA%20{user_token!s}%20{pass_word!s}".format(
            **locals())

        curl_cmd = 'curl -k -F "SUBMISSION=@' + submission_file + '" \
                 -F "PROJECT=@' + os.path.join(remote_path, project_file) + '" \
                 -F "SAMPLE=@' + os.path.join(remote_path, sample_file) + '" \
                 -F "EXPERIMENT=@' + os.path.join(remote_path, experiment_file) + '" \
                 -F "RUN=@' + os.path.join(remote_path, run_file) + '"' \
                   + '   "' + ena_uri + '"'

        lg.log("CURL command", level=Loglvl.INFO, type=Logtype.FILE)
        lg.log(curl_cmd, level=Loglvl.INFO, type=Logtype.FILE)

        output = subprocess.check_output(curl_cmd, shell=True)
        lg.log(output, level=Loglvl.INFO, type=Logtype.FILE)
        lg.log("Extracting fields from receipt", level=Loglvl.INFO, type=Logtype.FILE)

        xml = ET.fromstring(output)

        # first check for errors
        errors = xml.findall('*/ERROR')
        if errors:
            error_text = str()
            for e in errors:
                error_text = error_text + e.text

            transfer_fields = dict()
            transfer_fields["error"] = error_text
            transfer_fields["current_time"] = datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S")

            # save error to transfer record
            RemoteDataFile().update_transfer(self.transfer_token, transfer_fields)

            self.context["ena_status"] = "error"
            self.context["error_text"] = error_text

            lg.log(error_text, level=Loglvl.INFO, type=Logtype.FILE)
            lg.log('Submission error! Submission ID: ' + self.submission_id, level=Loglvl.ERROR, type=Logtype.FILE)

            return
        accessions_store = self._do_save_accessions(xml)

        return accessions_store

