__author__ = 'felix.shaw@tgac.ac.uk - 03/05/2016'

import converters.ena.copo_isa_ena as cnv
from bson.json_util import dumps
from tools import resolve_env
from django.conf import settings
from dal.copo_da import DataFile
from dal.copo_da import RemoteDataFile, Submission, Profile

from web.apps.web_copo.lookup.copo_enums import *

import xml.etree.ElementTree as ET

from isatools.convert import json2sra
from isatools import isajson

import subprocess, os, pexpect

from datetime import datetime

from django.shortcuts import redirect
from django.http import HttpRequest

REPOSITORIES = settings.REPOSITORIES
BASE_DIR = settings.BASE_DIR
lg = settings.LOGGER
from web.apps.web_copo.lookup.lookup import SRA_SETTINGS
import web.apps.web_copo.schemas.utils.data_utils as d_utils


class EnaSubmit(object):
    def __init__(self):
        self._dir = os.path.join(os.path.dirname(__file__), "data")
        self._config_dir = os.path.join(self._dir, "Configurations/isaconfig-default_v2015-07-02")
        self.d_files = []
        self.profile = str()
        self.submission = dict()

    def submit(self, sub_id, dataFile_ids):

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
            mongo_file = DataFile().get_record(f_id)
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

        submission_status = True

        if not submission_status or submission_status == 'false':

            lg.log('Starting aspera transfer', level=Loglvl.INFO, type=Logtype.FILE)

            kwargs = dict(target_id=sub_id, commenced_on=str(datetime.now()))
            Submission().save_record(dict(), **kwargs)

            # k is a loop counter which keeps track of the number of files transfered
            k = -1
            f_str = str()
            for f in file_path:
                f_str = f_str + ' ' + f
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
                        tokens_to_match = ["Mb/s"]
                        units_to_match = ["KB", "MB"]
                        time_units = ['d', 'h', 'm', 's']
                        end_of_transfer = False

                        if all(tm in pexp_match.decode("utf-8") for tm in tokens_to_match):
                            fields = {
                                "transfer_status": "transferring",
                                "current_time": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                            }

                            tokens = pexp_match.decode("utf-8").split(" ")

                            lg.log(tokens, level=Loglvl.INFO, type=Logtype.FILE)

                            for token in tokens:
                                if not token == '':
                                    if "file" in token:
                                        fields['file_path'] = token.split('=')[-1]
                                        if prev_file != fields['file_path']:
                                            k = k + 1
                                        prev_file == fields['file_path']
                                    elif '%' in token:
                                        pct = float((token.rstrip("%")))
                                        # pct = (1/len(file_path) * pct) + (k * 1/len(file_path) * 100)
                                        fields['pct_completed'] = pct
                                        # flag end of transfer
                                        print(str(transfer_token) + ":  " + str(pct) + '% transfered')
                                        if token.rstrip("%") == 100:
                                            end_of_transfer = True
                                    elif any(um in token for um in units_to_match):
                                        fields['amt_transferred'] = token
                                    elif "Mb/s" in token or "Mbps" in token:
                                        t = token[:-4]
                                        if '=' in t:
                                            fields['transfer_rate'] = t[t.find('=') + 1:]
                                        else:
                                            fields['transfer_rate'] = t
                                    elif "status" in token:
                                        fields['transfer_status'] = token.split('=')[-1]
                                    elif "rate" in token:
                                        fields['transfer_rate'] = token.split('=')[-1]
                                    elif "elapsed" in token:
                                        fields['elapsed_time'] = token.split('=')[-1]
                                    elif "loss" in token:
                                        fields['bytes_lost'] = token.split('=')[-1]
                                    elif "size" in token:
                                        fields['file_size_bytes'] = token.split('=')[-1]

                                    elif "ETA" in token:
                                        eta = tokens[-2]
                                        estimated_completion = ""
                                        eta_split = eta.split(":")
                                        t_u = time_units[-len(eta_split):]
                                        for indx, eta_token in enumerate(eta.split(":")):
                                            if eta_token == "00":
                                                continue
                                            estimated_completion += eta_token + t_u[indx] + " "
                                        fields['estimated_completion'] = estimated_completion
                            RemoteDataFile().update_transfer(transfer_token, fields)

                kwargs = dict(target_id=sub_id, completed_on=datetime.now())
                Submission().save_record(dict(), **kwargs)
                # close thread
                thread.close()
                lg.log('Aspera Transfer completed', level=Loglvl.INFO, type=Logtype.FILE)

            except OSError:
                return redirect('web.apps.web_copo.views.goto_error', request=HttpRequest(),
                                message='There appears to be an issue with EBI.')
            finally:
                pass

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
        json2sra.convert2(json_fp=open(json_file_path), path=conv_dir, sra_settings=sra_settings,
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
        user_token = user_token.split("@")[0]
        ena_uri = "https://www-test.ebi.ac.uk/ena/submit/drop-box/submit/?auth=ENA%20{user_token!s}%20{pass_word!s}".format(
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

        xml = ET.fromstring(output)

        accessions = dict()

        # first check for errors
        errors = xml.findall('*/ERROR')
        if errors:
            error_text = str()
            for e in errors:
                error_text = error_text + e.text
            return error_text

        # get project accessions
        project = xml.find('./PROJECT')
        project_accession = project.get('accession', default='undefined')
        project_alias = project.get('alias', default='undefined')
        accessions['project'] = {'accession': project_accession, 'alias': project_alias}

        # get experiment accessions
        experiment = xml.find('./EXPERIMENT')
        experiment_accession = experiment.get('accession', default='undefined')
        experiment_alias = experiment.get('alias', default='undefined')
        accessions['experiment'] = {'accession': experiment_accession, 'alias': experiment_alias}

        # get submission accessions
        submission = xml.find('./SUBMISSION')
        submission_accession = submission.get('accession', default='undefined')
        submission_alias = submission.get('alias', default='undefined')
        accessions['submission'] = {'accession': submission_accession, 'alias': submission_alias}

        # get run accessions
        run = xml.find('./RUN')
        run_accession = run.get('accession', default='undefined')
        run_alias = run.get('alias', default='undefined')
        accessions['run'] = {'accession': run_accession, 'alias': run_alias}

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

        # save accessions to mongo profile record
        s = Submission().get_record(sub_id)
        s['accessions'] = accessions
        s['complete'] = True
        s['target_id'] = str(s.pop('_id'))
        Submission().save_record(dict(), **s)
        RemoteDataFile().delete_transfer(transfer_token)
        return True
