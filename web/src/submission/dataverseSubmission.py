__author__ = 'felix.shaw@tgac.ac.uk - 19/04/2017'
import os
from django.conf import settings
from dataverse import Connection, Dataverse, Dataset, DataverseFile
from dataverse.exceptions import ConnectionError
import uuid
import requests
from requests.compat import urlencode, urljoin
import json
from dal.copo_da import Submission, DataFile
from web.apps.web_copo.schemas.utils import data_utils
from dal.copo_da import Profile
import datetime
from bson import ObjectId
from pprint import pprint
import copy


class DataverseSubmit(object):
    def __init__(self):
        self.host = settings.DATAVERSE["HARVARD_TEST_API"]
        self.token = settings.DATAVERSE["HARVARD_TEST_TOKEN"]
        # self.API_URL = settings.TEST_DATAVERSE_API_URL
        self.headers = {'X-Dataverse-key': self.token}

    def submit(self, sub_id, dataFile_ids):

        profile_id = data_utils.get_current_request().session.get('profile_id')
        dataverse = self._get_dataverse(profile_id=profile_id)
        dataset = self._get_dataset(profile_id=profile_id, dataFile_ids=dataFile_ids, dataverse=dataverse)

        #  get details of files

        file = self._upload_files(dataverse, dataset, dataFile_ids, sub_id)
        if not file:
            return 'File already present'
        return True

    def _get_dataverse(self, profile_id):

        # create new dataverse if none already exists

        u = data_utils.get_current_user()
        # create new dataverse if none exists already
        dv_details = Profile().check_for_dataverse_details(profile_id)

        if not dv_details:
            # dataverse = connection.create_dataverse(dv_alias, '{0} {1}'.format(u.first_name, u.last_name), u.email)
            dv_details = self._create_dataverse(profile_id)
            Profile().add_dataverse_details(profile_id, dv_details)

        return dv_details

    def _create_dataverse(self, profile_id):
        profile = Profile().get_record(profile_id)
        dv_alias = str(uuid.uuid1())
        dv_scaf = dict()
        # load dataverse scaffold
        pth = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'blanks', 'dataverse_scaffold.json')
        with open(pth, 'r') as f:
            user = data_utils.get_current_user()
            email = user.email
            dv_scaf = json.loads(f.read())
            dv_scaf['name'] = profile['title']
            dv_scaf['description'] = profile['description']
            dv_scaf['dataverseContacts'][0]['contactEmail'] = email
            dv_scaf['alias'] = dv_alias
        make_dataverse_url = self.host + '{0}/{1}/?key={2}'.format('dataverses', ':root', self.token)
        resp = requests.post(make_dataverse_url, data=json.dumps(dv_scaf))
        return json.loads(resp.content.decode('utf-8'))

    def _get_dataset(self, profile_id, dataFile_ids, dataverse):
        # create new dataset if none exists already
        ds_details = Profile().check_for_dataset_details(profile_id)
        if not ds_details:
            ds_details = self._create_dataset(dataFile_ids=dataFile_ids, dataverse=dataverse)
            Profile().add_dataverse_dataset_details(profile_id, ds_details)
        return ds_details

    def _create_dataset(self, dataFile_ids, dataverse):
        # get datafile mongo object to extract dataset metadata
        # all files submitted in this call will have the same dataverse dc:metadata
        id = dataFile_ids[0]
        df = DataFile().get_record(ObjectId(id))

        # load metadata skeleton
        ds_scaf = dict()
        pth = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'blanks', 'dataset_scaffold.json')
        with open(pth, 'r') as f:
            ds_scaf = json.loads(f.read())
            user = data_utils.get_current_user()
            email = user.email

            for n_dict in ds_scaf["datasetVersion"]["metadataBlocks"]["citation"]["fields"]:
                # parse skeleton dictionary checking for tag names, and inserting metadata where relevant
                if n_dict['typeName'] == 'title':
                    # export title
                    n_dict['value'] = df.get('description').get('attributes').get('title_author_contributor').get(
                        'dcterms:title')
                elif n_dict['typeName'] == 'author':
                    # get authors from mongo
                    authors = listize(
                        df.get('description').get('attributes').get('title_author_contributor').get('dcterms:creator'))
                    author_obj = n_dict['value']
                    authors_list = list()
                    for m in authors:
                        temp = copy.deepcopy(author_obj[0])
                        # reverse names
                        names = m.strip().split(' ')
                        temp['authorName']['value'] = names[1] + ' ' + names[0]
                        temp['authorAffiliation']['value'] = email.rsplit('@')[1]
                        authors_list.append(temp)
                    n_dict['value'] = authors_list
                elif n_dict['typeName'] == 'datasetContact':
                    for contacts in n_dict['value']:
                        for contact_key in contacts.keys():
                            if contact_key == 'datasetContactName':
                                contacts[contact_key]['value'] = df.get('description').get('attributes').get(
                                    'title_author_contributor').get(
                                    'dcterms:creator')
                            elif contact_key == 'datasetContactAffiliation':
                                tmp_email = df.get('description').get('attributes').get(
                                    'title_author_contributor').get(
                                    'dcterms:contributor')
                                affiliation = tmp_email.rsplit('@')[1]
                                contacts[contact_key]['value'] = affiliation
                            elif contact_key == 'datasetContactEmail':
                                contacts[contact_key]['value'] = email
                elif n_dict['typeName'] == 'dsDescription':
                    for descriptions in n_dict['value']:
                        for ds_key in descriptions.keys():
                            if ds_key == 'dsDescriptionValue':
                                descriptions[ds_key]['value'] = df.get('description').get('attributes').get(
                                    'subject_description').get(
                                    'dcterms:description')
                            elif ds_key == 'dsDescriptionDate':
                                d = df.get('description').get('attributes').get('optional_fields').get('dcterms:date')
                                descriptions[ds_key]['value'] = datetime.datetime.strptime(d, '%d/%m/%Y').strftime(
                                    '%Y-%m-%d')
                elif n_dict['typeName'] == 'subject':
                    n_dict['value'].append(
                        df.get('description').get('attributes').get('subject_description').get(
                            'dcterms:subject')
                    )
                elif n_dict['typeName'] == 'dateOfDeposit':
                    d = df.get('description').get('attributes').get('optional_fields').get(
                        'dcterms:date')
                    n_dict['value'] = datetime.datetime.strptime(d, '%d/%m/%Y').strftime('%Y-%m-%d')
                elif n_dict['typeName'] == 'depositor':
                    n_dict['value'] = settings.COPO_URL
                elif n_dict['typeName'] == 'dataSources':
                    n_dict['value'] = df.get('description').get('attributes').get('optional_fields').get(
                        'dcterms:source')
                    n_dict['value'] = listize(n_dict['value'])
                    if not n_dict['value']:
                        n_dict['value'] = []
                elif n_dict['typeName'] == 'relatedMaterial':
                    n_dict['value'] = df.get('description').get('attributes').get('optional_fields').get(
                        'dcterms:relation')
                    n_dict['value'] = listize(n_dict['value'])
                    if not n_dict['value']:
                        n_dict['value'] = []
                        # TODO - if other fields are required, add them into the dataset_scaffold template, and extract them from the datafile object
            new_dataset_url = self.host + '{0}/{1}/{2}/?key={3}'.format('dataverses', dataverse['data']['alias'],
                                                                        'datasets',
                                                                        self.token)
            resp = requests.post(new_dataset_url,
                                 data=json.dumps(ds_scaf)
                                 )

            out = json.loads(resp.content.decode('utf-8'))
            if out['status'] == "OK":
                # now we get dataset details
                dataset_id = out["data"]["id"]
                url = urljoin(self.host, 'datasets/' + str(dataset_id) + '/?key=' + self.token)
                d = requests.get(url)
                out = json.loads(d.content.decode('utf-8'))
                out['doi'] = out['data']['protocol'] + ':' + out['data']['authority'] + '/' + out['data']['identifier']

        return out

    def _upload_files(self, dataverse, dataset, dataFile_ids, sub_id):

        # TODO - get first dataset in dataverse...this should change in a future release
        if isinstance(dataset, list):
            dataset = dataset[0]

        url_dataset_id = '{0}datasets/:persistentId/add?persistentId={1}&key={2}'.format(self.host,
                                                                                         dataset['doi'],
                                                                                         self.token)
        accessions = list()
        for id in dataFile_ids:
            file = DataFile().get_record(ObjectId(id))
            file_location = file['file_location']

            with open(file_location, "rb") as f:
                file_content = f.read()
                # file_content = file_content + str(uuid.uuid1()).encode('utf-8')

            name = file['name']
            files = {'file': (name, file_content)}

            payload = dict()
            params = dict(description='Blue skies!',
                          categories=['Lily', 'Rosemary', 'Jack of Hearts'])
            params_as_json_string = json.dumps(params)
            payload = dict(jsonData=params_as_json_string)
            r = requests.post(url_dataset_id, data=payload, files=files)
            if r.status_code == 400:
                resp = json.loads(r.content.decode('utf-8'))
                if resp['status'] == 'ERROR':
                    return False

            # add mongo_file id
            acc = json.loads(r.content.decode('utf-8'))['data']['files'][0]['dataFile']
            acc['mongo_file_id'] = id
            acc['dataset_doi'] = dataset['doi']
            acc['dataverse_title'] = dataverse['data']['name']
            acc['dataverse_alias'] = dataverse['data']['alias']
            accessions.append(acc)

        # save accessions to mongo profile record
        s = Submission().get_record(sub_id)
        s['accessions'] = accessions
        s['complete'] = True
        s['target_id'] = str(s.pop('_id'))
        Submission().save_record(dict(), **s)
        Submission().mark_submission_complete(sub_id)
        return True


def listize(list):
    # split list by comma
    if list == '':
        return None
    else:
        return list.split(',')
