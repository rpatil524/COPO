__author__ = 'etuka'
__date__ = '27 March 2019'

import os
import glob
import shutil
import ntpath
import pexpect
import subprocess
import pandas as pd
from lxml import etree
from tools import resolve_env
from dal.copo_da import Submission
from datetime import datetime
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
from submission.helpers.ena_helper import SubmissionHelper
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.lookup.lookup import SRA_SUBMISSION_TEMPLATE, SRA_PROJECT_TEMPLATE, SRA_SAMPLE_TEMPLATE, \
    SRA_SUBMISSION_MODIFY_TEMPLATE, ENA_CLI

"""
class handles read data submissions to the ENA - see: https://ena-docs.readthedocs.io/en/latest/cli_06.html
"""


class EnaReads:
    def __init__(self, submission_id=str()):
        self.submission_id = submission_id
        self.project_alias = self.submission_id
        self.ena_service = resolve_env.get_env('ENA_SERVICE')
        self.pass_word = resolve_env.get_env('WEBIN_USER_PASSWORD')
        self.user_token = resolve_env.get_env('WEBIN_USER').split("@")[0]

        self.submission_helper = None
        self.submission_location = None
        self.sra_settings = None
        self.datafiles_dir = None

    def submit(self):
        """
        function acts as a controller for the submission process
        :return:
        """

        # check submission status
        if str(Submission().isComplete(self.submission_id)).lower() == 'true':  # signal submission completion
            context = dict(status=True, message='This record has been submitted.')
            return context

        # instantiate helper object - performs most auxiliary tasks associated with the submission
        self.submission_helper = SubmissionHelper(submission_id=self.submission_id)

        self.submission_helper.logging_info('Initiating submission...')

        # clear any existing submission error
        self.submission_helper.clear_submission_status()

        # submission location
        self.submission_location = self.create_submission_location()
        self.datafiles_dir = os.path.join(self.submission_location, "files")

        # retrieve sra settings
        self.sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())

        # get submission xml
        context = self._get_submission_xml()

        if context['status'] is False:
            self.submission_helper.add_submission_error(context.get("message", str()))
            return context

        submission_xml_path = context['value']

        # register project
        if not self.submission_helper.get_study_accessions():

            context = self._register_project(submission_xml_path=submission_xml_path)

            if context['status'] is False:
                self.submission_helper.add_submission_error(context.get("message", str()))
                return context

        # register samples
        context = self._register_samples(submission_xml_path=submission_xml_path)
        if context['status'] is False:
            self.submission_helper.add_submission_error(context.get("message", str()))
            return context

        # submit datafiles
        context = self._submit_datafiles()
        if context['status'] is False:
            self.submission_helper.add_submission_error(context.get("message", str()))
            return context

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
            self.submission_helper.logging_error(message)
            raise

        self.submission_helper.logging_info('Created submission location: ' + conv_dir)

        return conv_dir

    def _get_submission_xml(self):
        """
        function creates and return submission xml path
        :return:
        """

        # create submission xml
        self.submission_helper.logging_info("Creating submission xml...")

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

    def _register_project(self, submission_xml_path=str()):
        """
        function creates and submits project (study) xml
        :return:
        """

        # create project xml
        log_message = "Registering project..."
        self.submission_helper.logging_info(log_message)
        self.submission_helper.add_submission_info(log_message)

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

        # write project xml
        result = self.write_xml_file(root, "project.xml")
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

        self.submission_helper.logging_info("Submitting project xml to ENA via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx"))

        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
        except Exception as e:
            message = 'API call error ' + str(e)
            self.submission_helper.logging_error(message)
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
            self.submission_helper.logging_error(result['message'])

            return result

        # save project accession
        self.write_xml_file(root, "project_receipt.xml")
        self.submission_helper.logging_info("Saving project accessions to the database")
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

        submission_record = Submission().get_record(self.submission_id)
        accessions = submission_record.get("accessions", dict())
        accessions['project'] = project_accessions
        submission_record['accessions'] = accessions

        submission_record['target_id'] = str(submission_record.pop('_id'))
        Submission().save_record(dict(), **submission_record)

        # update submission status
        status_message = "Project successfully registered, and accessions saved."
        self.submission_helper.add_submission_info(status_message)

        return dict(status=True, value='')

    def _register_samples(self, submission_xml_path=str()):
        """
        function creates and submits sample xml
        :return:
        """

        result = dict(status=True, value='')

        # create sample xml
        log_message = "Registering samples..."
        self.submission_helper.logging_info(log_message)
        self.submission_helper.add_submission_info(log_message)

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
            self.submission_helper.logging_info(log_message)
            self.submission_helper.add_submission_info(log_message)

            return dict(status=True, value='')

        sra_df = pd.DataFrame(sra_samples)
        sra_df.index = sra_df['sample_alias']

        # write sample xml
        result = self.write_xml_file(root, "sample.xml")
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

        self.submission_helper.logging_info("Submitting samples xml to ENA via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx"))

        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
        except Exception as e:
            message = 'API call error ' + str(e)
            self.submission_helper.logging_error(message)
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
            self.submission_helper.logging_error(result['message'])

            return result

        # save sample accession
        self.write_xml_file(root, "samples_receipt.xml")
        self.submission_helper.logging_info("Saving samples accessions to the database")
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

        submission_record = Submission().get_record(self.submission_id)
        accessions = submission_record.get("accessions", dict())
        previous = accessions.get('sample', list())
        previous.extend(sample_accessions)
        accessions['sample'] = previous
        submission_record['accessions'] = accessions

        submission_record['target_id'] = str(submission_record.pop('_id'))
        Submission().save_record(dict(), **submission_record)

        # update submission status
        status_message = "Samples successfully registered, and accessions saved."
        self.submission_helper.add_submission_info(status_message)

        return dict(status=True, value='')

    def _submit_datafiles(self):
        """
        function handles the submission of datafiles
        :return:
        """

        log_message = "Preparing datafiles for submission..."
        self.submission_helper.logging_info(log_message)
        self.submission_helper.add_submission_info(log_message)

        result = dict(status=True, value='')
        xml_parser = etree.XMLParser(remove_blank_text=True)

        # read in datafiles
        try:
            datafiles_df = pd.read_csv(os.path.join(self.submission_location, "datafiles.csv"))
        except Exception as e:
            message = 'Datafiles information not found ' + str(e)
            self.submission_helper.logging_error(message)
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
            self.submission_helper.logging_error(message)
            result = dict(status=False, value='', message=message)
            return result

        # compose the cli command to use
        manifest_location = os.path.join(self.submission_location, "manifest.txt")
        cli_cmd = self.get_cli_command(manifest_location=manifest_location)
        self.submission_helper.logging_info("CURL command is: " + cli_cmd.replace(self.pass_word, "xxxxxx"))

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
            self.submission_helper.logging_error(message)
            result = dict(status=False, value='', message=message)
            return result

        project_accession = ['STUDY', prj[0]['accession']]

        # get sample accessions
        sample_accessions = self.submission_helper.get_sample_accessions()
        if not sample_accessions:
            message = 'Sample accessions not found!'
            self.submission_helper.logging_error(message)
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
                self.submission_helper.logging_error(accession_error)
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
            reads_metadata.append(['FASTQ', ntpath.basename(files_pair[0].datafile_location)])
            if len(files_pair) > 1:
                reads_metadata.append(['FASTQ', ntpath.basename(files_pair[1].datafile_location)])

            # generate manifest file
            manifest = pd.DataFrame(reads_metadata)
            manifest.to_csv(manifest_location, sep='\t', header=False, index=False)

            # copy target datafile(s) to submission location
            existing_files = [ntpath.basename(name) for name in glob.glob(os.path.join(self.datafiles_dir, "*.*"))]
            copy_errors = list()
            submission_file_names = list()
            submitted_files_id = list()
            for file_meta in files_pair:
                submission_file_names.append(file_meta.datafile_name)
                submitted_files_id.append(file_meta.datafile_id)
                if ntpath.basename(file_meta.datafile_location) not in existing_files:
                    try:
                        shutil.copy(file_meta.datafile_location, self.datafiles_dir)
                    except Exception as e:
                        message = "Error copying datafile " + file_meta.datafile_name + " " + str(e)
                        copy_errors.append(message)

            if len(copy_errors):
                self.submission_helper.logging_error(str(copy_errors))
                submission_errors.extend(copy_errors)
                continue

            submission_message = "Submitting: " + str(submission_file_names)
            self.submission_helper.logging_info(submission_message)
            self.submission_helper.add_submission_info(submission_message)

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

                                submission_record = Submission().get_record(self.submission_id)
                                accessions = submission_record.get("accessions", dict())

                                previous_run = accessions.get('run', list())
                                previous_run.append(run_dict)
                                accessions['run'] = previous_run

                                previous_exp = accessions.get('experiment', list())
                                previous_exp.append(experiment_dict)
                                accessions['experiment'] = previous_exp

                                submission_record['accessions'] = accessions
                                submission_record['target_id'] = str(submission_record.pop('_id'))

                                Submission().save_record(dict(), **submission_record)
                            else:
                                datafile_error = "Submission error for datafiles: " + str(submission_file_names)
                                errors = receipt_root.findall('.//ERROR')
                                if errors:
                                    for e in errors:
                                        datafile_error = datafile_error + " \n" + e.text

                                # log error
                                self.submission_helper.logging_error(datafile_error)
                                submission_errors.append(datafile_error)
                        break
                    elif i == 1:
                        pexp_match = thread.match.group(1)
                        tokens_to_match = ["INFO", "ERROR"]

                        if any(tm in pexp_match.decode("utf-8") for tm in tokens_to_match):
                            tokens = pexp_match.decode("utf-8")

                            if tokens.startswith("INFO :"):
                                self.submission_helper.logging_info(tokens[7:])
                            elif tokens.startswith("ERROR:"):
                                t_message = tokens[7:]
                                self.submission_helper.logging_error(t_message)
                                submission_errors.append(t_message)
                            else:
                                self.submission_helper.logging_info(tokens)
                thread.close()
            except Exception as e:
                message = 'API call error ' + str(e)
                self.submission_helper.logging_error(message)
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
            self.submission_helper.logging_info("This is a test submission")

        cli_cmd = 'java -Xmx2048m -jar ' + ENA_CLI + ' -context reads -userName ' + self.user_token + \
                  ' -password ' + self.pass_word + ' -manifest ' + manifest_location + test_service + ' -submit -centerName ' + \
                  self.sra_settings["sra_center"] + ' -inputDir ' + self.datafiles_dir + ' -ascp '

        return cli_cmd

    def finalise_submission(self):
        """
        function runs final steps to complete the submission
        :return:
        """

        # all files have been successfully submitted
        log_message = "Finalising submission..."
        self.submission_helper.logging_info(log_message)
        self.submission_helper.add_submission_info(log_message)

        # remove submission files folder
        try:
            shutil.rmtree(self.datafiles_dir)
        except Exception as e:
            message = "Error removing files folder: " + str(e)
            self.submission_helper.logging_error(message)

        # mark submission as complete
        submission_record = Submission().get_record(self.submission_id)
        submission_record['complete'] = True
        submission_record['completed_on'] = datetime.now()

        submission_record['target_id'] = str(submission_record.pop('_id'))
        Submission().save_record(dict(), **submission_record)

        # update submission status
        status_message = "Submission marked as complete!"
        self.submission_helper.logging_info(status_message)
        self.submission_helper.add_submission_info(status_message)

        # clear any existing submission error
        self.submission_helper.clear_submission_status()

        return True

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
            message = 'Error writing xml file ' + file_name + ": " + str(e)
            self.submission_helper.logging_error(message)
            result['message'] = message
            result['status'] = False

            return result

        message = file_name + ' successfully written to  ' + xml_file_path
        self.submission_helper.logging_info(message)

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
        self.submission_helper.clear_submission_status()

        # submission location
        self.submission_location = self.create_submission_location()

        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.parse(SRA_SUBMISSION_MODIFY_TEMPLATE, parser).getroot()
        actions = root.find('ACTIONS')
        action = etree.SubElement(actions, 'ACTION')

        # get study accession
        submission_record = Submission().get_record(self.submission_id)
        prj = submission_record.get('accessions', dict()).get('project', [{}])
        prj_accession = prj[0].get("accession", str())

        if not prj_accession:
            message = 'Project accession not found!'
            self.submission_helper.logging_error(message)
            result = dict(status=False, value='', message=message)
            return result

        self.submission_helper.logging_info('Releasing study with accession: ' + prj_accession)

        action_type = etree.SubElement(action, 'RELEASE')
        action_type.set("target", prj_accession)

        context = self.write_xml_file(root, "submission_modify.xml")

        if context['status'] is False:
            self.submission_helper.add_submission_error(context.get("message", str()))
            return context

        submission_xml_path = context['value']

        result = dict(status=True, value='')

        # compose curl command for study release
        curl_cmd = 'curl -u ' + self.user_token + ':' + self.pass_word \
                   + ' -F "SUBMISSION=@' \
                   + submission_xml_path \
                   + '" "' + self.ena_service \
                   + '"'

        self.submission_helper.logging_info("Modifying study via CURL. CURL command is: " + curl_cmd.replace(self.pass_word, "xxxxxx"))

        try:
            receipt = subprocess.check_output(curl_cmd, shell=True)
        except Exception as e:
            message = 'API call error ' + str(e)
            self.submission_helper.logging_error(message)
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
            self.submission_helper.logging_error(result['message'])

            return result

        # update submission record with study status
        self.write_xml_file(root, "submission_receipt.xml")
        self.submission_helper.logging_info("Study successfully released. Updating status in the database")
        prj[0]['status'] = 'PUBLIC'
        prj[0]['release_date'] = d_utils.get_datetime()

        submission_record['target_id'] = str(submission_record.pop('_id'))
        Submission().save_record(dict(), **submission_record)

        # update submission status
        status_message = "Study release successful."
        self.submission_helper.add_submission_info(status_message)

        result = dict(status=True, value='', message=status_message)
        return result
