__author__ = 'felix.shaw@tgac.ac.uk - 19/04/2017'

from django.conf import settings
from dataverse import Connection, Dataverse, Dataset, DataverseFile
from dataverse.exceptions import ConnectionError
import uuid
import requests
import json
from dal.copo_da import Submission, DataFile
from django_tools.middlewares.ThreadLocal import get_current_user, get_current_request
from dal.copo_da import Profile
import datetime
from bson import ObjectId


class DataverseSubmit(object):
    def __init__(self):
        self.host = settings.DATAVERSE["HARVARD_TEST_API"]
        self.token = settings.DATAVERSE["HARVARD_TEST_TOKEN"]
        # self.API_URL = settings.TEST_DATAVERSE_API_URL
        self.headers = {'X-Dataverse-key': self.token}

    def submit(self, sub_id, dataFile_ids):

        profile_id = get_current_request().session.get('profile_id')
        connection = self._connect(self.host, self.token)
        dataverse = self._get_dataverse(profile_id, connection)

        # get datafile mongo object to extract dataset metadata
        # all files submitted in this call will have the same dataverse dc:metadata
        id = dataFile_ids[0]
        df = DataFile().get_record(ObjectId(id))
        meta = dict()
        meta["title"] = df['description']['attributes']['title_author_contributor']['dcterms:title']
        meta["authorName"] = df['description']['attributes']['title_author_contributor']['dcterms:author']
        meta["datasetContactEmail"] = df['description']['attributes']['title_author_contributor']['dcterms:contributor']
        meta["subject"] = df['description']['attributes']['subject_description']['dcterms:subject']
        meta["dsDescriptionValue"] = df['description']['attributes']['subject_description']['dcterms:description']

        dataset = self._get_dataset(profile_id=profile_id, dataverse=dataverse, meta=meta)

        #  get details of files

        file = self._upload_files(dataverse, dataset, dataFile_ids, sub_id)
        if not file:
            return 'File already present'
        else:
            return True

    def _get_dataverse(self, profile_id, connection):

        # create new dataverse if none already exists
        dv_alias = str(uuid.uuid1())
        u = get_current_user()
        # create new dataverse if none exists already
        dv_details = Profile().check_for_dataverse_details(profile_id)
        if not dv_details:
            dataverse = connection.create_dataverse(dv_alias, '{0} {1}'.format(u.first_name, u.last_name), u.email)
            Profile().add_dataverse_details(profile_id, dataverse)
        else:
            dataverse = connection.get_dataverse(dv_details['alias'])
        return dataverse

    def _get_dataset(self, profile_id, dataverse, meta):
        # create new dataset if none exists already
        ds_details = Profile().check_for_dataset_details(profile_id)
        if not ds_details:
            suffix = str(uuid.uuid1()).split('-')[0]
            dataset = dataverse.create_dataset(meta.pop('title'), meta.pop('subject'), meta.pop('authorName'), **meta)
            Profile().add_dataverse_dataset_details(profile_id, dataset)
        else:
            dataset = dataverse.get_dataset_by_doi(ds_details['doi'])
        return dataset

    def _upload_files(self, dataverse, dataset, dataFile_ids, sub_id):
        url_dataset_id = 'https://%s/api/datasets/:persistentId/add?persistentId=%s&key=%s' % (self.host,
                                                                                               dataset.doi,
                                                                                               self.token)
        accessions = list()
        for id in dataFile_ids:
            file = DataFile().get_record(ObjectId(id))
            file_location = file['file_location']

            with open(file_location, "rb") as f:
                file_content = f.read()
                #file_content = file_content + str(uuid.uuid1()).encode('utf-8')

            name = file['name']
            files = {'file': (name, file_content)}

            payload = dict()
            #params = dict(description='Blue skies!',
            #              categories=['Lily', 'Rosemary', 'Jack of Hearts'])
            #params_as_json_string = json.dumps(params)
            #payload = dict(jsonData=params_as_json_string)
            r = requests.post(url_dataset_id, data=payload, files=files)
            if r.status_code == 400:
                resp = json.loads(r.content.decode('utf-8'))
                if resp['status'] == 'ERROR':
                    return False

            # add mongo_file id
            acc = json.loads(r.content.decode('utf-8'))['data']['files'][0]['dataFile']
            acc['mongo_file_id'] = id
            acc['dataset_doi'] = dataset.doi
            acc['dataverse_title'] = dataverse.title
            acc['dataverse_alias'] = dataverse.alias
            accessions.append(acc)

        # save accessions to mongo profile record
        s = Submission().get_record(sub_id)
        s['accessions'] = accessions
        s['complete'] = True
        s['target_id'] = str(s.pop('_id'))
        Submission().save_record(dict(), **s)
        Submission().mark_submission_complete(sub_id)
        return True

    def _connect(self, host, token):
        try:
            c = Connection(host, token)
            return c
        except ConnectionError:
            return None
