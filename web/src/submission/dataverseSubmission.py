__author__ = 'felix.shaw@tgac.ac.uk - 19/04/2017'

import os, uuid, requests, json
from django_tools.middlewares import ThreadLocal
from dataverse import Connection, Dataset
from dal.copo_da import Submission, DataFile
from web.apps.web_copo.schemas.utils import data_utils
from dal.copo_da import Profile
from bson import ObjectId
from dataverse.exceptions import OperationFailedError
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas
from xml.etree.ElementTree import tostring
from xml.dom import minidom
import subprocess


class DataverseSubmit(object):
    host = None
    headers = None

    def __init__(self, sub_id=None):
        if sub_id:
            self.host = Submission().get_dataverse_details(sub_id)
            self.headers = {'X-Dataverse-key': self.host['apikey']}

    def test_data(self):
        """
        using for quick test, should be deleted afterwards
        :return:
        """

        test_data = dict()
        test_data['sub_id'] = '5c5b0ab468236b4071ea488e'
        test_data['sub_record'] = {
            "_id": "5c5b0ab468236b4071ea488e",
            "message": "",
            "destination_repo": {
                "name": "Test Dataverse Repo",
                "isCG": True,
                "password": "",
                "url": "https://demo.dataverse.org",
                "username": "",
                "type": "dataverse",
                "apikey": "fe6998df-c2a4-4103-9bf8-95200953fe0c",
                "repo_id": "5b90027d453d9a9f1c5aa456"
            },
            "bundle_meta": [
                {
                    "file_path": "/Users/fshaw/Dropbox/dev/COPO/web/src/media/chunked_uploads/35/10_05_58_023798/Sad-Fish-300x243.png",
                    "upload_status": False,
                    "file_id": "5bffba0668236b4a939fde3f"
                }
            ],
            "deleted": "0",
            "user_id": 35,
            "complete": "false",
            "token_obtained": False,
            "bundle": [
                "5bffba0668236b4a939fde3f"
            ],
            "profile_id": "5beae06668236b1a8e2ede97",
            "status": False,
            "repository": "dataverse",
            "transcript": {},
            "date_modified": "2019-02-06T16:26:28.056Z",
            "description_token": "5c5b0a0e68236b4071ea488d",
            "article_id": "",
            "is_cg": "True",
            "completed_on": "2019-02-11T10:38:21.853Z",
            "date_created": "2019-02-06T16:26:28.056Z",
            "meta": {
                "new_or_existing": "new",
                "alias": "f94a8793-1bf2-4c16-8815-37328062a206",
                "entity_id": 190041,
                "fields": [
                    {
                        "dc": "dc.type",
                        "vals": "Database",
                        "copo_id": "type"
                    },
                    {
                        "dc": "dc.title",
                        "vals": [
                            "Yon Posters"
                        ],
                        "copo_id": "title"
                    },
                    {
                        "dc": "dc.description",
                        "vals": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                        "copo_id": "description"
                    },
                    {
                        "dc": "dc.subject",
                        "vals": [
                            "Publication",
                            "Dark"
                        ],
                        "copo_id": "subject"
                    },
                    {
                        "dc": "dc.creator",
                        "vals": [
                            "Felix Shaw"
                        ],
                        "copo_id": "creator"
                    },
                    {
                        "dc": "dc.publisher",
                        "vals": [
                            "Hong Kong Ping Pong"
                        ],
                        "copo_id": "publisher"
                    },
                    {
                        "dc": "dc.format",
                        "vals": [
                            "image/png"
                        ],
                        "copo_id": "format"
                    },
                    {
                        "dc": "dc.language",
                        "vals": [
                            "eng",
                            "fra"
                        ],
                        "copo_id": "language"
                    },
                    {
                        "dc": "dc.relation",
                        "vals": "copo:5c5b0ab468236b4071ea488e",
                        "copo_id": "submission_id"
                    }
                ]
            },
            "published": "",
            "accessions": []
        }

        test_data['destination_repo'] = {
            "name": "Test Dataverse Repo",
            "isCG": True,
            "password": "",
            "url": "https://demo.dataverse.org",
            "username": "",
            "type": "dataverse",
            "apikey": "fe6998df-c2a4-4103-9bf8-95200953fe0c",
            "repo_id": "5b90027d453d9a9f1c5aa456"
        }

        return test_data

    def submit(self, sub_id, dataFile_ids):

        profile_id = data_utils.get_current_request().session.get('profile_id')
        s = Submission().get_record(ObjectId(sub_id))

        # test ####################
        sub_id = self.test_data()['sub_id']
        s = self.test_data()['sub_record']
        # test ends ################

        # this flag tells us if we are dealing with a cg submission
        isCg = s["is_cg"]
        # get url for dataverse
        # self.host = Submission().get_dataverse_details(sub_id)

        # test ####################
        self.host = self.test_data()['destination_repo']
        # test ends ################

        self.headers = {'X-Dataverse-key': self.host['apikey']}

        # if dataset id in submission meta, we are adding to existing dataset, otherwise
        #  we are creating a new dataset
        if "fields" in s["meta"]:  # toni's comment - any reason this doesn't simply check for 'alias' in meta?
            # create new
            return self._create_and_add_to_dataverse(submission_record=s)
        elif ('entity_id' in s['meta'] and 'alias' in s['meta']) or (
                'dataverse_alias' in s['meta'] and 'doi' in s['meta']):
            # submit to existing
            return self._add_to_dataverse(s)

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
        try:
            alias = sub['meta']['dataverse_alias']
        except KeyError:
            alias = sub['meta']['alias']
        dv = c.get_dataverse(alias)
        if dv == None:
            return {"status": 1, "message": "error getting dataverse"}
        doi = self.truncate_url(sub['meta']['doi'])
        ds = dv.get_dataset_by_doi(doi)
        if ds == None:
            ds = dv.get_dataset_by_string_in_entry(str.encode(sub['meta']['identifier']))
            if ds == None:
                ds = dv.get_dataset_by_string_in_entry(str(sub['meta']['doi']).encode())

        self.send_files(sub, ds)
        meta = ds._metadata
        dv_storageIdentifier = meta['latest']['storageIdentifier']
        return self._update_submission_record(sub, ds, dv, dv_storageIdentifier)

    def convert_dataset_metadata(self, metadata_fields=list()):
        """
        given metadata fields, function returns a Dataset-compliant schema
        :param metadata_fields:
        :return: converted metadata
        """

        converted_metadata = dict()
        return converted_metadata

    def _create_and_add_to_dataverse(self, submission_record=dict()):
        """
        creates a Dataset in a Dataverse
        :param submission_record:
        :return:
        """

        submission_meta = submission_record.get("meta", dict())

        # get dataverse alias
        dataverse_alias = submission_meta.get("alias", str())

        if not dataverse_alias:
            exception_message = 'Dataverse alias not found! '
            print(exception_message)
            raise OperationFailedError(exception_message)
            return False

        # convert dataset metadata
        converted_metadata = self.convert_dataset_metadata(metadata_fields=submission_meta.get("fields", list()))

        # make API call
        dataset_json = '/Users/etuka/Desktop/dataset-finch1.json'

        api_call = 'curl -H "X-Dataverse-key: {api_token}" -X POST ' \
                   '{server_url}/api/dataverses/{dv_alias}/datasets --upload-file {dataset_json}'

        api_call = api_call.format(api_token=self.host['apikey'],
                                   server_url=self.host['url'],
                                   dv_alias=dataverse_alias,
                                   dataset_json=dataset_json)

        # retrieve call result
        try:
            receipt = subprocess.check_output(api_call, shell=True)
        except Exception as e:
            print('API call error: ' + str(e))
            return False

        try:
            receipt = json.loads(receipt.decode('utf-8'))
        except Exception as e:
            exception_message = 'Could not retrieve API result. ' + str(receipt)
            print(exception_message)
            return False

        if receipt.get("status", str()).lower() in ("ok", "200"):
            dataset_id = receipt.get("data", dict())
        else:
            exception_message = 'The Dataset could not be created. ' + str(receipt)
            print(exception_message)
            raise OperationFailedError(exception_message)
            return False

        # publish dataset
        publish_status = self.publish_dataset(dataset_id.get('id', str()))

        # add file to dataset
        pass

        # save dataset info
        pass

        return False

        xml_path = self._make_dataset_xml(sub)
        ds = Dataset.from_xml_file(xml_path)
        dv._add_dataset(ds)
        # ds.publish()
        self.send_files(sub, ds)
        meta = ds._metadata
        dv_storageIdentifier = meta['latest']['storageIdentifier']
        return self._update_submission_record(sub, ds, dv, dv_storageIdentifier)

    def send_files(self, sub, ds):

        for id in sub['bundle']:
            file = DataFile().get_record(ObjectId(id))
            file_location = file['file_location']
            file_name = file['name']
            with open(file_location, 'rb') as f:
                contents = f.read()
                ds.upload_file(file_name, contents, zip_files=False)

    def send_files_curl(self, sub, persistent_id=str()):

        for id in sub['bundle']:
            file = DataFile().get_record(ObjectId(id))
            file_location = file['file_location']
            file_name = file['name']

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
        email = ""
        for f in meta["fields"]:
            if f["dc"] == "dc.title":
                name = f["vals"][0]
            if f["dc"] == "dc.email":
                email = f["vals"][0]
        if email == "":
            u = ThreadLocal.get_current_user()
            email = u.email
        dv = conn.create_dataverse(alias, name, email)
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

        # iterate through meta to get fields
        d = dict()
        datafile = DataFile().get_record(ObjectId(sub['bundle'][0]))
        df = datafile['description']['attributes']

        xml = '<?xml version="1.0"?>'
        xml = xml + '<entry xmlns="http://www.w3.org/2005/Atom" xmlns:dcterms="http://purl.org/dc/terms/">'
        xml = xml + '<dcterms:contributor>' + "felix.shaw@tgac.ac.uk" + '</dcterms:contributor>'

        for item in meta["fields"]:

            if type(item["vals"]) == type(""):
                tail = item["dc"].split(".")[1]
                xml = xml + "<dcterms:" + tail + '>' + item["vals"] + "</dcterms:" + tail + '>'

            elif type(item["vals"] == type(list())):
                for val in item["vals"]:
                    tail = item["dc"].split(".")[1]
                    xml = xml + '<dcterms:' + tail + '>' + val + '</dcterms:' + tail + '>'

        xml = xml + "</entry>"
        path = os.path.dirname(datafile['file_location'])
        xml_path = os.path.join(path, 'xml.xml')
        with open(xml_path, 'w+') as f:
            f.write(xml)
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

    def publish_dataset(self, dataset_id):
        url = self.host['url'] + '/api/datasets/' + str(dataset_id) + '/actions/:publish?type=major'

        resp = requests.post(
            url,
            data={'type': 'major', 'key': self.host['apikey']},
            headers=self.headers
        )

        if resp.status_code not in (200, 201):
            raise OperationFailedError('Dataset could not be published. ' + resp.content)
            return False

        return True

    def dc_dict_to_dc(self, sub_id):
        # get file metadata, call converter to strip out dc fields
        s = Submission().get_record(ObjectId(sub_id))
        f_id = s["bundle"][0]
        items = CgCoreSchemas().extract_repo_fields(str(f_id), "dataverse")
        temp_id = "copo:" + str(sub_id)
        # add the submission_id to the dataverse metadata to allow backwards treversal from dataverse
        items.append({"dc": "dc.relation", "copo_id": "submission_id", "vals": temp_id})
        Submission().update_meta(sub_id, json.dumps(items))


def prettify(elem):
    # Return a pretty-printed XML string for the Element.
    rough_string = tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")
