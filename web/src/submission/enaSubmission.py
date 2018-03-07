__author__ = 'felix.shaw@tgac.ac.uk - 03/05/2016'

import json
from bson import json_util
import converters.ena.copo_isa_ena as cnv
from bson import ObjectId
from bson.json_util import dumps
from tools import resolve_env
from django.conf import settings
from dal.copo_da import DataFile
from dal.copo_da import RemoteDataFile, Submission, Profile

from web.apps.web_copo.lookup.copo_enums import *

from hurry.filesize import size, alternative
import xml.etree.ElementTree as ET

from isatools.convert import json2sra
from isatools import isajson

import subprocess, os, pexpect

from datetime import datetime

REPOSITORIES = settings.REPOSITORIES
BASE_DIR = settings.BASE_DIR
lg = settings.LOGGER
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
import web.apps.web_copo.schemas.utils.data_utils as d_utils


# please note!!! There's now a separate class to handle submission of raw reads sequence, called: EnaSubmit4Reads

class EnaSubmit(object):
    def __init__(self):
        self._dir = os.path.join(os.path.dirname(__file__), "data")
        self.d_files = []
        self.profile = str()
        self.submission = dict()

    def submit(self, sub_id, dataFile_ids):
        submission_record = Submission().get_record(sub_id)

        # bundle_meta, if present, should provide a better picture of what datafiles need to be uploaded
        if "bundle_meta" in submission_record:
            pending_files = [x["file_id"] for x in submission_record['bundle_meta'] if not x["upload_status"]]
            dataFile_ids = pending_files

        # physically transfer files
        path2library = os.path.join(BASE_DIR, REPOSITORIES['ASPERA']['resource_path'])

        # change these to be collected properly
        user_name = REPOSITORIES['ASPERA']['user_token']
        password = REPOSITORIES['ASPERA']['password']

        # create transfer record
        transfer_token = RemoteDataFile().create_transfer(sub_id)['_id']
        self.submission = Submission().get_record(sub_id)

        self.profile = Profile().get_record(self.submission['profile_id'])
        remote_path = d_utils.get_ena_remote_path(sub_id)

        # get each file in the bundle
        file_path = []
        for idx, f_id in enumerate(dataFile_ids):
            mongo_file = DataFile().get_record(ObjectId(f_id))
            self.d_files.append(mongo_file)
            file_path.append(mongo_file.get("file_location", str()))

        case = self._do_aspera_transfer(transfer_token=transfer_token,
                                        user_name=user_name,
                                        password=password,
                                        remote_path=remote_path,
                                        file_path=file_path,
                                        path2library=path2library,
                                        sub_id=sub_id)
        return case

    def _do_aspera_transfer(self, transfer_token=None, user_name=None, password=None, remote_path=None, file_path=None,
                            path2library=None, sub_id=None):

        # check submission status
        submission_status = Submission().isComplete(sub_id)

        if str(submission_status).lower() == 'true':  # submission already done
            RemoteDataFile().delete_transfer(transfer_token)
            return True

        if file_path:  # there are files to be uploaded to ENA's Dropbox

            lg.log('Starting aspera transfer', level=Loglvl.INFO, type=Logtype.FILE)

            kwargs = dict(target_id=sub_id, commenced_on=str(datetime.now()))
            Submission().save_record(dict(), **kwargs)

            f_str = ' '.join(file_path)
            cmd = "./ascp -d -QT -l700M -L- {f_str!s} {user_name!s}:{remote_path!s}".format(**locals())
            lg.log(cmd, level=Loglvl.INFO, type=Logtype.FILE)
            os.chdir(path2library)

            try:
                thread = pexpect.spawn(cmd, timeout=None)
                thread.expect(["assword:", pexpect.EOF])
                thread.sendline(password)

                cpl = thread.compile_pattern_list([pexpect.EOF, '(.+)'])

                while True:
                    i = thread.expect_list(cpl, timeout=None)
                    if i == 0:  # EOF! Possible error point if encountered before transfer completion
                        print("Process termination - check exit status!")
                        break
                    elif i == 1:
                        pexp_match = thread.match.group(1)
                        prev_file = ''
                        tokens_to_match = ["Mb/s", "status=success", "status=started"]
                        units_to_match = ["KB", "MB", "GB"]
                        rates_to_match = ["Kb/s", "kb/s", "Mb/s", "mb/s", "Gb/s", "gb/s"]
                        time_units = ['d', 'h', 'm', 's']
                        end_of_transfer = False

                        if any(tm in pexp_match.decode("utf-8") for tm in tokens_to_match):
                            transfer_fields = dict()
                            tokens = pexp_match.decode("utf-8").split(" ")
                            lg.log(tokens, level=Loglvl.INFO, type=Logtype.FILE)

                            # has a file transfer started?
                            if 'status=started' in tokens:
                                # get the target file and update transfer record
                                target_file = [tk for tk in tokens if tk[:5] == "file=" or tk[:7] == "source="]

                                for up_f in target_file:
                                    up_f_1 = up_f.split("=")[1].strip('"')

                                    # update file path and datafile id
                                    transfer_fields["file_path"] = up_f_1

                                    submission_record = Submission().get_record(sub_id)
                                    bundle_meta = submission_record.get("bundle_meta", list())

                                    listed_file = [indx for indx, elem in enumerate(bundle_meta) if
                                                   elem['file_path'] == up_f_1]

                                    if listed_file:
                                        transfer_fields["datafile_id"] = bundle_meta[listed_file[0]]["file_id"]

                                # get original file size
                                file_size_bytes = [x for x in tokens if len(x) > 5 and x[:4] == 'size']
                                if file_size_bytes:
                                    t = file_size_bytes[0].split("=")[1]
                                    transfer_fields["file_size_bytes"] = size(int(t), system=alternative)

                            # extract other file transfer metadata
                            if 'ETA' in tokens:
                                # get %completed, bytes transferred, current time etc
                                pct_completed = [x for x in tokens if len(x) > 1 and x[-1] == '%']
                                if pct_completed:
                                    transfer_fields["pct_completed"] = pct_completed[0][:-1]
                                    print(
                                        str(transfer_token) + ":  " + transfer_fields[
                                            "pct_completed"] + '% transferred')

                                # bytes transferred
                                bytes_transferred = [x for x in tokens if len(x) > 2 and x[-2:] in units_to_match]
                                if bytes_transferred:
                                    transfer_fields["bytes_transferred"] = bytes_transferred[0]

                                # transfer rate
                                transfer_rate = [x for x in tokens if len(x) > 4 and x[-4:] in rates_to_match]
                                if transfer_rate:
                                    transfer_fields["transfer_rate"] = transfer_rate[0]

                                # current time - this will serve as the last time an activity was recorded
                                transfer_fields["current_time"] = datetime.now().strftime(
                                    "%d-%m-%Y %H:%M:%S")

                            # has a file been successfully transferred?
                            if 'status=success' in tokens:
                                # get the target file and update its status in the submission record
                                target_file = [tk for tk in tokens if tk[:5] == "file=" or tk[:7] == "source="]

                                for up_f in target_file:
                                    up_f_1 = up_f.split("=")[1].strip('"')
                                    submission_record = Submission().get_record(sub_id)

                                    bundle_meta = submission_record.get("bundle_meta", list())
                                    listed_file = [indx for indx, elem in enumerate(bundle_meta) if
                                                   elem['file_path'] == up_f_1]
                                    if listed_file:
                                        bundle_meta[listed_file[0]]["upload_status"] = True
                                        kwargs = dict(target_id=sub_id, bundle_meta=bundle_meta)
                                        Submission().save_record(dict(), **kwargs)

                                        # is this the final file to be transferred?
                                        submission_record = Submission().get_record(sub_id)
                                        if "bundle_meta" in submission_record:
                                            pending_files = [x["file_id"] for x in submission_record['bundle_meta'] if
                                                             not x["upload_status"]]

                                            if not pending_files:  # we are all done!
                                                transfer_fields["transfer_status"] = "completed"
                                                transfer_fields["pct_completed"] = '100'
                                                transfer_fields["current_time"] = datetime.now().strftime(
                                                    "%d-%m-%Y %H:%M:%S")

                            # save collected metadata to the transfer record
                            RemoteDataFile().update_transfer(transfer_token, transfer_fields)

                # commenting this out since, technically, submission is yet to be completed at this point
                # kwargs = dict(target_id=sub_id, completed_on=datetime.now())
                # Submission().save_record(dict(), **kwargs)
                # close thread
                thread.close()
                lg.log('Aspera Transfer completed', level=Loglvl.INFO, type=Logtype.FILE)


            except OSError:
                transfer_fields = dict()
                transfer_fields["error"] = "Encountered problems with file upload."
                transfer_fields["current_time"] = datetime.now().strftime(
                    "%d-%m-%Y %H:%M:%S")

                # save error to transfer record
                RemoteDataFile().update_transfer(transfer_token, transfer_fields)
                return False
            finally:
                pass

        else:  # no files to be uploaded
            transfer_fields = dict()
            transfer_fields["transfer_status"] = "completed"
            transfer_fields["pct_completed"] = '100'
            transfer_fields["current_time"] = datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S")

            # save collected metadata to the transfer record
            RemoteDataFile().update_transfer(transfer_token, transfer_fields)

        # setup paths for conversion directories
        if self.submission['repository'] == 'ena':
            return self.do_seq_reads_submission(sub_id, remote_path, transfer_token)
        elif self.submission['repository'] == 'ena-ant':
            return self.do_annotation_submission(sub_id, remote_path, transfer_token)

    def do_seq_reads_submission(self, sub_id, remote_path, transfer_token):
        # # setup paths for conversion directories
        conv_dir = os.path.join(self._dir, sub_id)
        if not os.path.exists(os.path.join(conv_dir, 'json')):
            os.makedirs(os.path.join(conv_dir, 'json'))
        json_file_path = os.path.join(conv_dir, 'json', 'isa_json.json')
        xml_dir = conv_dir
        xml_path = os.path.join(xml_dir, 'run_set.xml')
        #
        # #  Convert COPO JSON to ISA JSON
        # lg.log('Obtaining ISA-JSON', level=Loglvl.INFO, type=Logtype.FILE)
        conv = cnv.Investigation(submission_token=sub_id)
        meta = conv.get_schema()
        json_file = open(json_file_path, '+w')
        # # dump metadata to output file
        json_file.write(dumps(meta))
        json_file.close()

        # Validate ISA_JSON
        lg.log('Validating ISA-JSON', level=Loglvl.INFO, type=Logtype.FILE)

        with open(json_file_path) as json_file:
            v = isajson.validate(json_file)
            lg.log(v, level=Loglvl.INFO, type=Logtype.FILE)

        # convert to SRA with isatools converter
        lg.log('Converting to SRA', level=Loglvl.INFO, type=Logtype.FILE)
        sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())
        datafilehashes = conv.get_datafilehashes()
        json2sra.convert(json_fp=open(json_file_path), path=conv_dir, sra_settings=sra_settings,
                         datafilehashes=datafilehashes, validate_first=False)

        # finally submit to SRA
        lg.log('Submitting XMLS to ENA via CURL', level=Loglvl.INFO, type=Logtype.FILE)
        submission_file = os.path.join(xml_dir, 'submission.xml')
        project_file = os.path.join(xml_dir, 'project_set.xml')
        sample_file = os.path.join(xml_dir, 'sample_set.xml')
        experiment_file = os.path.join(xml_dir, 'experiment_set.xml')
        run_file = os.path.join(xml_dir, 'run_set.xml')

        # "https://www-test.ebi.ac.uk"
        # "https://www.ebi.ac.uk"
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

        output = subprocess.check_output(curl_cmd, shell=True)
        lg.log(output, level=Loglvl.INFO, type=Logtype.FILE)
        lg.log("Extracting fields from receipt", level=Loglvl.INFO, type=Logtype.FILE)

        accessions = self.get_accessions(output, sub_id, transfer_token)

        return True

    def do_annotation_submission(self, sub_id, remote_path, transfer_token):
        from submission import ena_xml_util as xml
        study = xml.do_study_xml(sub_id)
        sample = xml.do_sample_xml(sub_id)
        analysis = xml.do_analysis_xml(sub_id)
        submission = xml.do_submission_xml(sub_id)

        xml_dir = os.path.join(self._dir, sub_id)
        if not os.path.exists(os.path.join(xml_dir)):
            os.makedirs(os.path.join(xml_dir))

        with open(os.path.join(xml_dir, 'study.xml'), "w") as ff:
            ff.write(study)
        with open(os.path.join(xml_dir, 'sample.xml'), "w") as ff:
            ff.write(str(sample))
        with open(os.path.join(xml_dir, 'analysis.xml'), "w") as ff:
            ff.write(analysis)
        with open(os.path.join(xml_dir, 'submission.xml'), "w") as ff:
            ff.write(submission)

        pass_word = resolve_env.get_env('WEBIN_USER_PASSWORD')
        user_token = resolve_env.get_env('WEBIN_USER')
        user_token = user_token.split("@")[0]
        ena_uri = "https://www-test.ebi.ac.uk/ena/submit/drop-box/submit/?auth=ENA%20{user_token!s}%20{pass_word!s}".format(
            **locals())

        curl_cmd = 'curl -k -F "SUBMISSION=@' + os.path.join(xml_dir,
                                                             'submission.xml') + '" -F "ANALYSIS=@' + os.path.join(
            xml_dir, 'analysis.xml') + '" -F "STUDY=@' + os.path.join(xml_dir, 'study.xml') + '" "' + ena_uri + '"'

        receipt = subprocess.check_output(curl_cmd, shell=True)

        accessions = self.get_accessions(receipt, sub_id, transfer_token)

        lg.log(receipt, level=Loglvl.INFO, type=Logtype.FILE)
        lg.log("Extracting fields from receipt", level=Loglvl.INFO, type=Logtype.FILE)

        return True

    def get_accessions(self, reciept, sub_id, transfer_token=None):
        xml = ET.fromstring(reciept)

        accessions = dict()

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
            RemoteDataFile().update_transfer(transfer_token, transfer_fields)
            return False

        # get project accessions
        project = xml.find('./PROJECT')
        if project is not None:
            project_accession = project.get('accession', default='undefined')
            project_alias = project.get('alias', default='undefined')
            accessions['project'] = {'accession': project_accession, 'alias': project_alias}
        projects = xml.findall('./PROJECT')
        project_accessions = list()
        for project in projects:
            project_accession = project.get('accession', default='undefined')
            project_alias = project.get('alias', default='undefined')
            project_accessions.append(dict(accession=project_accession, alias=project_alias))
        accessions['project'] = project_accessions

        # get experiment accessions
        experiments = xml.findall('./EXPERIMENT')
        if experiments is not None:
            experiment_accessions = list()
            for experiment in experiments:
                experiment_accession = experiment.get('accession', default='undefined')
                experiment_alias = experiment.get('alias', default='undefined')
                experiment_accessions.append(dict(accession=experiment_accession, alias=experiment_alias))
            accessions['experiment'] = experiment_accessions

        # get submission accessions
        submissions = xml.findall('./SUBMISSION')
        if submissions is not None:
            submission_accessions = list()
            for submission in submissions:
                submission_accession = submission.get('accession', default='undefined')
                submission_alias = submission.get('alias', default='undefined')
                submission_accessions.append(dict(accession=submission_accession, alias=submission_alias))
            accessions['submission'] = submission_accessions

        # get run accessions
        runs = xml.findall('./RUN')
        if runs is not None:
            run_accessions = list()
            for run in runs:
                run_accession = run.get('accession', default='undefined')
                run_alias = run.get('alias', default='undefined')
                run_accessions.append(dict(accession=run_accession, alias=run_alias))
            accessions['run'] = run_accessions

        # get sample accessions
        samples = xml.findall('./SAMPLE')
        if samples is not None:
            sample_accessions = list()
            for sample in samples:
                sample_accession = sample.get('accession', default='undefined')
                sample_alias = sample.get('alias', default='undefined')
                s = {'sample_accession': sample_accession, 'sample_alias': sample_alias}
                for bio_s in sample:
                    s['biosample_accession'] = bio_s.get('accession', default='undefined')
                sample_accessions.append(s)
            accessions['sample'] = sample_accessions

        # save accessions to mongo record
        s = Submission().get_record(sub_id)
        s['accessions'] = accessions
        s['complete'] = True
        s['completed_on'] = datetime.now()
        s['target_id'] = str(s.pop('_id'))

        Submission().save_record(dict(), **s)

        RemoteDataFile().delete_transfer(transfer_token)


