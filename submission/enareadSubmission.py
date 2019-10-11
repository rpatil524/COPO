__author__ = 'etuka'
__date__ = '27 March 2019'

import os
import glob
import shutil
import ftplib
import ntpath
import pexpect
import subprocess
import pandas as pd
from lxml import etree
from bson import ObjectId
from datetime import datetime
from tools import resolve_env
from dal import cursor_to_list
import dal.mongo_util as mutil
from contextlib import closing
from django.conf import settings
from submission.helpers import generic_helper as ghlper
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
from submission.helpers.ena_helper import SubmissionHelper
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.lookup.copo_lookup_service import COPOLookup
from web.apps.web_copo.lookup.lookup import SRA_SUBMISSION_TEMPLATE, SRA_EXPERIMENT_TEMPLATE, SRA_RUN_TEMPLATE, \
    SRA_PROJECT_TEMPLATE, SRA_SAMPLE_TEMPLATE, \
    SRA_SUBMISSION_MODIFY_TEMPLATE, ENA_CLI

REPOSITORIES = settings.REPOSITORIES
BASE_DIR = settings.BASE_DIR

"""
class handles read data submissions to the ENA - see: https://ena-docs.readthedocs.io/en/latest/cli_06.html
"""

REFRESH_THRESHOLD = 5 * 3600  # in hours, time to reset a potentially staled task to pending


