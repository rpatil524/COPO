__author__ = 'etuka'
__date__ = '27 March 2019'

import os
from lxml import etree
from datetime import datetime
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
        self.submission_helper = SubmissionHelper(submission_id=submission_id)

        # create submission location
        self.submission_location = self.create_submission_location()

        # retrieve sra settings
        self.sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())

    def submit(self):
        """
        function ochestrates the submission process
        :return:
        """

        context = dict()

        # create submission xml
        self.create_submission_xml()

        # create project xml
        self.create_project_xml()

        return context

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
            lg.log(message, level=Loglvl.ERROR, type=Logtype.FILE)
            raise

        lg.log('Submission location is: ' + conv_dir, level=Loglvl.INFO, type=Logtype.FILE)

        return conv_dir

    def write_xml_file(self, doc_root, file_name):
        """

        :param doc_root:
        :param file_name:
        :return:
        """

        xml_file_path = os.path.join(self.submission_location, file_name)
        tree = etree.ElementTree(doc_root)

        try:
            tree.write(xml_file_path, encoding="utf8", xml_declaration=True, pretty_print=True)
        except Exception as e:
            message = 'Error writing xml file ' + file_name + ": " + str(e)
            lg.log(message, level=Loglvl.ERROR, type=Logtype.FILE)
            raise

        lg.log(file_name + ' successfully written to  ' + xml_file_path, level=Loglvl.INFO, type=Logtype.FILE)

        return xml_file_path

    def create_submission_xml(self):
        """
        function creates submission.xml
        :return:
        """

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.parse(SRA_SUBMISSION_TEMPLATE, parser).getroot()

        # set submission attributes
        root.set("broker_name", self.sra_settings["sra_broker"])
        root.set("center_name", self.sra_settings["sra_center"])
        root.set("submission_date", datetime.utcnow().replace(tzinfo=d_utils.simple_utc()).isoformat())

        # set SRA contacts
        contacts = root.find('CONTACTS')

        # set COPO contact
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
                action_type.set("target", self.project_alias)
                action_type.set("HoldUntilDate", release_date["release_date"])
            else:
                action_type = etree.SubElement(action, 'RELEASE')
                action_type.set("target", self.project_alias)

        return self.write_xml_file(root, "submission.xml")

    def create_project_xml(self):
        """
        function creates project (study) xml
        :return:
        """

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
