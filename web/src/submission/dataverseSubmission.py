__author__ = 'felix.shaw@tgac.ac.uk - 19/04/2017'
import os
from django.conf import settings
from dataverse import Connection, Dataverse, Dataset, DataverseFile
from dataverse.exceptions import ConnectionError
import uuid
import requests
from dal.copo_da import Submission, DataFile
from web.apps.web_copo.schemas.utils import data_utils
from dal.copo_da import Profile
import datetime
from bson import ObjectId, json_util
import xml.etree.ElementTree as et
from dataverse.exceptions import OperationFailedError


class DataverseSubmit(object):
    host = None
    headers = None

    def __init__(self, sub_id=None):
        if sub_id:
            self.host = Submission().get_dataverse_details(sub_id)
            self.headers = {'X-Dataverse-key': self.host['apikey']}

    def submit(self, sub_id, dataFile_ids):

        profile_id = data_utils.get_current_request().session.get('profile_id')
        s = Submission().get_record(ObjectId(sub_id))

        # get url for dataverse
        self.host = Submission().get_dataverse_details(sub_id)
        self.headers = {'X-Dataverse-key': self.host['apikey']}

        # if dataset id in submission meta, we are adding to existing dataset, otherwise
        #  we are creating a new dataset
        if 'dataverse_alias' in s['meta'] and 'doi' in s['meta']:
            # submit to existing
            return self._add_to_dataverse(s)
        else:
            # create new
            return self._create_and_add_to_dataverse(s)


    def truncate_url(self, url):
        if url.startswith('https://'):
            url = url[8:]
        elif url.startswith('http://'):
            url = url[7:]
        return url


    def clear_submission_metadata(self, sub_id):
        Submission().clear_submission_metadata(sub_id)

    def _add_to_dataverse(self, sub):
        c = self._get_connection()
        dv = c.get_dataverse(sub['meta']['dataverse_alias'])
        if dv == None:
            return {"status": 1, "message": "error getting dataverse"}
        doi = self.truncate_url(sub['meta']['doi'])
        ds = dv.get_dataset_by_doi(doi)
        if ds == None:
            ds = dv.get_dataset_by_string_in_entry(str.encode(sub['meta']['identifier']))
            if ds == None:
                ds = dv.get_dataset_by_string_in_entry(str(sub['meta']['doi']).encode())

        for id in sub['bundle']:
            file = DataFile().get_record(ObjectId(id))
            file_location = file['file_location']
            file_name = file['name']
            with open(file_location, 'rb') as f:
                contents = f.read()
                ds.upload_file(file_name, contents, zip_files=False)
        meta = ds._metadata
        dv_storageIdentifier = meta['latest']['storageIdentifier']
        return self._update_submission_record(sub, ds, dv, dv_storageIdentifier)

    def _create_and_add_to_dataverse(self, sub):
        connection = self._get_connection()
        dv = self._create_dataverse(sub['meta'], connection)
        xml_path = self._make_dataset_xml(sub)
        ds = Dataset.from_xml_file(xml_path)
        dv._add_dataset(ds)
        for id in sub['bundle']:
            file = DataFile().get_record(ObjectId(id))
            file_location = file['file_location']
            file_name = file['name']
            with open(file_location, 'rb') as f:
                contents = f.read()
                ds.upload_file(file_name, contents, zip_files=False)
        meta = ds._metadata
        dv_storageIdentifier = meta['latest']['storageIdentifier']
        return self._update_submission_record(sub, ds, dv, dv_storageIdentifier)

    def _get_connection(self):
        dvurl = self.host['url']
        apikey = self.host['apikey']
        dvurl = self.truncate_url(dvurl)
        c = Connection(dvurl, apikey)
        return c

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

    def _create_dataverse(self, meta, conn):
        alias = str(uuid.uuid4())
        dv = conn.create_dataverse(alias, meta['dvName'], meta['dsContactEmail'])
        return dv

    def _create_dataset(self, meta, dv, conn):
        dv.create_dataset()
        x = self._make_dataset_xml(meta)
        Dataset.from_xml_file()

    def _get_dataset(self, profile_id, dataFile_ids, dataverse):
        # create new dataset if none exists already
        ds_details = Profile().check_for_dataset_details(profile_id)
        if not ds_details:
            ds_details = self._create_dataset(dataFile_ids=dataFile_ids, dataverse=dataverse)
            Profile().add_dataverse_dataset_details(profile_id, ds_details)
        return ds_details

    def _make_dataset_xml(self, sub):
        meta = sub['meta']
        # get datafile for some dataverse specific metadata
        datafile = DataFile().get_record(ObjectId(sub['bundle'][0]))
        df = datafile['description']['attributes']
        pth = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'blanks', 'dataset_xml.xml')
        tree = et.parse(pth)
        root = tree.getroot()
        xmlns = "http://www.w3.org/2005/Atom"
        dcns = "http://purl.org/dc/terms/"
        x = "<?xml version='1.0'?>"
        x = x + '<entry xmlns="http://www.w3.org/2005/Atom" xmlns:dcterms="http://purl.org/dc/terms/">'
        x = x + '<title>' + meta['dsTitle'] + '</title>'
        x = x + '<id>' + str(uuid.uuid4()) + '</id>'
        x = x + '<updated>' + datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ') + '</updated>'
        x = x + '<author><name>' + meta['dsAuthorLastname'] + ', ' + meta['dsAuthorFirstname'] + '</name></author>'
        x = x + '<summary type="text"></summary>'
        x = x + '<dcterms:title>' + meta['dsTitle'] + '</dcterms:title>'
        x = x + '<dcterms:creator>' + meta['dsAuthorLastname'] + ', ' + meta['dsAuthorFirstname'] + '</dcterms:creator>'
        if settings.UNIT_TESTING:
            x = x + '<dcterms:date>' + sub['date_modified'] + '</dcterms:date>'
        else:
            x = x + '<dcterms:date>' + sub['date_modified'].strftime('%Y-%m-%d') + '</dcterms:date>'
        x = x + '<dcterms:rights>' + df['optional_fields']['license'] + '</dcterms:rights>'
        # this should be an array
        x = x + '<dcterms:bibliographicCitation>' + df['optional_fields']['source'] + '</dcterms:bibliographicCitation>'
        x = x + '<dcterms:description>' + df['subject_description']['description'] + '</dcterms:description>'
        x = x + '<dcterms:identifier>' + '' + '</dcterms:identifier>'
        x = x + '<dcterms:subject>' + df['subject_description']['subject'] + '</dcterms:subject>'
        x = x + '</entry>'
        path = os.path.dirname(datafile['file_location'])
        xml_path = os.path.join(path, 'xml.xml')
        with open(xml_path, 'w+') as f:
            f.write(x)
        return xml_path

    def _update_submission_record(self, sub, dataset, dataverse, dv_storageIdentifier=None):
        # add mongo_file id
        acc = dict()
        acc['storageIdentifier'] = dv_storageIdentifier
        acc['mongo_file_id'] = dataset.id
        acc['dataset_doi'] = dataset.doi
        acc['dataset_edit_media_uri'] = dataset.edit_media_uri
        acc['dataset_edit_uri'] = dataset.edit_uri
        acc['dataset_is_deleted'] = dataset.is_deleted
        acc['dataset_title'] = dataset.title
        acc['dataverse_title'] = dataset.dataverse.title
        acc['dataverse_alias'] = dataset.dataverse.alias
        acc['dataset_id'] = dataset._id
        # save accessions to mongo profile record
        sub['accessions'] = acc
        sub['complete'] = True
        sub['target_id'] = str(sub.pop('_id'))
        Submission().save_record(dict(), **sub)
        Submission().mark_submission_complete(sub['target_id'])
        return True

    def _listize(list):
        # split list by comma
        if list == '':
            return None
        else:
            return list.split(',')

    def publish_dataverse(self, sub_id):
        # get url for dataverse
        self.host = Submission().get_dataverse_details(sub_id)
        self.headers = {'X-Dataverse-key': self.host['apikey']}
        submission = Submission().get_record(sub_id)
        dvAlias = submission['accessions']['dataverse_alias']
        dsId = submission['accessions']['dataset_id']
        conn = self._get_connection()
        dv = conn.get_dataverse(dvAlias)
        # ds = dv.get_dataset_by_doi(dsDoi)
        if not dv.is_published:
            dv.publish()
        # POST http://$SERVER/api/datasets/$id/actions/:publish?type=$type&key=$apiKey
        url = submission['destination_repo']['url']
        url = url + '/api/datasets/' + str(dsId) + '/actions/:publish?type=major'
        print(url)
        resp = requests.post(
            url,
            data={'type': 'major', 'key': self.host['apikey']},
            headers=self.headers
        )
        if resp.status_code != 200 or resp.status_code != 201:
            raise OperationFailedError('The Dataset could not be published. ' + resp.content)

        doc = Submission().mark_as_published(sub_id)

        return doc

    def cg_to_dc(self, sub_id):
        pass