class EnaReads:
    def __init__(self, submission_id=str()):
        self.submission_id = submission_id
        self.project_alias = self.submission_id

        self.ena_service = resolve_env.get_env('ENA_SERVICE')
        self.pass_word = resolve_env.get_env('WEBIN_USER_PASSWORD')
        self.user_token = resolve_env.get_env('WEBIN_USER').split("@")[0]
        self.webin_domain = resolve_env.get_env('WEBIN_USER').split("@")[1]

        self.submission_helper = None
        self.submission_location = None
        self.sra_settings = None
        self.datafiles_dir = None
        self.submission_context = None

    def process_queue(self):
        """
        function picks a submission from the queue to process
        :return:
        """

        collection_handle = ghlper.get_submission_queue_handle()

        # check and update status for long running tasks
        records = cursor_to_list(
            collection_handle.find({'repository': 'ena', 'processing_status': 'running'}))

        for rec in records:
            recorded_time = rec.get("date_modified", None)

            if not recorded_time:
                rec['date_modified'] = d_utils.get_datetime()
                collection_handle.update(
                    {"_id": ObjectId(str(rec.pop('_id')))},
                    {'$set': rec})

                continue

            current_time = d_utils.get_datetime()
            time_difference = current_time - recorded_time
            if time_difference.seconds >= (REFRESH_THRESHOLD):  # time submission is perceived to have been running
                # refresh task to be rescheduled again
                rec['date_modified'] = d_utils.get_datetime()
                rec['processing_status'] = 'pending'
                collection_handle.update(
                    {"_id": ObjectId(str(rec.pop('_id')))},
                    {'$set': rec})

        # obtain pending submission for processing
        records = cursor_to_list(
            collection_handle.find({'repository': 'ena', 'processing_status': 'pending'}).sort([['date_modified', 1]]))

        if not records:
            return True

        # pick top of the list, update status and timestamp
        queued_record = records[0]
        queued_record['processing_status'] = 'running'
        queued_record['date_modified'] = d_utils.get_datetime()

        queued_record_id = queued_record.pop('_id', '')

        self.submission_id = queued_record.get("submission_id", str())
        message = "Now processing submission..."

        ghlper.logging_info(message, self.submission_id)
        ghlper.update_submission_status(status='info', message=message, submission_id=self.submission_id)

        collection_handle.update(
            {"_id": ObjectId(str(queued_record_id))},
            {'$set': queued_record})

        result = self.submit()
        # remove from queue - this supposes that submissions that returned error will have
        # to be re-scheduled for processing, upon addressing the error, by the user
        collection_handle.remove({"_id": queued_record_id})

        return True

    def submit(self):
        """
        function acts as a controller for the submission process
        :return:
        """

        self.project_alias = self.submission_id

        collection_handle = ghlper.get_submission_handle()

        # check status of submission record
        doc = collection_handle.find_one({"_id": ObjectId(self.submission_id)})

        if not doc:
            return dict(status=True, message='Submission record not found!')

        if str(doc.get("complete", False)).lower() == 'true':
            return dict(status=True,
                        message='This submission is marked as completed. '
                                'Please contact your administrator to raise any issues.')

        # instantiate helper object - performs most auxiliary tasks associated with the submission
        self.submission_helper = SubmissionHelper(submission_id=self.submission_id)

        ghlper.logging_info('Initiating submission...', self.submission_id)

        # clear any existing submission error
        ghlper.update_submission_status(submission_id=self.submission_id)

        # submission location
        self.submission_location = self.create_submission_location()
        self.datafiles_dir = os.path.join(self.submission_location, "files")
        self.submission_context = os.path.join(self.submission_location, "reads")

        # retrieve sra settings
        self.sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())

        # get submission xml
        context = self._get_submission_xml()

        if context['status'] is False:
            ghlper.update_submission_status(status='error', message=context.get("message", str()),
                                            submission_id=self.submission_id)
            return context

        submission_xml_path = context['value']

        # register project
        if not self.submission_helper.get_study_accessions():

            context = self._register_project(submission_xml_path=submission_xml_path)

            if context['status'] is False:
                ghlper.update_submission_status(status='error', message=context.get("message", str()),
                                                submission_id=self.submission_id)
                return context

        # register samples
        context = self._register_samples(submission_xml_path=submission_xml_path)
        if context['status'] is False:
            ghlper.update_submission_status(status='error', message=context.get("message", str()),
                                            submission_id=self.submission_id)
            return context

        # submit datafiles via either CLI or RESTful pathways - only use one at a time
        # todo: uncomment this to use the CLI submission pathway
        # context = self._submit_datafiles_cli(submission_xml_path=submission_xml_path)
        # todo: uncomment this to use the RESTful submission pathway
        context = self._submit_datafiles_rest(submission_xml_path=submission_xml_path)
        if context['status'] is False:
            ghlper.update_submission_status(status='error', message=context.get("message", str()),
                                            submission_id=self.submission_id)
            return context

        # release project
        context = self._process_study_release()

        return context

    def create_submission_location(self):
        """
        function creates the location for storing submission files
        :return:
        """

        conv_dir = os.path.join(os.path.join(os.path.dirname(__file__), "data"), self.submission_id)

        try:
            if not os.path.exists(conv_dir):
                os.makedirs(conv_dir)
        except Exception as e:
            message = 'Error creating submission location ' + conv_dir + ": " + str(e)
            ghlper.logging_error(message, self.submission_id)
            raise

        ghlper.logging_info('Created submission location: ' + conv_dir, self.submission_id)

        return conv_dir

    def _get_submission_xml(self):
        """
        function creates and return submission xml path
        :return:
        """

        # create submission xml
        ghlper.logging_info("Creating submission xml...", self.submission_id)

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

        # todo: add study publications

        # set release action
        release_date = self.submission_helper.get_study_release()

        # only set release info if in the past, instant release should be handled upon submission completion
        if release_date and release_date["in_the_past"] is False:
            actions = root.find('ACTIONS')
            action = etree.SubElement(actions, 'ACTION')

            action_type = etree.SubElement(action, 'HOLD')
            action_type.set("HoldUntilDate", release_date["release_date"])

        return self.write_xml_file(xml_object=root, file_name="submission.xml")

    def _register_project(self, submission_xml_path=str()):
        """
        function creates and submits project (study) xml
        :return:
        """

        # create project xml
        log_message = "Registering project..."
        ghlper.logging_info(log_message, self.submission_id)
        ghlper.update_submission_status(status='info', message=log_message, submission_id=self.submission_id)

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.parse(SRA_PROJECT_TEMPLATE, parser).getroot()

        # set SRA contacts
        project = root.find('PROJECT')

        # set project descriptors
        project.set("alias", self.project_alias)
        project.set("center_name", self.sra_settings["sra_center"])

        study_attributes = self.submission_helper.get_study_descriptors()

        if study_attributes.get("name", str()):
            etree.SubElement(project, 'NAME').text = study_attributes.get("name", str())

        if study_attributes.get("title", str()):
            etree.SubElement(project, 'TITLE').text = study_attributes.get("title", str())

        if study_attributes.get("description", str()):
            etree.SubElement(project, 'DESCRIPTION').text = study_attributes.get("description", str())

        # set project type - sequencing project
        submission_project = etree.SubElement(project, 'SUBMISSION_PROJECT')
        etree.SubElement(submission_project, 'SEQUENCING_PROJECT')

        # write project xml
        result = self.write_xml_file(xml_object=root, file_name="project.xml")
        if result['status'] is False:
            return result

        project_xml_path = result['value']

        result = dict(status=True, value='')

        # register project to the ENA service
        curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                   + ' -F "SUBMISSION=@' \
                   + submission_xml_path \
                   + '" -F "PROJECT=@' \
                   + project_xml_path \
                   + '" "' + self.ena_service \
                   + '"'

        ghlper.logging_info(
            "Submitting project xml to ENA via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx"),
            self.submission_id)

        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
        except Exception as e:
            message = 'API call error ' + str(e)
            ghlper.logging_error(message, self.submission_id)
            result['message'] = message
            result['status'] = False

            return result

        root = etree.fromstring(receipt)

        if root.get('success') == 'false':
            result['status'] = False
            result['message'] = "Couldn't register STUDY due to the following errors: "
            errors = root.findall('.//ERROR')
            if errors:
                error_text = str()
                for e in errors:
                    error_text = error_text + " \n" + e.text

                result['message'] = result['message'] + error_text

            # log error
            ghlper.logging_error(result['message'], self.submission_id)

            return result

        # save project accession
        self.write_xml_file(xml_object=root, file_name="project_receipt.xml")
        ghlper.logging_info("Saving project accessions to the database", self.submission_id)
        project_accessions = list()
        for accession in root.findall('PROJECT'):
            project_accessions.append(
                dict(
                    accession=accession.get('accession', default=str()),
                    alias=accession.get('alias', default=str()),
                    status=accession.get('status', default=str()),
                    release_date=accession.get('holdUntilDate', default=str())
                )
            )

        collection_handle = ghlper.get_submission_handle()
        doc = collection_handle.find_one({"_id": ObjectId(self.submission_id)}, {"accessions": 1})

        if doc:
            submission_record = doc
            accessions = submission_record.get("accessions", dict())
            accessions['project'] = project_accessions
            submission_record['accessions'] = accessions

            collection_handle.update(
                {"_id": ObjectId(str(submission_record.pop('_id')))},
                {'$set': submission_record})

            # update submission status
            status_message = "Project successfully registered, and accessions saved."
            ghlper.update_submission_status(status='info', message=status_message, submission_id=self.submission_id)

        return dict(status=True, value='')

    def _register_samples(self, submission_xml_path=str()):
        """
        function creates and submits sample xml
        :return:
        """

        result = dict(status=True, value='')

        # create sample xml
        log_message = "Registering samples..."
        ghlper.logging_info(log_message, self.submission_id)
        ghlper.update_submission_status(status='info', message=log_message, submission_id=self.submission_id)

        # reset error object
        self.submission_helper.flush_converter_errors()

        parser = etree.XMLParser(remove_blank_text=True)

        # root element is  SAMPLE_SET
        root = etree.parse(SRA_SAMPLE_TEMPLATE, parser).getroot()

        # get samples and create sample nodes
        samples = self.submission_helper.get_sra_samples(submission_location=self.submission_location)

        # get errors
        converter_errors = self.submission_helper.get_converter_errors()

        if converter_errors:
            result['status'] = False
            result['message'] = converter_errors

            return result

        # filter out already submitted samples
        submitted_samples_id = [x['sample_id'] for x in self.submission_helper.get_sample_accessions()]

        # add samples
        sra_samples = list()
        for sample in samples:
            sample_alias = self.project_alias + ":sample:" + sample.get("name", str())

            if sample['sample_id'] in submitted_samples_id:
                continue

            sra_samples.append(dict(sample_id=sample['sample_id'], sample_alias=sample_alias))
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

        if not sra_samples:  # no samples to submit
            log_message = "No new samples to register!"
            ghlper.logging_info(log_message, self.submission_id)
            ghlper.update_submission_status(status='info', message=log_message, submission_id=self.submission_id)

            return dict(status=True, value='')

        sra_df = pd.DataFrame(sra_samples)
        sra_df.index = sra_df['sample_alias']

        # write sample xml
        result = self.write_xml_file(xml_object=root, file_name="sample.xml")
        if result['status'] is False:
            return result

        sample_xml_path = result['value']

        result = dict(status=True, value='')

        # register samples to the ENA service
        curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                   + ' -F "SUBMISSION=@' \
                   + submission_xml_path \
                   + '" -F "SAMPLE=@' \
                   + sample_xml_path \
                   + '" "' + self.ena_service \
                   + '"'

        ghlper.logging_info(
            "Submitting samples xml to ENA via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx"),
            self.submission_id)

        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
        except Exception as e:
            message = 'API call error ' + str(e)
            ghlper.logging_error(message, self.submission_id)
            result['message'] = message
            result['status'] = False

            return result

        root = etree.fromstring(receipt)

        if root.get('success') == 'false':
            result['status'] = False
            result['message'] = "Couldn't register SAMPLES due to the following errors: "
            errors = root.findall('.//ERROR')
            if errors:
                error_text = str()
                for e in errors:
                    error_text = error_text + " \n" + e.text

                result['message'] = result['message'] + error_text

            # log error
            ghlper.logging_error(result['message'], self.submission_id)

            return result

        # save sample accession
        self.write_xml_file(xml_object=root, file_name="samples_receipt.xml")
        ghlper.logging_info("Saving samples accessions to the database", self.submission_id)
        sample_accessions = list()
        for accession in root.findall('SAMPLE'):
            biosample = accession.find('EXT_ID')
            sample_alias = accession.get('alias', default=str())
            sample_id = sra_df.loc[sample_alias]['sample_id']
            sample_accessions.append(
                dict(
                    sample_accession=accession.get('accession', default=str()),
                    sample_alias=sample_alias,
                    biosample_accession=biosample.get('accession', default=str()),
                    sample_id=sample_id
                )
            )

        collection_handle = ghlper.get_submission_handle()
        doc = collection_handle.find_one({"_id": ObjectId(self.submission_id)}, {"accessions": 1})

        if doc:
            submission_record = doc
            accessions = submission_record.get("accessions", dict())
            previous = accessions.get('sample', list())
            previous.extend(sample_accessions)
            accessions['sample'] = previous
            submission_record['accessions'] = accessions

            collection_handle.update(
                {"_id": ObjectId(str(submission_record.pop('_id')))},
                {'$set': submission_record})

            # update submission status
            status_message = "Samples successfully registered, accessions saved."
            ghlper.update_submission_status(status='info', message=status_message, submission_id=self.submission_id)

        return dict(status=True, value='')

    def _process_study_release(self):
        """
        function manages the decision to release a study
        :return:
        """

        release_date = self.submission_helper.get_study_release()
        if release_date and release_date["in_the_past"] is True:
            return self.release_study()

        return dict(status=True, value='', message='')

    def _submit_datafiles_rest(self, submission_xml_path=str()):
        """
        function submits files uisng the ENA resfulness API
        :param submission_xml_path:
        :return:
        """

        log_message = "Preparing datafiles for submission..."
        ghlper.logging_info(log_message, self.submission_id)
        ghlper.update_submission_status(status='info', message=log_message, submission_id=self.submission_id)

        collection_handle = ghlper.get_submission_handle()

        result = dict(status=True, value='')
        xml_parser = etree.XMLParser(remove_blank_text=True)

        # read in datafiles
        try:
            datafiles_df = pd.read_csv(os.path.join(self.submission_location, "datafiles.csv"))
        except Exception as e:
            message = 'Datafiles information not found ' + str(e)
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        if not len(datafiles_df):
            # no further datafiles to submit, finalise submission
            self.finalise_submission()
            return dict(status=True, value='')

        # set default for nans
        datafile_columns = datafiles_df.columns
        for k in datafile_columns:
            datafiles_df[k].fillna('', inplace=True)

        # get run accessions - these provide info on already submitted datafiles
        run_accessions = self.submission_helper.get_run_accessions()

        submitted_files = [x for y in run_accessions for x in y.get('datafiles', list())]

        # filter out submitted files from datafiles_df
        datafiles_df = datafiles_df[~datafiles_df.datafile_id.isin(submitted_files)]

        if not len(datafiles_df):
            # no further datafiles to submit, finalise submission
            self.finalise_submission()
            return dict(status=True, value='')

        # get pairing info
        datafiles_pairs = pd.DataFrame(self.submission_helper.get_pairing_info(), columns=['_id', '_id2'])

        # filter datafiles_pairs based on submitted_files and datafiles_df
        # i.e. if any of the paired files has been submitted, then remove the paired record
        if len(datafiles_pairs):
            datafiles_pairs = datafiles_pairs[
                ~((datafiles_pairs['_id'].isin(submitted_files)) | (datafiles_pairs['_id2'].isin(submitted_files)))]

        datafile_ids = list(datafiles_df.datafile_id)

        # ...also, it's a valid pair if both files in a pair are in datafiles_df
        if len(datafiles_pairs):
            datafiles_pairs = datafiles_pairs[
                (datafiles_pairs['_id'].isin(datafile_ids)) & (datafiles_pairs['_id2'].isin(datafile_ids))]

        # datafiles will be submitted on the following guideline:
        # if a datafile is marked as paired, but no pairing information is found (in datafiles_pairs),
        # the datafile will be submitted as a single file

        left_right_pair = list(datafiles_pairs['_id']) + list(datafiles_pairs['_id2'])
        unpaired_datafiles = [x for x in datafile_ids if x not in left_right_pair]

        if unpaired_datafiles:
            unpaired_datafiles = [[x, ''] for x in unpaired_datafiles]
            frames = [datafiles_pairs, pd.DataFrame(unpaired_datafiles, columns=['_id', '_id2'])]
            datafiles_pairs = pd.concat(frames, ignore_index=True)

        datafiles_df.index = datafiles_df.datafile_id

        # get study accession
        prj = self.submission_helper.get_study_accessions()
        if not prj:
            message = 'Project accession not found!'
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        project_accession = prj[0].get('accession', str())

        # get sample accessions
        sample_accessions = self.submission_helper.get_sample_accessions()
        if not sample_accessions:
            message = 'Sample accessions not found!'
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        # store file submission error
        submission_errors = list()

        # create submission context - where all
        try:
            if not os.path.exists(self.submission_context):
                os.makedirs(self.submission_context)
        except Exception as e:
            message = 'Error creating submission context ' + self.submission_context + ": " + str(e)
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        # get instruments
        instruments = COPOLookup(data_source='sequencing_instrument').broker_data_source()

        for indx in range(len(datafiles_pairs)):
            file1_id = datafiles_pairs.iloc[indx]['_id']
            file2_id = datafiles_pairs.iloc[indx]['_id2']

            files_pair = list()

            if file1_id:
                files_pair.append(datafiles_df.loc[file1_id, :])

            if file2_id:
                files_pair.append(datafiles_df.loc[file2_id, :])

            if not files_pair:
                continue

            # collate submission metadata

            # set sample accession
            s_accession = [x['sample_accession'] for x in sample_accessions if
                           x['sample_id'] == files_pair[0]['study_samples']]

            if not s_accession:
                accession_error = 'Sample accession not found for datafiles: ' + str(
                    [file_meta['datafile_name'] for file_meta in files_pair])
                ghlper.logging_error(accession_error, self.submission_id)
                submission_errors.append(accession_error)
                continue

            sample_accession = s_accession[0]

            # get submission name
            submission_name = self.project_alias + "_reads_" + files_pair[0].datafile_id

            # get sequencing instrument
            sequencing_instrument = files_pair[
                0].sequencing_instrument if 'sequencing_instrument' in datafile_columns else ''

            # get library source
            library_source = files_pair[0].library_source if 'library_source' in datafile_columns else ''

            # get library selection
            library_selection = files_pair[0].library_selection if 'library_selection' in datafile_columns else ''

            # get library_strategy
            library_strategy = files_pair[0].library_strategy if 'library_strategy' in datafile_columns else ''

            # get description
            library_description = files_pair[0].library_description if 'library_description' in datafile_columns else ''

            submission_file_names = list()
            file_paths = list()
            submitted_files_id = list()
            file = files_pair[0]
            file_paths.append(file.datafile_location)
            submission_file_names.append(file.datafile_name)
            submitted_files_id.append(file.datafile_id)
            if len(files_pair) > 1:
                file = files_pair[1]
                file_paths.append(file.datafile_location)
                submission_file_names.append(file.datafile_name)
                submitted_files_id.append(file.datafile_id)

            # create manifest
            submission_location = os.path.join(self.submission_context, submission_name)
            try:
                if not os.path.exists(submission_location):
                    os.makedirs(submission_location)
            except Exception as e:
                message = 'Error creating submission location ' + ": " + str(e)
                ghlper.logging_error(message, self.submission_id)
                submission_errors.append(message)
                continue

            submission_message = f'Transferring {str(submission_file_names)} to remote location...'
            ghlper.logging_info(submission_message, self.submission_id)
            ghlper.update_submission_status(status='info', message=submission_message, submission_id=self.submission_id)

            if not self.ftp_transfer_handler(local_paths=file_paths, remote_location=submission_name):
                continue

            # construct experiment xml
            experiment_root = etree.parse(SRA_EXPERIMENT_TEMPLATE, xml_parser).getroot()

            # add experiment node to experiment set
            experiment_node = etree.SubElement(experiment_root, 'EXPERIMENT')
            experiment_alias = "copo-reads-" + submission_name
            experiment_node.set("alias", experiment_alias)
            experiment_node.set("center_name", self.sra_settings["sra_center"])

            study_attributes = self.submission_helper.get_study_descriptors()
            etree.SubElement(experiment_node, 'TITLE').text = study_attributes.get("title", submission_name)
            etree.SubElement(experiment_node, 'STUDY_REF').set("accession", project_accession)

            # design
            experiment_design_node = etree.SubElement(experiment_node, 'DESIGN')
            etree.SubElement(experiment_design_node, 'DESIGN_DESCRIPTION').text = library_description
            etree.SubElement(experiment_design_node, 'SAMPLE_DESCRIPTOR').set("accession", sample_accession)

            # descriptor
            experiment_library_descriptor_node = etree.SubElement(experiment_design_node, 'LIBRARY_DESCRIPTOR')
            etree.SubElement(experiment_library_descriptor_node, 'LIBRARY_STRATEGY').text = library_strategy
            etree.SubElement(experiment_library_descriptor_node, 'LIBRARY_SOURCE').text = library_source
            etree.SubElement(experiment_library_descriptor_node, 'LIBRARY_SELECTION').text = library_selection

            experiment_library_layout_node = etree.SubElement(experiment_library_descriptor_node, 'LIBRARY_LAYOUT')
            if len(files_pair) == 1:
                etree.SubElement(experiment_library_layout_node, 'SINGLE')
            else:
                etree.SubElement(experiment_library_layout_node, 'PAIRED')

            # platform
            inst_plat = [inst['platform'] for inst in instruments if inst['value'] == sequencing_instrument]

            if len(inst_plat):
                experiment_platform_node = etree.SubElement(experiment_node, 'PLATFORM')
                experiment_platform_type_node = etree.SubElement(experiment_platform_node, inst_plat[0])
                etree.SubElement(experiment_platform_type_node, 'INSTRUMENT_MODEL').text = sequencing_instrument

            # write experiement xml
            result = self.write_xml_file(location=submission_location, xml_object=experiment_root,
                                         file_name="experiment.xml")

            if result['status'] is False:
                submission_errors.append(result['message'])
                continue

            experiement_xml_path = result['value']

            # construct run xml
            run_root = etree.parse(SRA_RUN_TEMPLATE, xml_parser).getroot()

            # add run to run set
            run_node = etree.SubElement(run_root, 'RUN')
            run_node.set("alias", experiment_alias)
            run_node.set("center_name", self.sra_settings["sra_center"])
            etree.SubElement(run_node, 'TITLE').text = study_attributes.get("title", submission_name)
            etree.SubElement(run_node, 'EXPERIMENT_REF').set("refname", experiment_alias)

            run_data_block_node = etree.SubElement(run_node, 'DATA_BLOCK')
            run_files_node = etree.SubElement(run_data_block_node, 'FILES')

            for file in files_pair:
                run_file_node = etree.SubElement(run_files_node, 'FILE')
                run_file_node.set("filename", os.path.join(submission_name, file.datafile_name))
                run_file_node.set("filetype", "fastq")
                run_file_node.set("checksum", file.datafile_hash)
                run_file_node.set("checksum_method", "MD5")

            # write run xml
            result = self.write_xml_file(location=submission_location, xml_object=run_root,
                                         file_name="run.xml")

            if result['status'] is False:
                submission_errors.append(result['message'])
                continue

            run_xml_path = result['value']

            # submit xmls to ENA service
            curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                       + ' -F "SUBMISSION=@' \
                       + submission_xml_path \
                       + '" -F "EXPERIMENT=@' \
                       + experiement_xml_path \
                       + '" -F "RUN=@' \
                       + run_xml_path \
                       + '" "' + self.ena_service \
                       + '"'

            ghlper.logging_info(
                "Submitting EXPERIMENT and RUN XMLs for " + str(
                    submission_file_names) + " using CURL. CURL command is: " + curl_cmd.replace(self.pass_word,
                                                                                                 "xxxxxx"),
                self.submission_id)

            try:
                receipt = subprocess.check_output(curl_cmd, shell=True)
            except Exception as e:
                message = 'API call error ' + str(e)
                ghlper.logging_error(message, self.submission_id)
                submission_errors.append(message)
                continue

            receipt_root = etree.fromstring(receipt)

            if receipt_root.get('success') == 'false':
                result['status'] = False
                result['message'] = "Submission error for datafiles: " + str(submission_file_names)
                errors = receipt_root.findall('.//ERROR')
                if errors:
                    error_text = str()
                    for e in errors:
                        error_text = error_text + " \n" + e.text

                    result['message'] = result['message'] + error_text

                # log error
                ghlper.logging_error(result['message'], self.submission_id)

                submission_errors.append(result['message'])
                continue

            # retrieve and save accessions
            self.write_xml_file(location=submission_location, xml_object=receipt_root, file_name="receipt.xml")
            ghlper.logging_info("Saving EXPERIMENT and RUN accessions to the database", self.submission_id)
            run_dict = dict(
                accession=receipt_root.find('RUN').get('accession', default=str()),
                alias=receipt_root.find('RUN').get('alias', default=str()),
                datafiles=submitted_files_id
            )

            experiment_dict = dict(
                accession=receipt_root.find('EXPERIMENT').get('accession', default=str()),
                alias=receipt_root.find('EXPERIMENT').get('alias', default=str()),
            )

            submission_record = collection_handle.find_one({"_id": ObjectId(self.submission_id)},
                                             {"accessions": 1})
            if submission_record:
                accessions = submission_record.get("accessions", dict())

                previous_run = accessions.get('run', list())
                previous_run.append(run_dict)
                accessions['run'] = previous_run

                previous_exp = accessions.get('experiment', list())
                previous_exp.append(experiment_dict)
                accessions['experiment'] = previous_exp

                submission_record['accessions'] = accessions

                collection_handle.update(
                    {"_id": ObjectId(self.submission_id)},
                    {'$set': submission_record})

        # completion formalities
        if submission_errors:
            result['status'] = False
            result['message'] = submission_errors
        else:
            # do post submission clean-up

            # get updated run accessions
            run_accessions = self.submission_helper.get_run_accessions()

            submitted_files = [x for y in run_accessions for x in y.get('datafiles', list())]

            # filter out submitted files from datafiles_df
            datafiles_df = datafiles_df[~datafiles_df.datafile_id.isin(submitted_files)]

            if not len(datafiles_df):
                # all files have been successfully submitted, finalise submission
                self.finalise_submission()

        return result

    def _submit_datafiles_cli(self, submission_xml_path=str()):
        """
        function handles the submission of datafiles using ENA CLI
        :param submission_xml_path:
        :return:
        """

        collection_handle = ghlper.get_submission_handle()
        log_message = "Preparing datafiles for submission..."
        ghlper.logging_info(log_message, self.submission_id)
        ghlper.update_submission_status(status='info', message=log_message, submission_id=self.submission_id)

        result = dict(status=True, value='')
        xml_parser = etree.XMLParser(remove_blank_text=True)

        # read in datafiles
        try:
            datafiles_df = pd.read_csv(os.path.join(self.submission_location, "datafiles.csv"))
        except Exception as e:
            message = 'Datafiles information not found ' + str(e)
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        if not len(datafiles_df):
            # no further datafiles to submit, finalise submission
            self.finalise_submission()
            return dict(status=True, value='')

        # set default for nans
        datafile_columns = datafiles_df.columns
        for k in datafile_columns:
            datafiles_df[k].fillna('', inplace=True)

        # create location for submission files -  ena-cli only accepts a single file path
        try:
            if not os.path.exists(self.datafiles_dir):
                os.makedirs(self.datafiles_dir)
        except Exception as e:
            message = 'Error creating file location ' + self.datafiles_dir + ": " + str(e)
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        # compose the cli command to use
        manifest_location = os.path.join(self.submission_location, "manifest.txt")
        cli_cmd = self.get_cli_command(manifest_location=manifest_location)
        ghlper.logging_info("CURL command is: " + cli_cmd.replace(self.pass_word, "xxxxxx"),
                            self.submission_id)

        # get run accessions - these provide info on already submitted datafiles
        run_accessions = self.submission_helper.get_run_accessions()

        submitted_files = [x for y in run_accessions for x in y.get('datafiles', list())]

        # filter out submitted files from datafiles_df
        datafiles_df = datafiles_df[~datafiles_df.datafile_id.isin(submitted_files)]

        if not len(datafiles_df):
            # no further datafiles to submit, finalise submission
            self.finalise_submission()
            return dict(status=True, value='')

        # get pairing info
        datafiles_pairs = pd.DataFrame(self.submission_helper.get_pairing_info(), columns=['_id', '_id2'])

        # filter datafiles_pairs based on submitted_files and datafiles_df
        # i.e. if any of the paired files has been submitted, then remove the paired record
        if len(datafiles_pairs):
            datafiles_pairs = datafiles_pairs[
                ~((datafiles_pairs['_id'].isin(submitted_files)) | (datafiles_pairs['_id2'].isin(submitted_files)))]

        datafile_ids = list(datafiles_df.datafile_id)

        # ...also, it's a valid pair if both files in a pair are in datafiles_df
        if len(datafiles_pairs):
            datafiles_pairs = datafiles_pairs[
                (datafiles_pairs['_id'].isin(datafile_ids)) & (datafiles_pairs['_id2'].isin(datafile_ids))]

        # datafiles will be submitted on the following guideline:
        # if a datafile is marked as paired, but no pairing information is found (in datafiles_pairs),
        # the datafile will be submitted as a single file

        left_right_pair = list(datafiles_pairs['_id']) + list(datafiles_pairs['_id2'])
        unpaired_datafiles = [x for x in datafile_ids if x not in left_right_pair]

        if unpaired_datafiles:
            unpaired_datafiles = [[x, ''] for x in unpaired_datafiles]
            frames = [datafiles_pairs, pd.DataFrame(unpaired_datafiles, columns=['_id', '_id2'])]
            datafiles_pairs = pd.concat(frames, ignore_index=True)

        datafiles_df.index = datafiles_df.datafile_id

        # get study accession
        prj = self.submission_helper.get_study_accessions()
        if not prj:
            message = 'Project accession not found!'
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        project_accession = ['STUDY', prj[0]['accession']]

        # get sample accessions
        sample_accessions = self.submission_helper.get_sample_accessions()
        if not sample_accessions:
            message = 'Sample accessions not found!'
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        # store file submission error
        submission_errors = list()

        for indx in range(len(datafiles_pairs)):
            file1_id = datafiles_pairs.iloc[indx]['_id']
            file2_id = datafiles_pairs.iloc[indx]['_id2']

            files_pair = list()

            if file1_id:
                files_pair.append(datafiles_df.loc[file1_id, :])

            if file2_id:
                files_pair.append(datafiles_df.loc[file2_id, :])

            if not files_pair:
                continue

            # collate submission metadata
            reads_metadata = list()

            # set study accession
            reads_metadata.append(project_accession)

            # set sample accession
            s_accession = [x['sample_accession'] for x in sample_accessions if
                           x['sample_id'] == files_pair[0]['study_samples']]

            if not s_accession:
                accession_error = 'Sample accession not found for datafiles: ' + str(
                    [file_meta['datafile_name'] for file_meta in files_pair])
                ghlper.logging_error(accession_error, self.submission_id)
                submission_errors.append(accession_error)
                continue

            reads_metadata.append(['SAMPLE', s_accession[0]])

            # set submission name
            submission_name = self.project_alias + "_reads_" + files_pair[0].datafile_id
            reads_metadata.append(['NAME', submission_name])

            # set sequencing instrument
            if 'sequencing_instrument' in datafile_columns:
                reads_metadata.append(['INSTRUMENT', files_pair[0].sequencing_instrument])

            # set library source
            if 'library_source' in datafile_columns:
                reads_metadata.append(['LIBRARY_SOURCE', files_pair[0].library_source])

            # set library selection
            if 'library_selection' in datafile_columns:
                reads_metadata.append(['LIBRARY_SELECTION', files_pair[0].library_selection])

            # set library_strategy
            if 'library_strategy' in datafile_columns:
                reads_metadata.append(['LIBRARY_STRATEGY', files_pair[0].library_strategy])

            # set description
            if 'library_description' in datafile_columns:
                reads_metadata.append(['DESCRIPTION', files_pair[0].library_description])

            # set file name - The following file name fields are supported in the manifest file:
            #
            #     BAM: Single BAM file
            #     CRAM: Single CRAM file
            #     FASTQ: Single fastq file
            # reads_metadata.append(['FASTQ', ntpath.basename(files_pair[0].datafile_location)])
            # if len(files_pair) > 1:
            #     reads_metadata.append(['FASTQ', ntpath.basename(files_pair[1].datafile_location)])

            submission_file_names = list()
            submitted_files_id = list()
            file = files_pair[0]
            reads_metadata.append(['FASTQ', file.datafile_location])
            submission_file_names.append(file.datafile_name)
            submitted_files_id.append(file.datafile_id)
            if len(files_pair) > 1:
                file = files_pair[1]
                reads_metadata.append(['FASTQ', file.datafile_location])
                submission_file_names.append(file.datafile_name)
                submitted_files_id.append(file.datafile_id)

            # generate manifest file
            manifest = pd.DataFrame(reads_metadata)
            manifest.to_csv(manifest_location, sep='\t', header=False, index=False)

            # copy target datafile(s) to submission location
            # existing_files = [ntpath.basename(name) for name in glob.glob(os.path.join(self.datafiles_dir, "*.*"))]
            # copy_errors = list()
            # submission_file_names = list()
            # submitted_files_id = list()
            # for file_meta in files_pair:
            #     submission_file_names.append(file_meta.datafile_name)
            #     submitted_files_id.append(file_meta.datafile_id)
            #     if ntpath.basename(file_meta.datafile_location) not in existing_files:
            #         try:
            #             shutil.copy(file_meta.datafile_location, self.datafiles_dir)
            #         except Exception as e:
            #             message = "Error copying datafile " + file_meta.datafile_name + " " + str(e)
            #             copy_errors.append(message)
            #
            # if len(copy_errors):
            #     ghlper.logging_error(str(copy_errors))
            #     submission_errors.extend(copy_errors)
            #     continue

            submission_message = "Submitting: " + str(submission_file_names)
            ghlper.logging_info(submission_message, self.submission_id)
            ghlper.update_submission_status(status='info', message=submission_message, submission_id=self.submission_id)

            try:
                thread = pexpect.spawn(cli_cmd, timeout=None)
                cpl = thread.compile_pattern_list([pexpect.EOF, '(.+)'])

                while True:
                    i = thread.expect_list(cpl, timeout=None)
                    if i == 0:  # signals end of transfer
                        # retrieve submission receipt
                        output_path = os.path.join(self.submission_location, 'reads', submission_name, 'submit',
                                                   'receipt.xml')
                        receipt_xml = [x for x in glob.glob(output_path)]

                        if receipt_xml:
                            receipt_root = etree.parse(receipt_xml[0], xml_parser).getroot()

                            if receipt_root.get('success') == 'true':
                                run_dict = dict(
                                    accession=receipt_root.find('RUN').get('accession', default=str()),
                                    alias=receipt_root.find('RUN').get('alias', default=str()),
                                    datafiles=submitted_files_id
                                )

                                experiment_dict = dict(
                                    accession=receipt_root.find('EXPERIMENT').get('accession', default=str()),
                                    alias=receipt_root.find('EXPERIMENT').get('alias', default=str()),
                                )

                                doc = collection_handle.find_one({"_id": ObjectId(self.submission_id)},
                                                                 {"accessions": 1})
                                if doc:
                                    submission_record = doc
                                    accessions = submission_record.get("accessions", dict())

                                    previous_run = accessions.get('run', list())
                                    previous_run.append(run_dict)
                                    accessions['run'] = previous_run

                                    previous_exp = accessions.get('experiment', list())
                                    previous_exp.append(experiment_dict)
                                    accessions['experiment'] = previous_exp

                                    submission_record['accessions'] = accessions
                                    submission_record['target_id'] = str(submission_record.pop('_id'))

                                    collection_handle.update(
                                        {"_id": ObjectId(str(submission_record.pop('_id')))},
                                        {'$set': submission_record})
                            else:
                                datafile_error = "Submission error for datafiles: " + str(submission_file_names)
                                errors = receipt_root.findall('.//ERROR')
                                if errors:
                                    for e in errors:
                                        datafile_error = datafile_error + " \n" + e.text

                                # log error
                                ghlper.logging_error(datafile_error, self.submission_id)
                                submission_errors.append(datafile_error)
                        break
                    elif i == 1:
                        pexp_match = thread.match.group(1)
                        tokens_to_match = ["INFO", "ERROR"]

                        if any(tm in pexp_match.decode("utf-8") for tm in tokens_to_match):
                            tokens = pexp_match.decode("utf-8")

                            if tokens.startswith("INFO :"):
                                ghlper.logging_info(tokens[7:], self.submission_id)
                            elif tokens.startswith("ERROR:"):
                                t_message = tokens[7:]
                                ghlper.logging_error(t_message, self.submission_id)
                                submission_errors.append(t_message)
                            else:
                                ghlper.logging_info(tokens, self.submission_id)
                thread.close()
            except Exception as e:
                message = 'API call error ' + str(e)
                ghlper.logging_error(message, self.submission_id)
                submission_errors.append(message)

        if submission_errors:
            result['status'] = False
            result['message'] = submission_errors
        else:
            # do post submission clean-up

            # get updated run accessions
            run_accessions = self.submission_helper.get_run_accessions()

            submitted_files = [x for y in run_accessions for x in y.get('datafiles', list())]

            # filter out submitted files from datafiles_df
            datafiles_df = datafiles_df[~datafiles_df.datafile_id.isin(submitted_files)]

            if not len(datafiles_df):
                # all files have been successfully submitted, finalise submission
                self.finalise_submission()

        return result

    def get_cli_command(self, manifest_location=str()):
        """
        function composes the command line interface command to use for datafiles submission
        :param manifest_location:
        :return:
        """

        test_service = ''
        if 'wwwdev' in self.ena_service:  # using ena's test service
            test_service = ' -test '
            ghlper.logging_info("This is a test submission", self.submission_id)

        # todo with -inputdir set - ENA currently claims we don't need this, but doesn't work otherwise
        # cli_cmd = 'java -Xmx2048m -jar ' + ENA_CLI + ' -context reads -userName ' + self.user_token + \
        #           ' -password ' + self.pass_word + ' -manifest ' + manifest_location + test_service + ' -submit -centerName ' + \
        #           self.sra_settings["sra_center"] + ' -inputDir ' + self.datafiles_dir + ' -ascp '

        cli_cmd = 'java -Xmx2048m -jar ' + ENA_CLI + ' -context reads -userName ' + self.user_token + \
                  ' -password ' + self.pass_word + ' -manifest ' + manifest_location + test_service + ' -submit -centerName ' + \
                  self.sra_settings["sra_center"] + ' -ascp '

        return cli_cmd

    def finalise_submission(self):
        """
        function runs final steps to complete the submission
        :return:
        """

        # all files have been successfully submitted
        log_message = "Finalising submission..."
        ghlper.logging_info(log_message, self.submission_id)
        ghlper.update_submission_status(status='info', message=log_message, submission_id=self.submission_id)

        # remove submission files folder
        try:
            shutil.rmtree(self.datafiles_dir)
        except Exception as e:
            message = "Error removing files folder: " + str(e)
            ghlper.logging_error(message, self.submission_id)

        # mark submission as complete
        collection_handle = ghlper.get_submission_handle()
        submission_record = dict(complete=True, completed_on=d_utils.get_datetime())
        collection_handle.update(
            {"_id": ObjectId(self.submission_id)},
            {'$set': submission_record})

        # update submission status
        status_message = "Submission marked as complete!"
        ghlper.logging_info(status_message, self.submission_id)
        ghlper.update_submission_status(status='info', message=status_message, submission_id=self.submission_id)

        # clear any existing submission error
        ghlper.update_submission_status(submission_id=self.submission_id)

        return True

    def write_xml_file(self, location=str(), xml_object=None, file_name=str()):
        """
        function writes xml to the specified location or to a default one
        :param location:
        :param xml_object:
        :param file_name:
        :return:
        """

        result = dict(status=True, value='')

        output_location = self.submission_location
        if location:
            output_location = location

        xml_file_path = os.path.join(output_location, file_name)
        tree = etree.ElementTree(xml_object)

        try:
            tree.write(xml_file_path, encoding="utf8", xml_declaration=True, pretty_print=True)
        except Exception as e:
            message = 'Error writing xml file ' + file_name + ": " + str(e)
            ghlper.logging_error(message, self.submission_id)
            result['message'] = message
            result['status'] = False

            return result

        message = file_name + ' successfully written to  ' + xml_file_path
        ghlper.logging_info(message, self.submission_id)

        result['value'] = xml_file_path

        return result

    def release_study(self):
        """
        function makes the study public
        :return:
        """

        # instantiate helper object - performs most auxiliary tasks associated with the submission
        self.submission_helper = SubmissionHelper(submission_id=self.submission_id)

        # clear any existing submission error
        ghlper.update_submission_status(submission_id=self.submission_id)

        # submission location
        self.submission_location = self.create_submission_location()

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.parse(SRA_SUBMISSION_MODIFY_TEMPLATE, parser).getroot()
        actions = root.find('ACTIONS')
        action = etree.SubElement(actions, 'ACTION')

        # get study accession
        prj_accession = str()
        collection_handle = self.submission_helper.collection_handle
        doc = collection_handle.find_one({"_id": ObjectId(self.submission_id)}, {"accessions": 1})

        if doc:
            submission_record = doc
            prj = submission_record.get('accessions', dict()).get('project', [{}])
            prj_accession = prj[0].get("accession", str())

        if not prj_accession:
            message = 'Project accession not found!'
            ghlper.logging_error(message, self.submission_id)
            result = dict(status=False, value='', message=message)
            return result

        ghlper.logging_info('Releasing study with accession: ' + prj_accession, self.submission_id)

        action_type = etree.SubElement(action, 'RELEASE')
        action_type.set("target", prj_accession)

        context = self.write_xml_file(xml_object=root, file_name="submission_modify.xml")

        if context['status'] is False:
            ghlper.update_submission_status(status='error', message=context.get("message", str()),
                                            submission_id=self.submission_id)
            return context

        submission_xml_path = context['value']

        result = dict(status=True, value='')

        # compose curl command for study release
        curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                   + ' -F "SUBMISSION=@' \
                   + submission_xml_path \
                   + '" "' + self.ena_service \
                   + '"'

        ghlper.logging_info(
            "Modifying study via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx"),
            self.submission_id)

        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
        except Exception as e:
            message = 'API call error ' + str(e)
            ghlper.logging_error(message, self.submission_id)
            result['message'] = message
            result['status'] = False

            return result

        root = etree.fromstring(receipt)

        if root.get('success') == 'false':
            result['status'] = False
            result['message'] = "Couldn't release STUDY due to the following errors: "
            errors = root.findall('.//ERROR')
            if errors:
                error_text = str()
                for e in errors:
                    error_text = error_text + " \n" + e.text

                result['message'] = result['message'] + error_text

            # log error
            ghlper.logging_error(result['message'], self.submission_id)

            return result

        # update submission record with study status
        self.write_xml_file(xml_object=root, file_name="submission_receipt.xml")
        ghlper.logging_info("Study successfully released. Updating status in the database",
                            self.submission_id)
        prj[0]['status'] = 'PUBLIC'
        prj[0]['release_date'] = d_utils.get_datetime()

        collection_handle.update(
            {"_id": ObjectId(str(submission_record.pop('_id')))},
            {'$set': submission_record})

        # update submission status
        status_message = "Study release successful."
        ghlper.update_submission_status(status='info', message=status_message, submission_id=self.submission_id)

        result = dict(status=True, value='', message=status_message)
        return result

    def update_study_status(self):
        """
        function updates the embargo status of studies
        :return:
        """

        # this manages its own mongodb connection as it will be accessed by a celery worker subprocess
        mongo_client = mutil.get_mongo_client()
        collection_handle = mongo_client['SubmissionCollection']

        records = cursor_to_list(collection_handle.find({"$and": [
            {"repository": "ena", "complete": True, 'deleted': d_utils.get_not_deleted_flag()},
            {'accessions.project.0': {"$exists": True}}]},
            {'accessions.project': 1}))

        status_message = "Checking for ENA Study status updates " + str(len(records))
        ghlper.log_general_info(status_message)
        #
        # if submissions:
        #     pass

        result = dict(status=True, value='')

        return result

    def delete_submission(self):
        """
        function deletes submission: can only delete non-submitted submission
        :return:
        """

        # todo: to delete submission record, delete or also cancel the already registered project and samples on ENA

        return True

    def ftp_transfer_handler(self, local_paths=list(), remote_location=str()):
        """
        function transfers file to ENA using ftp
        :param local_paths: paths to file in the local system
        :param remote_location: remote folder
        :return:
        """

        with closing(ftplib.FTP(self.webin_domain)) as ftp:
            try:
                ftp.login(self.user_token, self.pass_word)

                if remote_location not in ftp.nlst():
                    ftp.mkd(remote_location)

            except ftplib.all_errors as e:
                message = 'FTP error:' + str(e)
                ghlper.logging_error(message, self.submission_id)
                return False

            ftp.cwd(remote_location)

            for f_path in local_paths:
                try:
                    with open(f_path, 'rb') as fp:
                        filename = ntpath.basename(f_path)
                        res = ftp.storlines("STOR " + filename, fp)
                        if not res.startswith('226 Transfer complete'):
                            message = f'Upload of {filename} failed!'
                            ghlper.logging_error(message, self.submission_id)
                            return False

                except ftplib.all_errors as e:
                    message = 'FTP error:' + str(e)
                    ghlper.logging_error(message, self.submission_id)
                    return False

        return True

    def aspera_transfer_handler(self):
        """
        function transfers file to ENA using aspera
        :return:
        """

        # get aspera library
        # path2library = os.path.join(BASE_DIR, REPOSITORIES['ASPERA']['resource_path'])
        # webin_user = resolve_env.get_env('WEBIN_USER')

        # f_str = ' '.join(file_paths)
        # aspera_cmd = f'./ascp -d -QT -l700M -L- {f_str} {webin_user}:{submission_name}'
        # message = "Aspera command: " + aspera_cmd
        # ghlper.logging_info(message, self.submission_id)
        # ghlper.logging_info(path2library, self.submission_id)
        # os.chdir(path2library)

        # try:
        #     thread = pexpect.spawn(aspera_cmd, timeout=None)
        #     thread.expect(["assword:", pexpect.EOF])
        #     thread.sendline(self.pass_word)
        #
        #     cpl = thread.compile_pattern_list([pexpect.EOF, '(.+)'])
        #
        #     while True:
        #         i = thread.expect_list(cpl, timeout=None)
        #         if i == 0:  # EOF! Possible error point if encountered before transfer completion
        #             print("Process termination - check exit status!")
        #             break
        #         elif i == 1:
        #             pexp_match = thread.match.group(1)
        #             tokens_to_match = ["status=success"]
        #
        #             if any(tm in pexp_match.decode("utf-8") for tm in tokens_to_match):
        #                 tokens = pexp_match.decode("utf-8").split(" ")
        #
        #                 # file successfully transferred
        #                 if 'status=success' in tokens:
        #                     submission_message = f'Successfully transferred {str(submission_file_names)}'
        #                     ghlper.logging_info(submission_message, self.submission_id)
        #
        #     thread.close()
        # except Exception as e:
        #     message = 'File transfer error ' + str(e)
        #     ghlper.logging_error(message, self.submission_id)
        #     submission_errors.append(message)
        #
        #     continue

        return True
