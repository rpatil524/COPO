__author__ = 'felix.shaw@tgac.ac.uk - 03/05/2016'

import converters.ena.copo_isa_ena as cnv

from bson.json_util import dumps
from django.conf import settings
from dal.copo_da import DataFile
from dal.copo_da import RemoteDataFile, Submission, Profile

from web.apps.web_copo.lookup.copo_enums import *

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element

from isatools.convert import json2sra
from isatools import isajson

import subprocess, os, pexpect

from datetime import datetime

from django.shortcuts import redirect
from django.http import HttpResponse, HttpRequest

from django_tools.middlewares import ThreadLocal

REPOSITORIES = settings.REPOSITORIES
BASE_DIR = settings.BASE_DIR
lg = settings.LOGGER


class EnaSubmit(object):

    def __init__(self):
        self._dir = os.path.join(os.path.dirname(__file__), "data")
        self._config_dir = os.path.join(self._dir, "Configurations/isaconfig-default_v2015-07-02")
        self._tmp = os.path.join(self._dir, './tmp/')
        self.d_files = []
        self.profile = str()
        self.submission = dict()
        if not os.path.exists(self._tmp):
            os.mkdir(self._tmp)


    def submit(self, sub_id, dataFile_ids):

        # physically transfer files
        path2library = os.path.join(BASE_DIR, REPOSITORIES['ASPERA']['resource_path'])

        # change these to be collected properly
        user_name = REPOSITORIES['ASPERA']['user_token']
        password = REPOSITORIES['ASPERA']['password']

        #remote_path = REPOSITORIES['ASPERA']['remote_path']



        # create transfer record
        transfer_token = RemoteDataFile().create_transfer(sub_id)['_id']
        self.submission = Submission().get_record(sub_id)

        self.profile = Profile().get_record(self.submission['profile_id'])
        remote_path = os.path.join(sub_id, str(ThreadLocal.get_current_user()))

        # get each file in the bundle
        file_path = []
        for idx, f_id in enumerate(dataFile_ids):
            mongo_file = DataFile().get_record(f_id)
            self.d_files.append(mongo_file)
            file_path.append(mongo_file.get("file_location", str()))

        self._do_aspera_transfer(transfer_token=transfer_token,
                                 user_name='Webin-39233@webin.ebi.ac.uk',
                                 password='Apple123',
                                 remote_path=remote_path,
                                 file_path=file_path,
                                 path2library=path2library,
                                 sub_id=sub_id)



    def _do_aspera_transfer(self, transfer_token=None, user_name=None, password=None, remote_path=None, file_path=None,
                            path2library=None, sub_id=None):



        # check submission status
        if not Submission().isComplete(sub_id):

            lg.log('Starting aspera transfer', level=Loglvl.INFO, type=Logtype.FILE )



            kwargs = dict(target_id=sub_id, commenced_on=str(datetime.now()))
            Submission().save_record(dict(), **kwargs)

            # k is a loop counter which keeps track of the number of files transfered
            k = -1
            f_str = str()
            for f in file_path:
                f_str = f_str + ' ' + f
            cmd = "./ascp -d -QT -l300M -L- {f_str!s} {user_name!s}:{remote_path!s}".format(**locals())
            lg.log(cmd)
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

                kwargs = dict(target_id=sub_id, completed_on=str(datetime.now()))
                Submission().save_record(dict(), **kwargs)
                # close thread
                thread.close()
                lg.log('Aspera Transfer completed', level=Loglvl.INFO, type=Logtype.FILE )

            except OSError:
                return redirect('web.apps.web_copo.views.goto_error', request=HttpRequest(),
                                message='There appears to be an issue with EBI.')

        # setup paths for conversion directories
        conv_dir = os.path.join(self._dir, sub_id)
        if not os.path.exists(os.path.join(conv_dir, 'json')):
            os.makedirs(os.path.join(conv_dir, 'json'))
        json_file_path = os.path.join(conv_dir, 'json', 'isa_json.json')
        xml_dir = os.path.join(conv_dir, 'sra', sub_id)
        xml_path = os.path.join(xml_dir, 'run_set.xml')
        #  Convert COPO data to ISA_JSON

        lg.log('Obtaining ISA-JSON', level=Loglvl.INFO, type=Logtype.FILE )
        meta = cnv.Investigation(submission_token=sub_id).get_schema()
        json_file = open(json_file_path, '+w')
        # dump metadata to output file
        json_file.write(dumps(meta))
        json_file.close()

        # Validate ISA_JSON
        lg.log('Validating ISA-JSON', level=Loglvl.INFO, type=Logtype.FILE )
        with open(json_file_path) as json_file:
            v = isajson.validate(json_file)
            lg.log(v, level=Loglvl.INFO, type=Logtype.FILE )


        # create dummy files for ISA - the need for this will hopefully be removed in a future ISA release
        lg.log('Creating dummy files', level=Loglvl.INFO, type=Logtype.FILE )
        for f in self.d_files:
            x_split = f['file_location'].split('/')[-1]
            # f_name = x_split[len(x_split) - 1]
            loc = os.path.join(conv_dir, x_split)
            with open(loc, "w") as i:
                i.write("")


        # convert to SRA with isatools converter
        lg.log('Converting to SRA', level=Loglvl.INFO, type=Logtype.FILE )
        json2sra.convert(open(json_file_path), conv_dir, self._config_dir)

        lg.log('Adjusting SRA XMLS', level=Loglvl.INFO, type=Logtype.FILE )
        # adjust hashes in SRA XML
        xml = ET.parse(xml_path)
        for child in xml.findall("RUN/DATA_BLOCK/FILES/FILE"):
            file_name = child.attrib['filename']
            for df in self.d_files:
                if file_name == df['file_location'].split('/')[-1]:
                    # change the hash
                    child.set('checksum', df['file_hash'])
                    filename = os.path.basename(file_name)
                    child.set('filename', os.path.join(remote_path, filename))
        xml.write(xml_path)

        # make sure there is a study abstract supplied
        xml_path = os.path.join(xml_dir, 'study.xml')
        xml = ET.parse(xml_path)
        desc = xml.find('DESCRIPTOR')
        abstract_found = False
        for x in desc.iter():
            if x.tag == 'STUDY_ABSTRACT':
                abstract_found = True
        if abstract_found == False:
            child = Element('STUDY_ABSTRACT')
            child.text = "HERE IS SOME TEXT FOR THE ABSTRACT"
            desc.append(child)
        xml.write(xml_path)


        # finally submit to SRA
        lg.log('Submitting XMLS to ENA via CURL', level=Loglvl.INFO, type=Logtype.FILE )
        submission_file = os.path.join(xml_dir, 'submission.xml')
        study_file = os.path.join(xml_dir, 'study.xml')
        sample_file = os.path.join(xml_dir, 'sample_set.xml')
        experiment_file = os.path.join(xml_dir, 'experiment_set.xml')
        run_file = os.path.join(xml_dir, 'run_set.xml')




        curl_cmd = 'curl -k -F "SUBMISSION=@' + submission_file + '" \
         -F "STUDY=@' + os.path.join(remote_path, study_file) + '" \
         -F "SAMPLE=@' + os.path.join(remote_path, sample_file) + '" \
         -F "EXPERIMENT=@' + os.path.join(remote_path, experiment_file) + '" \
         -F "RUN=@' + os.path.join(remote_path, run_file) + '" \
         "https://www.ebi.ac.uk/ena/submit/drop-box/submit/?auth=ENA%20Webin-39233%20Apple123"'

        output = subprocess.check_output(curl_cmd, shell=True)

        lg.log( output, level=Loglvl.INFO, type=Logtype.FILE )



        #output = b'<RECEIPT receiptDate="2016-08-12T15:16:25.796+01:00" submissionFile="submission.xml" success="true"><EXPERIMENT accession="ERX1649918" alias="0000000000000:generic_assay:a_57a1d46168236ba7ef4741cc.EXP1" status="PRIVATE"/><RUN accession="ERR1579162" alias="0000000000000:assay:EXP1.1" status="PRIVATE"/><SAMPLE accession="ERS1290270" alias="0000000000000:source:dog1" status="PRIVATE"><EXT_ID accession="SAMEA4378821" type="biosample"/></SAMPLE><SAMPLE accession="ERS1290271" alias="0000000000000:source:dog2" status="PRIVATE"><EXT_ID accession="SAMEA4378822" type="biosample"/></SAMPLE><SAMPLE accession="ERS1290272" alias="0000000000000:source:dog3" status="PRIVATE"><EXT_ID accession="SAMEA4378824" type="biosample"/></SAMPLE><STUDY accession="ERP016832" alias="0000000000000" status="PUBLIC"/><SUBMISSION accession="ERA688261" alias="0000000000000"/><MESSAGES><INFO> ADD action for the following XML: study.xml sample_set.xml experiment_set.xml run_set.xml</INFO><INFO>Found other as the existing study type, please provide a new study type in the Study (0000000000000)</INFO><INFO>Deprecated element ignored: CENTER_NAME</INFO><INFO> Please provide the new study type for your study(null) as you provided \'OTHER\' for the exisiting type is null</INFO></MESSAGES><ACTIONS>ADD</ACTIONS><ACTIONS>ADD</ACTIONS><ACTIONS>ADD</ACTIONS><ACTIONS>ADD</ACTIONS></RECEIPT>'
        lg.log( "Extracting fields from receipt", level=Loglvl.INFO, type=Logtype.FILE )


        xml = ET.fromstring(output)

        accessions = dict()

        # get study accessions
        study = xml.find('./STUDY')
        study_accession = study.get('accession', default='undefined')
        study_alias = study.get('alias', default='undefined')
        accessions['study'] = {'accession': study_accession, 'alias': study_alias}

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