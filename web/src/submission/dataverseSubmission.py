__author__ = 'felix.shaw@tgac.ac.uk - 19/04/2017'

from django.conf import settings
from dataverse import Connection, Dataverse, Dataset, DataverseFile
from dataverse.exceptions import ConnectionError
import uuid
import requests
import json
from dal.copo_da import Submission
from django_tools.middlewares.ThreadLocal import get_current_user, get_current_request
from dal.copo_da import Profile
import datetime


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
        dataset = self._get_dataset(profile_id, dataverse, connection)
        meta = dict()

        m = dataset.get_metadata()

        meta["title"] = "TITLE123"
        meta["authorName"] = "AUTHOR123"
        meta["subject"] = "SUBJECT123"
        meta["dsDescriptionValue"] = "DESCRIPTION123"
        meta["datasetContactEmail"] = "ABC@GMAIL.COM"

        d = dataset.update_metadata(meta)

        #  get details of files

        file = self._upload_files(dataset)

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

    def _get_dataset(self, profile_id, dataverse, connection):
        # create new dataset if none exists already
        ds_details = Profile().check_for_dataset_details(profile_id)
        if not ds_details:
            suffix = str(uuid.uuid1()).split('-')[0]
            dataset = dataverse.create_dataset('test', 'test_description', 'f.shaw@tgac.ac.uk')
            Profile().add_dataverse_dataset_details(profile_id, dataset)
        else:
            dataset = dataverse.get_dataset_by_doi(ds_details['doi'])
        return dataset

    def _upload_files(self, dataset):
        url_dataset_id = 'https://%s/api/datasets/:persistentId/add?persistentId=%s&key=%s' % (self.host,
                                                                                               dataset.doi,
                                                                                               self.token)
        file_content = 'content: %s' % datetime.datetime.now()
        files = {'file': ('sample_file.txt', file_content)}

        params = dict(description='Blue skies!',
                      categories=['Lily', 'Rosemary', 'Jack of Hearts'])
        params_as_json_string = json.dumps(params)
        payload = dict(jsonData=params_as_json_string)
        r = requests.post(url_dataset_id, data=payload, files=files)

    def _connect(self, host, token):
        try:
            c = Connection(host, token)
            return c
        except ConnectionError:
            return None
