__author__ = 'felix.shaw@tgac.ac.uk - 19/04/2017'

from datetime import datetime
import os, uuid, requests, json
from django_tools.middlewares import ThreadLocal
from dataverse import Connection, Dataset
from dal.copo_da import Submission, DataFile, DAComponent
from web.apps.web_copo.schemas.utils import data_utils
from dal.copo_da import Profile
from bson import ObjectId
from dataverse.exceptions import OperationFailedError
from xml.etree.ElementTree import tostring
from xml.dom import minidom
import subprocess
import pandas as pd
from django.conf import settings
from collections import namedtuple
from web.apps.web_copo.lookup.resolver import RESOLVER
from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas

lg = settings.LOGGER


class DataverseSubmit(object):
    def __init__(self, submission_id=str()):
        self.submission_id = submission_id

        self.submission_record = dict()
        self.file_path = str()
        self.host = str()
        self.api_token = str()
        self.headers = dict()

        if self.submission_id:
            # get submission record
            self.submission_record = Submission().get_record(self.submission_id)

            # set up submission parameters...

            # submission path
            dir = os.path.join(os.path.dirname(__file__), "data")
            self.file_path = os.path.join(os.path.join(dir, self.submission_id), 'dataverse')

            # dataverse host
            self.host = self.submission_record.get("destination_repo", dict()).get("url", str())

            # api_token
            self.api_token = self.submission_record.get("destination_repo", dict()).get("apikey", str())

            # headers
            self.headers = {'X-Dataverse-key': self.api_token}

    def submit(self):
        """
        function controls the submission of objects to a Dataverse
        :return:
        """

        sub_meta = self.submission_record.get("meta", dict())

        # if dataset id in submission meta, we are adding to existing dataset, otherwise
        #  we are creating a new dataset
        if "fields" in sub_meta:
            return self._create_and_add_to_dataverse()
        elif ('entity_id' in sub_meta and 'alias' in sub_meta) or ('dataverse_alias' in sub_meta and 'doi' in sub_meta):
            return self._add_to_dataverse()

    def truncate_url(self, url):
        if url.startswith('https://'):
            url = url[8:]
        elif url.startswith('http://'):
            url = url[7:]
        return url

    def clear_submission_metadata(self):
        Submission().clear_submission_metadata(self.submission_id)

    def _add_to_dataverse(self):
        sub = self.submission_record
        c = self._get_connection()
        try:
            alias = sub['meta']['dataverse_alias']
        except KeyError:
            alias = sub['meta']['alias']
        dv = c.get_dataverse(alias)
        if dv == None:
            return {"status": 404, "message": "error getting dataverse"}
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

    def _create_and_add_to_dataverse(self):
        """
        creates a Dataset in a Dataverse
        :param submission_record:
        :return:
        """

        # proceed with the creation of a dataset iff no accessions are recorded
        dataset_persistent_id = self.submission_record.get("accessions", dict()).get("dataset_doi", str())

        # there's existing submission associated with this submission
        if dataset_persistent_id:
            return self.post_dataset_creation(persistent_id=dataset_persistent_id)


        # get dataverse alias
        dataverse_alias = self.submission_record.get("meta", dict()).get("alias", str())

        if not dataverse_alias:
            exception_message = 'Dataverse alias not found! '
            self.report_error(exception_message)
            return exception_message
            # raise OperationFailedError(exception_message)

        # convert to Dataset metadata
        metadata_file_path = self.do_conversion()

        # make API call
        api_call = 'curl -H "X-Dataverse-key: {api_token}" -X POST ' \
                   '{server_url}/api/dataverses/{dv_alias}/datasets --upload-file {dataset_json}'

        api_call = api_call.format(api_token=self.api_token,
                                   server_url=self.host,
                                   dv_alias=dataverse_alias,
                                   dataset_json=metadata_file_path)

        # retrieve call result
        try:
            receipt = subprocess.check_output(api_call, shell=True)
        except Exception as e:
            exception_message = 'API call error: ' + str(e)
            self.report_error(exception_message)
            return exception_message
            # raise OperationFailedError(exception_message)

        try:
            receipt = json.loads(receipt.decode('utf-8'))
        except Exception as e:
            exception_message = 'Could not retrieve API result. ' + str(receipt)
            return exception_message
            # raise OperationFailedError(exception_message)

        if receipt.get("status", str()).lower() in ("ok", "200"):
            receipt = receipt.get("data", dict())
        else:
            exception_message = 'The Dataset could not be created. ' + str(receipt)
            self.report_error(exception_message)
            return exception_message
            # raise OperationFailedError(exception_message)

        dataset_persistent_id = receipt.get("persistentId", str())
        dataset_id = receipt.get("id", str())

        # retrieve and store accessions to db
        sub = self.submission_record
        acc = dict()
        acc['dataset_id'] = dataset_id
        acc['dataset_doi'] = dataset_persistent_id
        acc['dataverse_alias'] = dataverse_alias
        acc['dataverse_title'] = str()
        acc['dataset_title'] = str()

        # retrieve dataverse details given its alias
        response = requests.get(self.host + "/api/dataverses/" + dataverse_alias)
        if str(response.status_code).lower() in ("ok", "200"):
            response_data = response.json().get("data", dict())
            acc['dataverse_title'] = response_data.get("name", str())

        # retrieve dataset details given its doi
        headers = {'X-Dataverse-key': self.api_token}

        params = (
            ('persistentId', dataset_persistent_id),
        )

        response = requests.get(self.host + "/api/datasets/:persistentId/", headers=headers, params=params)
        if str(response.status_code).lower() in ("ok", "200"):
            response_data = response.json().get("data", dict())
            dataset_title = [x["value"] for x in
                             response_data.get("latestVersion", dict()).get("metadataBlocks", dict()).get("citation",
                                                                                                          dict()).get(
                                 "fields", dict()) if x.get("typeName", str()) == "title"]
            acc['dataset_title'] = dataset_title[0] if dataset_title else ''

        sub['accessions'] = acc

        sub['target_id'] = sub.pop('_id', self.submission_id)
        Submission().save_record(dict(), **sub)

        # do post creation tasks
        return self.post_dataset_creation(persistent_id=dataset_persistent_id)

    def post_dataset_creation(self, persistent_id=str()):
        """
        upon completion of dataset creation, perform this task(s)
        :param persistent_id:
        :return:
        """
        # add file to dataset
        result = self.send_files_curl(persistent_id=persistent_id)

        if result:
            self.clear_submission_metadata()

        return result

    def send_files(self, sub, ds):

        for id in sub['bundle']:
            file = DataFile().get_record(ObjectId(id))
            file_location = file['file_location']
            file_name = file['name']
            with open(file_location, 'rb') as f:
                contents = f.read()
                ds.upload_file(file_name, contents, zip_files=False)

    def send_files_curl(self, persistent_id=str()):
        """
        function uses curl to add datafiles to a Dataverse dataset, given its persistent_id (DOI)
        :param persistent_id:
        :return:
        """

        # get submission record
        sub = self.submission_record

        datafiles = sub.get("bundle_meta", list())

        # get all pending files
        pending_files = [x for x in datafiles if x.get("upload_status", False) is False]

        if not pending_files:  # update status and exit method
            if sub.get("complete", False) is False:
                sub['complete'] = True
                sub['completed_on'] = datetime.now()
                sub['target_id'] = sub.pop('_id', self.submission_id)
                Submission().save_record(dict(), **sub)

            return True

        # compose api call
        api_call = 'curl -H "X-Dataverse-key:{api_token}" -X POST -F \'file=@{data_file}\' -F \'jsonData={{"description":"Datafile","categories":["Data"], "restrict":"true"}}\' "{server_url}/api/datasets/:persistentId/add?persistentId={persistent_id}"'
        api_call = api_call.format(api_token=self.api_token,
                                   server_url=self.host,
                                   persistent_id=persistent_id,
                                   data_file='mock-datafile')

        for df in pending_files:
            upload_string = api_call.replace("mock-datafile", df.get("file_path", str()))
            try:
                receipt = subprocess.check_output(upload_string, shell=True)
            except Exception as e:
                exception_message = "Error uploading file " + df.get("file_path", str()) + " : " + str(e)
                self.report_error(exception_message)
            else:
                df["upload_status"] = True

        # if all files uploaded, mark submission as complete
        pending_files = [x for x in pending_files if x.get("upload_status", False) is False]

        if pending_files:
            return False

        sub['complete'] = True
        sub['completed_on'] = datetime.now()
        sub['target_id'] = sub.pop('_id', self.submission_id)
        Submission().save_record(dict(), **sub)

        return True

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

    def get_registered_types(self):
        """
        function uses a schema mapping of Dataverse types to drive conversion from cgcore to dataverse metadata
        Schema source: https://docs.google.com/spreadsheets/d/13HP-jI_cwLDHBetn9UKTREPJ_F4iHdAvhjmlvmYdSSw/edit#gid=0
        :return:
        """

        df = pd.read_csv(os.path.join(RESOLVER["cg_core_utils"], 'dataverse_schema_mapping.csv'))

        df.value = df['value'].fillna('')
        df.parent = df['parent'].fillna('')
        df.copo_id = df['copo_id'].fillna('')
        df.rename(index=str, columns={"dataverse_id": "typeName"}, inplace=True)

        Attribute = namedtuple('Attribute', ['typeName', 'typeClass', 'multiple', 'value', 'parent', 'copo_id'])
        registered_attibutes = [Attribute(**x) for x in df.to_dict('records')]

        return registered_attibutes

    def do_conversion(self):
        """
        function manages the conversion from CG Core to Dataverse types
        :return:
        """

        template = self.get_metadata_template()
        user_data = self.submission_record.get("meta", dict()).get("fields", list())
        citation_fragment = template["datasetVersion"]["metadataBlocks"]["citation"]
        citation_fragment["fields"] = self.get_dv_attributes(user_data=user_data)
        citation_fragment["displayName"] = self.get_display_name()

        return self.dump_metadata(template)

    def get_metadata_template(self):
        schemas_utils_paths = RESOLVER["cg_core_utils"]

        try:
            template = data_utils.json_to_pytype(os.path.join(schemas_utils_paths, 'dataverse_dataset_template.json'))
        except Exception as e:
            self.report_error("Couldn't retrieve Dataverse template. " + str(e))
            raise

        return template

    def get_dv_attributes(self, user_data):
        """
        function sets attribute value for Dataverse fields from user data
        :param user_data:
        :return:
        """
        fields = list()

        for attrib in self.get_registered_types():
            # dependent attribute - ignore for now
            if attrib.parent:
                continue

            # predefined values
            elif type(attrib.value) is bool or attrib.value:
                field = dict(attrib._asdict())

                if attrib.multiple is True:
                    field['value'] = [field['value']]

                field.pop('parent', None)
                field.pop('copo_id', None)
                fields.append(field)

            # primitive and controlledVocabulary types
            elif attrib.typeClass in ["primitive", "controlledVocabulary"]:
                val = [x["vals"] for x in user_data if x.get("copo_id", str()) == attrib.copo_id]
                if val:
                    val = val[0]
                field = self.get_dv_primitive(attrib, val)
                if field:
                    fields.append(field)

            # compound type
            elif attrib.typeClass == "compound":
                children = [x for x in self.get_registered_types() if x.parent == attrib.typeName]

                if not children:
                    continue

                values = list()

                children_values = dict()
                for child in children:
                    # obtain predefined values
                    predefined_children_values = list()
                    if type(child.value) is bool or child.value:
                        vals = child.value
                        if attrib.multiple is True:
                            vals = [vals]

                        predefined_children_value = self.get_dv_primitive(child, vals)

                        if predefined_children_value:
                            predefined_children_values.append(predefined_children_value)

                        continue

                    vals = [x["vals"] for x in user_data if x.get("copo_id", str()) == child.copo_id]

                    if vals:
                        vals = vals[0]
                        if not isinstance(vals, list):
                            vals = [vals]

                        for indx, vv in enumerate(vals):
                            children_values.setdefault(indx, []).append(self.get_dv_primitive(child, vv))

                for entry in children_values:
                    new_dict = dict()
                    for descendant in children_values[entry]:
                        new_dict[descendant["typeName"]] = descendant

                    # add predefined children values
                    for descendant in predefined_children_values:
                        new_dict[descendant["typeName"]] = descendant

                    values.append(new_dict)

                field = self.get_dv_primitive(attrib, [1])  # pass any value to generate parent dict
                field["value"] = values
                fields.append(field)

        return fields

    def get_dv_primitive(self, attrib, val):
        """
        function returns schema fragment for a dataverse primitive type, given val
        :param attrib:
        :param val:
        :return:
        """

        field = dict()

        if isinstance(val, list) and attrib.multiple is False:
            value = val[0]
        elif not isinstance(val, list) and attrib.multiple is True:
            value = [val]
        else:
            value = val

        if value:
            field = dict(attrib._asdict())
            field['value'] = value
            field.pop('parent', None)
            field.pop('copo_id', None)

        return field

    def get_display_name(self):
        """
        sets display name for Dataset
        :return:
        """

        profile = DAComponent(component="profile").get_record(self.submission_record.get("profile_id", str()))

        return profile.get("title", str())

    def dump_metadata(self, dv_metadata):
        """
        function write converted metadata to file and returns the path on success
        :return:
        """

        # create submission file path
        if not os.path.exists(self.file_path):
            try:
                os.makedirs(self.file_path)
            except Exception as e:
                self.report_error("Error creating submission file path. " + str(e))
                raise

        path_to_json = os.path.join(self.file_path, 'dataset.json')

        try:
            with open(path_to_json, "w") as ff:
                ff.write(json.dumps(dv_metadata))
        except Exception as e:
            self.report_error("Error writing Dataset metadata to file. " + str(e))
            raise

        return path_to_json

    def report_error(self, error_message):
        print(error_message)

        try:
            lg.log('Submission ID: ' + self.submission_id + " " + error_message, level=Loglvl.ERROR,
                   type=Logtype.FILE)
        except Exception as e:
            pass

        return False



def prettify(elem):
    # Return a pretty-printed XML string for the Element.
    rough_string = tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")