# ************************ Submission for ENA Sequence Reads  *************************#
# The following class handles submission for raw sequence reads
# It divides the submission process to callable micro-tasks to overcome request timeout issues


class EnaSubmit4Reads(object):
    def __init__(self, submission_id=str(), status=str()):
        """
        the submission module breaks tasks into smaller 'callable' chunks to deal with the gunicorn timeout issue
        :param submission_id: the submission id
        :param status: the current status or stage the submission has reached
        """
        self._dir = os.path.join(os.path.dirname(__file__), "data")
        self.d_files = []
        self.submission_id = submission_id
        self.transfer_token = str()
        self.context = dict()
        self.status = status  # status or the execution stage the submission has reached
        self.dispatcher = {
            'commenced': self._do_file_transfer,
            'files_transferred': self._do_collate_copo_records,
            'collated_records': self._get_assay_schema,
            'generated_assay_schema': self._get_study_schema,
            'generated_study_schema': self._do_copojson2isajson,
            'generated_isajson': self._convert_to_sra,
            'converted_to_sra': self._submit_to_sra
        }
        self.submission_sequence = ["commenced",
                                    "files_transferred",
                                    "collated_records",
                                    "generated_assay_schema",
                                    "generated_study_schema",
                                    "generated_isajson",
                                    "converted_to_sra",
                                    "completed"]

    def submit(self):
        # check submission status
        submission_status = Submission().isComplete(self.submission_id)

        if str(submission_status).lower() == 'true':  # submission already done, terminate process
            self.context["ena_status"] = "completed"

            return

        # if there is an existing transfer token, reuse it
        rem = RemoteDataFile().get_by_sub_id(self.submission_id)
        if rem:
            self.transfer_token = str(rem["_id"])
        else:
            # create a transfer record
            self.transfer_token = RemoteDataFile().create_transfer(self.submission_id)['_id']

        # get the next action in the sequence of submission tasks
        next_stage_indx = 0
        try:
            next_stage_indx = self.submission_sequence.index(self.status)
        except:
            # no valid stage, flag error and terminate
            self.update_process_time()
            self.context["ena_status"] = "error"
            return self.context

        # check for completed stage
        if self.submission_sequence[next_stage_indx] == "completed":
            self.context["ena_status"] = "completed"
        else:
            self.dispatcher[self.submission_sequence[next_stage_indx]]()  # dispatch the next task

        self.update_process_time()
        return self.context

    def update_process_time(self):
        rem = RemoteDataFile().get_by_sub_id(self.submission_id)
        if rem:
            transfer_fields = dict()
            transfer_fields["current_time"] = datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S")

            # save error to transfer record
            RemoteDataFile().update_transfer(self.transfer_token, transfer_fields)

    def _get_output_paths(self):
        # setup paths for conversion directories
        conv_dir = os.path.join(self._dir, self.submission_id)
        if not os.path.exists(os.path.join(conv_dir, 'json')):
            os.makedirs(os.path.join(conv_dir, 'json'))
        json_file_path = os.path.join(conv_dir, 'json', 'isa_json.json')
        assay_file_path = os.path.join(conv_dir, 'json', 'assay.json')
        study_file_path = os.path.join(conv_dir, 'json', 'study.json')

        return dict(json_file_path=json_file_path,
                    assay_file_path=assay_file_path,
                    study_file_path=study_file_path,
                    xml_dir=conv_dir,
                    conv_dir=conv_dir,
                    remote_path=d_utils.get_ena_remote_path(self.submission_id)
                    )

    def _do_collate_copo_records(self):
        """
        collates relevant copo records to be used in deriving the submission components
        :return:
        """

        lg.log('Collating COPO records', level=Loglvl.INFO, type=Logtype.FILE)

        collated_records = cnv.ISAHelpers().broker_copo_records(submission_token=self.submission_id)
        submission_record = Submission().get_record(self.submission_id)
        transcript = submission_record["transcript"]
        transcript["collated_records"] = json.dumps(collated_records, default=json_util.default)

        kwargs = dict(target_id=self.submission_id, transcript=transcript)
        Submission().save_record(dict(), **kwargs)

        self.context["ena_status"] = "collated_records"

        return

    def _get_assay_schema(self):
        lg.log('Composing Assay schema', level=Loglvl.INFO, type=Logtype.FILE)

        submission_record = Submission().get_record(self.submission_id)

        collated_records = submission_record["transcript"]["collated_records"]
        collated_records = json.loads(collated_records, object_hook=json_util.object_hook)

        assay_schema = cnv.Assay(copo_isa_records=collated_records).get_schema()
        assay_file = open(self._get_output_paths()["assay_file_path"], '+w')

        # dump generated json to output file
        assay_file.write(dumps(assay_schema))
        assay_file.close()

        self.context["ena_status"] = "generated_assay_schema"

        return

    def _get_study_schema(self):
        lg.log('Composing Study schema', level=Loglvl.INFO, type=Logtype.FILE)

        submission_record = Submission().get_record(self.submission_id)

        collated_records = submission_record["transcript"]["collated_records"]
        collated_records = json.loads(collated_records, object_hook=json_util.object_hook)

        # retrieve stored assay schema and pass along
        assay_schema = d_utils.json_to_pytype(self._get_output_paths()["assay_file_path"])

        study_schema = cnv.Study(copo_isa_records=collated_records, assay_schema=assay_schema).get_schema()
        study_file = open(self._get_output_paths()["study_file_path"], '+w')

        # dump generated json to output file
        study_file.write(dumps(study_schema))
        study_file.close()

        self.context["ena_status"] = "generated_study_schema"

        return

    def _do_copojson2isajson(self):
        """
        converts copo json to isa json
        :return:
        """
        lg.log('Obtaining ISA-JSON', level=Loglvl.INFO, type=Logtype.FILE)
        submission_record = Submission().get_record(self.submission_id)

        collated_records = submission_record["transcript"]["collated_records"]
        collated_records = json.loads(collated_records, object_hook=json_util.object_hook)

        # retrieve stored study schema and pass along
        study_schema = d_utils.json_to_pytype(self._get_output_paths()["study_file_path"])

        copo_isa_object = cnv.Investigation(copo_isa_records=collated_records, study_schema=study_schema)
        generated_json = copo_isa_object.get_schema()

        json_file = open(self._get_output_paths()["json_file_path"], '+w')

        # dump generated json to output file
        json_file.write(dumps(generated_json))
        json_file.close()

        self.context["ena_status"] = "generated_isajson"

        return

    def validate_isajson(self):
        lg.log('Validating ISA-JSON', level=Loglvl.INFO, type=Logtype.FILE)
        paths = self._get_output_paths()
        with open(paths["json_file_path"]) as json_file:
            v = isajson.validate(json_file)
            lg.log(v, level=Loglvl.INFO, type=Logtype.FILE)

        return

    def _convert_to_sra(self):
        self.validate_isajson()

        lg.log('Converting to SRA', level=Loglvl.INFO, type=Logtype.FILE)
        sra_settings = d_utils.json_to_pytype(SRA_SETTINGS).get("properties", dict())
        submission_record = Submission().get_record(self.submission_id)

        collated_records = submission_record["transcript"]["collated_records"]
        collated_records = json.loads(collated_records, object_hook=json_util.object_hook)
        datafilehashes = collated_records["datafilehashes"]

        paths = self._get_output_paths()

        json2sra.convert(json_fp=open(paths["json_file_path"]), path=paths["conv_dir"], sra_settings=sra_settings,
                         datafilehashes=datafilehashes, validate_first=False)

        self.context["ena_status"] = "converted_to_sra"
        return

    def _submit_to_sra(self):
        lg.log('Submitting XMLS to ENA via CURL', level=Loglvl.INFO, type=Logtype.FILE)
        paths = self._get_output_paths()
        xml_dir = paths["xml_dir"]
        remote_path = paths["xml_dir"]

        submission_file = os.path.join(xml_dir, 'submission.xml')
        project_file = os.path.join(xml_dir, 'project_set.xml')
        sample_file = os.path.join(xml_dir, 'sample_set.xml')
        experiment_file = os.path.join(xml_dir, 'experiment_set.xml')
        run_file = os.path.join(xml_dir, 'run_set.xml')

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

        return self._do_save_accessions(xml)

    def _do_save_accessions(self, xml):
        lg.log('Retrieving and saving accessions to database', level=Loglvl.INFO, type=Logtype.FILE)

        accessions = dict()

        # get project accessions
        projects = xml.findall('./PROJECT')
        project_accessions = list()
        for project in projects:
            project_accession = project.get('accession', default='undefined')
            project_alias = project.get('alias', default='undefined')
            project_accessions.append(dict(accession=project_accession, alias=project_alias))
        accessions['project'] = project_accessions

        # get experiment accessions
        experiments = xml.findall('./EXPERIMENT')
        experiment_accessions = list()
        for experiment in experiments:
            experiment_accession = experiment.get('accession', default='undefined')
            experiment_alias = experiment.get('alias', default='undefined')
            experiment_accessions.append(dict(accession=experiment_accession, alias=experiment_alias))
        accessions['experiment'] = experiment_accessions

        # get submission accessions
        submissions = xml.findall('./SUBMISSION')
        submission_accessions = list()
        for submission in submissions:
            submission_accession = submission.get('accession', default='undefined')
            submission_alias = submission.get('alias', default='undefined')
            submission_accessions.append(dict(accession=submission_accession, alias=submission_alias))
        accessions['submission'] = submission_accessions

        # get run accessions
        runs = xml.findall('./RUN')
        run_accessions = list()
        for run in runs:
            run_accession = run.get('accession', default='undefined')
            run_alias = run.get('alias', default='undefined')
            run_accessions.append(dict(accession=run_accession, alias=run_alias))
        accessions['run'] = run_accessions

        # get sample accessions
        samples = xml.findall('./SAMPLE')
        sample_accessions = list()
        for sample in samples:
            sample_accession = sample.get('accession', default='undefined')
            sample_alias = sample.get('alias', default='undefined')
            s = {'sample_accession': sample_accession, 'sample_alias': sample_alias}
            for bio_s in sample:
                s['biosample_accession'] = bio_s.get('accession', default='undefined')
            sample_accessions.append(s)
        accessions['sample'] = sample_accessions

        # save accessions to mongo record
        submission_record = Submission().get_record(self.submission_id)
        submission_record['accessions'] = accessions
        submission_record['complete'] = True
        submission_record['completed_on'] = datetime.now()
        submission_record['target_id'] = str(submission_record.pop('_id'))
        try:
            del submission_record["transcript"]["collated_records"]
        except:
            pass

        Submission().save_record(dict(), **submission_record)
        RemoteDataFile().delete_transfer(self.transfer_token)

        self.context["ena_status"] = "completed"
        return

    def _do_aspera_transfer(self, user_name=None, password=None, remote_path=None, file_path=None,
                            path2library=None):

        lg.log('Starting aspera transfer', level=Loglvl.INFO, type=Logtype.FILE)

        kwargs = dict(target_id=self.submission_id, commenced_on=str(datetime.now()))
        Submission().save_record(dict(), **kwargs)

        f_str = ' '.join(file_path)
        cmd = "./ascp -d -QT -l700M -L- {f_str!s} {user_name!s}:{remote_path!s}".format(**locals())
        lg.log(cmd, level=Loglvl.INFO, type=Logtype.FILE)
        os.chdir(path2library)

        try:
            thread = pexpect.spawn(cmd, timeout=None)
            thread.expect(["assword:", pexpect.EOF])
            thread.sendline(password)

            cpl = thread.compile_pattern_list([pexpect.EOF, '(.+)'])

            while True:
                i = thread.expect_list(cpl, timeout=None)
                if i == 0:  # EOF! Possible error point if encountered before transfer completion
                    print("Process termination - check exit status!")
                    break
                elif i == 1:
                    pexp_match = thread.match.group(1)
                    prev_file = ''
                    tokens_to_match = ["Mb/s", "status=success", "status=started"]
                    units_to_match = ["KB", "MB", "GB"]
                    rates_to_match = ["Kb/s", "kb/s", "Mb/s", "mb/s", "Gb/s", "gb/s"]
                    time_units = ['d', 'h', 'm', 's']
                    end_of_transfer = False

                    if any(tm in pexp_match.decode("utf-8") for tm in tokens_to_match):
                        transfer_fields = dict()
                        tokens = pexp_match.decode("utf-8").split(" ")
                        lg.log(tokens, level=Loglvl.INFO, type=Logtype.FILE)

                        # has a file transfer started?
                        if 'status=started' in tokens:
                            # get the target file and update transfer record
                            target_file = [tk for tk in tokens if tk[:5] == "file=" or tk[:7] == "source="]

                            for up_f in target_file:
                                up_f_1 = up_f.split("=")[1].strip('"')

                                # update file path and datafile id
                                transfer_fields["file_path"] = up_f_1

                                submission_record = Submission().get_record(self.submission_id)
                                bundle_meta = submission_record.get("bundle_meta", list())

                                listed_file = [indx for indx, elem in enumerate(bundle_meta) if
                                               elem['file_path'] == up_f_1]

                                if listed_file:
                                    transfer_fields["datafile_id"] = bundle_meta[listed_file[0]]["file_id"]

                            # get original file size
                            file_size_bytes = [x for x in tokens if len(x) > 5 and x[:4] == 'size']
                            if file_size_bytes:
                                t = file_size_bytes[0].split("=")[1]
                                transfer_fields["file_size_bytes"] = size(int(t), system=alternative)

                        # extract other file transfer metadata
                        if 'ETA' in tokens:
                            # get %completed, bytes transferred, current time etc
                            pct_completed = [x for x in tokens if len(x) > 1 and x[-1] == '%']
                            if pct_completed:
                                transfer_fields["pct_completed"] = pct_completed[0][:-1]
                                print(
                                    str(self.transfer_token) + ":  " + transfer_fields[
                                        "pct_completed"] + "% transferred")

                            # bytes transferred
                            bytes_transferred = [x for x in tokens if len(x) > 2 and x[-2:] in units_to_match]
                            if bytes_transferred:
                                transfer_fields["bytes_transferred"] = bytes_transferred[0]

                            # transfer rate
                            transfer_rate = [x for x in tokens if len(x) > 4 and x[-4:] in rates_to_match]
                            if transfer_rate:
                                transfer_fields["transfer_rate"] = transfer_rate[0]

                            # current time - this will serve as the last time an activity was recorded
                            transfer_fields["current_time"] = datetime.now().strftime(
                                "%d-%m-%Y %H:%M:%S")

                        # has a file been successfully transferred?
                        if 'status=success' in tokens:
                            # get the target file and update its status in the submission record
                            target_file = [tk for tk in tokens if tk[:5] == "file=" or tk[:7] == "source="]

                            for up_f in target_file:
                                up_f_1 = up_f.split("=")[1].strip('"')
                                submission_record = Submission().get_record(self.submission_id)

                                bundle_meta = submission_record.get("bundle_meta", list())
                                listed_file = [indx for indx, elem in enumerate(bundle_meta) if
                                               elem['file_path'] == up_f_1]
                                if listed_file:
                                    bundle_meta[listed_file[0]]["upload_status"] = True
                                    kwargs = dict(target_id=self.submission_id, bundle_meta=bundle_meta)
                                    Submission().save_record(dict(), **kwargs)

                                    # is this the final file to be transferred?
                                    submission_record = Submission().get_record(self.submission_id)
                                    if "bundle_meta" in submission_record:
                                        pending_files = [x["file_id"] for x in submission_record['bundle_meta'] if
                                                         not x["upload_status"]]

                                        if not pending_files:  # we are all done!
                                            transfer_fields["transfer_status"] = "completed"
                                            transfer_fields["pct_completed"] = '100'
                                            transfer_fields["current_time"] = datetime.now().strftime(
                                                "%d-%m-%Y %H:%M:%S")

                        # save collected metadata to the transfer record
                        RemoteDataFile().update_transfer(self.transfer_token, transfer_fields)

            thread.close()
            lg.log('Aspera Transfer completed', level=Loglvl.INFO, type=Logtype.FILE)

        except OSError:
            transfer_fields = dict()
            transfer_fields["error"] = "Encountered problems with file upload."
            transfer_fields["current_time"] = datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S")
            lg.log('File upload error! Submission ID: ' + self.submission_id, level=Loglvl.ERROR, type=Logtype.FILE)

            # save error to transfer record
            RemoteDataFile().update_transfer(self.transfer_token, transfer_fields)
            return False
        finally:
            pass

        self.context["ena_status"] = "files_transferred"
        return

    def _do_file_transfer(self):
        submission_record = Submission().get_record(self.submission_id)

        # what datafiles need to be uploaded?
        pending_files = list()
        if "bundle_meta" in submission_record:
            pending_files = [x["file_id"] for x in submission_record['bundle_meta'] if not x["upload_status"]]

        if pending_files:
            # there are files to be transferred
            path2library = os.path.join(BASE_DIR, REPOSITORIES['ASPERA']['resource_path'])

            user_name = REPOSITORIES['ASPERA']['user_token']
            password = REPOSITORIES['ASPERA']['password']

            remote_path = d_utils.get_ena_remote_path(self.submission_id)

            # get each file in the bundle
            file_path = []
            for idx, f_id in enumerate(pending_files):
                mongo_file = DataFile().get_record(f_id)
                self.d_files.append(mongo_file)
                file_path.append(mongo_file.get("file_location", str()))

            self._do_aspera_transfer(user_name=user_name,
                                     password=password,
                                     remote_path=remote_path,
                                     file_path=file_path,
                                     path2library=path2library)
        else:
            # no files to be uploaded
            transfer_fields = dict()
            transfer_fields["transfer_status"] = "completed"
            transfer_fields["pct_completed"] = '100'
            transfer_fields["current_time"] = datetime.now().strftime(
                "%d-%m-%Y %H:%M:%S")

            # save collected metadata to the transfer record
            RemoteDataFile().update_transfer(self.transfer_token, transfer_fields)

            self.context["ena_status"] = "files_transferred"
        return
