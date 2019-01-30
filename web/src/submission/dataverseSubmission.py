__author__ = 'felix.shaw@tgac.ac.uk - 19/04/2017'
import os, uuid, requests, json, datetime, sys
from datetime import datetime as dt
from django_tools.middlewares import ThreadLocal
from django.conf import settings
from dataverse import Connection, Dataverse, Dataset, DataverseFile
from dataverse.exceptions import ConnectionError
from dal.copo_da import Submission, DataFile
from web.apps.web_copo.schemas.utils import data_utils
from dal.copo_da import Profile
from bson import ObjectId, json_util
import xml.etree.ElementTree as et
from dataverse.exceptions import OperationFailedError
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ElementTree, Element, SubElement, Comment, tostring
from xml.dom import minidom


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
        # this flag tells us if we are dealing with a cg submission
        isCg = s["is_cg"]
        # get url for dataverse
        self.host = Submission().get_dataverse_details(sub_id)
        self.headers = {'X-Dataverse-key': self.host['apikey']}

        # if dataset id in submission meta, we are adding to existing dataset, otherwise
        #  we are creating a new dataset
        if "fields" in s["meta"]:
            # create new
            return self._create_and_add_to_dataverse(s)
        elif 'entity_id' in s['meta'] and 'alias' in s['meta'] or 'dataverse_alias' in s['meta'] and 'doi' in s['meta']:
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
        # dv = self._create_dataverse(sub['meta'], connection)
        dv = connection.get_dataverse(sub["meta"]["alias"])
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
        # for e in sub["meta"]["fields"]:
        #    if type(e["vals"]) == type(list()):
        #        d[e["dvname"]] = e["vals"][0]
        #    else:
        #        d[e["dvname"]] = e["vals"]
        # get datafile for some dataverse specific metadata
        datafile = DataFile().get_record(ObjectId(sub['bundle'][0]))
        df = datafile['description']['attributes']
        # pth = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'blanks', 'dataset_xml.xml')
        # tree = et.parse(pth)
        # root = tree.getroot()
        root = ET.Element("entry")
        root.set("xmlns", "http://www.w3.org/2005/Atom")
        root.set("xmlns:dcterms", "http://purl.org/dc/terms/")
        # tree = ElementTree(root)
        for item in meta["fields"]:
            if type(item["vals"]) == type(""):
                tail = item["dc"].split(".")[1]
                term = "dcterms:" + tail
                child = ET.SubElement(root, term)
                child.text = item["vals"]
                root.append(child)
            elif type(item["vals"] == type(list())):
                for val in item["vals"]:
                    tail = item["dc"].split(".")[1]
                    term = "dcterms:" + tail
                    child = ET.SubElement(root, term)
                    child.text = val
                    root.append(child)

        x = prettify(root)
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
