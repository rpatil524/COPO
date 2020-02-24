# Created by fshaw at 13/09/2018
from dal.copo_da import Submission, DataFile
import requests, os
import json
import traceback
from bson import ObjectId
from urllib.request import quote
from collections import namedtuple
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas
from web.apps.web_copo.schemas.utils.data_utils import get_base_url
from urllib.parse import urljoin
from dal import cursor_to_list
from submission.helpers import generic_helper as ghlper


class DspaceSubmit:
    def __init__(self, submission_id=str()):
        self.submission_id = submission_id

        self.host = None
        self.username = None
        self.password = None
        self.profile_id = None
        self.login_details = None
        self.dspace_type = None

    def submit(self):
        """
        function manages the submission of objects to ckan
        :return:
        """

        if not self.submission_id:
            return dict(status=False, message='Submission identifier not found!')

            # retrieve submssion record from db

        # specify filtering
        filter_by = dict(_id=ObjectId(str(self.submission_id)))

        # specify projection
        query_projection = {
            "_id": 1,
            "repository_docs.url": 1,
            "repository_docs.username": 1,
            "repository_docs.password": 1,
            "profile_id": 1,
            "meta.type": 1,
            "meta.params": 1,
            "complete": 1

        }

        doc = Submission().get_collection_handle().aggregate(
            [
                {"$addFields": {
                    "destination_repo_converted": {
                        "$convert": {
                            "input": "$destination_repo",
                            "to": "objectId",
                            "onError": 0
                        }
                    }
                }
                },
                {
                    "$lookup":
                        {
                            "from": "RepositoryCollection",
                            "localField": "destination_repo_converted",
                            "foreignField": "_id",
                            "as": "repository_docs"
                        }
                },
                {
                    "$project": query_projection
                },
                {
                    "$match": filter_by
                }
            ])

        records = cursor_to_list(doc)

        # get submission record
        try:
            submission_record = records[0]
        except Exception as ex:
            ghlper.logging_error(traceback.format_exc(), self.submission_id)
            message = "Submission record not found. Please try resubmitting."
            ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
            return dict(status='error', message=message)

        try:
            repository_info = submission_record['repository_docs'][0]
        except Exception as ex:
            ghlper.logging_error(traceback.format_exc(), self.submission_id)
            error_type = type(ex).__name__
            message = f"Couldn't retrieve repository information due to the following error: '{error_type}'"
            ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
            return dict(status='error', message=message)

        if str(submission_record.get("complete", False)).lower() == 'true':
            message = 'Submission is marked as complete!'
            ghlper.logging_info(message, self.submission_id)
            ghlper.update_submission_status(status='success', message=message, submission_id=self.submission_id)

            return dict(status=True, message=message)

        # set submission parameters
        self.host = repository_info.get("url", str())
        self.username = repository_info.get("username", str())
        self.password = repository_info.get("password", str())
        self.profile_id = submission_record.get("profile_id", str())

        # authenticate against the repository
        try:
            authentication_result = self._do_dspace_authenticate()
            if authentication_result['status'] is not True:
                return authentication_result
        except Exception as ex:
            user_message = f"DSpace Authentication error"  # risk of exposing login credentials
            ghlper.logging_error(traceback.format_exc(), self.submission_id)
            ghlper.update_submission_status(status='error', message=user_message, submission_id=self.submission_id)
            return dict(status='error', message=user_message)

        login_details, dspace_type = authentication_result['value']
        self.login_details = login_details
        self.dspace_type = dspace_type

        # check submission context and select submission pathway
        type = submission_record.get("meta", dict()).get("type", str())
        params = submission_record.get("meta", dict()).get("params", dict())

        if type == "new":  # create a dataset to submit
            return self._do_item_create_submit(**params)

        if type == "existing":  # a dataset specified proceed to submit
            return self._do_item_submit(**params)

        return dict(status=True, message="No status message provided!")

    def _do_dspace_authenticate(self):
        """
        function authenticates against the dspace repository to facilitate interactions
        :return:
        """

        login_url = urljoin(self.host, '/rest/login')

        # try to login using v6 method
        # special characters must be urlencoded (but only for version 6!)
        param_string = "?email=" + quote(self.username) + "&password=" + self.password

        try:
            response = requests.post(login_url + param_string)
        except Exception as ex:
            ghlper.logging_error(traceback.format_exc(), self.submission_id)
            message = f"DSpace Authentication error"  # risk of exposing login credentials
            ghlper.logging_error(traceback.format_exc(), self.submission_id)
            return dict(status='error', message=message)

        response_status_code = response.status_code

        if response_status_code != 200:
            # try using v5 method
            params = dict(email=self.username, password=self.password)
            try:
                response = requests.post(login_url, json=params)
            except Exception as ex:
                ghlper.logging_error(traceback.format_exc(), self.submission_id)
                message = f"DSpace Authentication error"  # risk of exposing login credentials
                ghlper.logging_error(traceback.format_exc(), self.submission_id)
                return dict(status='error', message=message)

            response_status_code = response.status_code

            if response_status_code != 200:
                error_code = response.status_code
                message = f"DSpace Authentication error: '{str(error_code)}'"
                ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                return dict(status='error', message=message)

        try:
            login_details = response.cookies["JSESSIONID"]
            dspace_type = 6
        except KeyError:
            login_details = response.content
            dspace_type = 5

        return dict(status=True, value=(login_details, dspace_type))

    def _do_item_submit(self, **params):
        """
        function fulfills submission given item identifier
        :param params:
        :return:
        """

        # get collection id for which a new item is to be created
        item_id = params.get("identifier", str())

        if not item_id:
            message = 'Missing item identifier! Please try resubmitting.'
            ghlper.logging_error(message, self.submission_id)
            ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
            return dict(status='error', message=message)

        return self._submit_datafiles(item_id=item_id)

    def _do_item_create_submit(self, **params):
        """
        function creates a new item to fulfill submission
        :return:
        """

        # get collection id for which a new item is to be created
        collection_id = params.get("identifier", str())

        if not collection_id:
            message = 'Missing collection identifier! Please try resubmitting.'
            ghlper.logging_error(message, self.submission_id)
            ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
            return dict(status='error', message=message)

        # convert to DSpace metadata
        try:
            submission_metadata = self._get_submission_metadata()
        except Exception as ex:
            ghlper.logging_error(traceback.format_exc(), self.submission_id)
            message = f"Error converting from CG Core to DSpace: '{str(ex)}'"
            ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
            return dict(status='error', message=message)

        # create item
        call_url = urljoin(self.host, f"/rest/collections/{collection_id}/items")
        dspace_meta = dict(metadata=submission_metadata)

        if self.dspace_type == 6:
            try:
                response = requests.post(call_url, json=dspace_meta,
                                         headers={"Content-Type": "application/json",
                                                  "accept": "application/json"},
                                         cookies={"JSESSIONID": self.login_details})
            except Exception as ex:
                ghlper.logging_error(traceback.format_exc(), self.submission_id)
                message = f"Error creating DSpace item: '{str(ex)}'"
                ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                return dict(status='error', message=message)

        elif self.dspace_type == 5:
            try:
                response = requests.post(call_url, json=dspace_meta,
                                         headers={"rest-dspace-token": self.login_details,
                                                  "Content-Type": "application/json",
                                                  "accept": "application/json"})
            except Exception as ex:
                ghlper.logging_error(traceback.format_exc(), self.submission_id)
                message = f"Error creating DSpace item: '{str(ex)}'"
                ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                return dict(status='error', message=message)

        if response.status_code == 200:
            response_data = response.json()
        else:
            error_message = response.reason
            message = f"Error creating DSpace item.'{error_message}'"
            ghlper.logging_error(message, self.submission_id)
            ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
            return dict(status='error', message=message)

        item_id = response_data.get("id", str()) or response_data.get("uuid", str())
        if not item_id:
            message = f"Error creating DSpace item. Couldn't obtain item identifier."
            ghlper.logging_error(message, self.submission_id)
            ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
            return dict(status='error', message=message)

        return self._submit_datafiles(item_id=item_id)

    def _get_submission_metadata(self):
        """
        function composes the metadata for a new dataset creation
        :return:
        """

        submission_metadata = list()

        # get user data
        description_metadata = Submission().get_submission_metadata(submission_id=self.submission_id)["meta"]

        # get metadata language

        lang = [x.get("vals", str()) for x in description_metadata if x.get("dc", str()) == "dc.language"]

        lang = lang[0] if lang else str()
        if isinstance(lang, list):
            lang = lang[0]

        # predefined fields

        try:
            url = get_base_url()
            submission_metadata.append(
                dict(key="dc.relation.ispartof", value=urljoin(url, 'copo/resolve/' + self.submission_id),
                     language=lang))
        except Exception as ex:
            ghlper.logging_error(traceback.format_exc(), self.submission_id)

        # define a mapping from cgcore to dspace fields
        MetaMap = namedtuple('MetaMap', ['repo', 'cgcore'])

        schema_mappings = [
            MetaMap(repo="dc.contributor.author", cgcore="dc.creator"),
            MetaMap(repo="", cgcore="dc.relation isPartOf"),  # doing this penalises the cgcore field
        ]

        # map defined fields first
        for mapping in schema_mappings:
            target_val = [x for x in description_metadata if x.get("dc", str()) == mapping.cgcore]

            if not target_val:
                continue

            target_dict = target_val[0]
            target_val = target_dict.get("vals", str())

            # remove mapped entry from list
            description_metadata.remove(target_dict)

            # can't map unspecified repository field
            if not mapping.repo:
                continue

            if isinstance(target_val, str) and target_val.strip() != "":
                submission_metadata.append(dict(key=mapping.repo, value=target_val, language=lang))

            # set one value from the list that isn't empty
            elif isinstance(target_val, list):
                target_val = [x for x in target_val if str(x).strip() != ""]
                if target_val:
                    submission_metadata.append(dict(key=mapping.repo, value=target_val[0], language=lang))

        # now map non-predefined entries
        for target_dict in description_metadata:
            # process key
            prefix = target_dict.get("prefix", "dc")
            key = target_dict.get("dc", str()).replace('dc.', f'{prefix}.', 1)
            key = '.'.join(key.split())
            key = '.'.join(key.split('.type='))
            key = key.lower()

            # process value
            target_val = target_dict.get("vals", str())
            if isinstance(target_val, str) and target_val.strip() != "":
                submission_metadata.append(dict(key=key, value=target_val, language=lang))

            # set one value from the list that isn't empty
            elif isinstance(target_val, list):
                target_val = [x for x in target_val if str(x).strip() != ""]
                if target_val:
                    submission_metadata.append(dict(key=key, value=target_val[0], language=lang))

        return submission_metadata

    def _submit_datafiles(self, item_id=str()):
        """
        function uploads files to DSpace given an item
        :param item_id:
        :return:
        """

        submission_record = Submission().get_collection_handle().find_one({'_id': ObjectId(self.submission_id)},
                                                                          {"bundle_meta": 1})

        # get files to upload
        datafiles = submission_record.get("bundle_meta", list())

        # set post parameters
        headers = {"Content-Type": "application/json", "accept": "application/json"}
        policy = [{"action": "DEFAULT_*", "epersonId": -1, "groupId": 0, "resourceId": 47166,
                   "resourceType": "bitstream", "rpDescription": None, "rpName": None, "rpType": "TYPE_INHERITED",
                   "startDate": None, "endDate": None}]

        for df in datafiles:
            # # check for already uploaded file
            # if str(df.get("upload_status", False)).lower() == 'true':
            #     continue

            file_basename = os.path.basename(df.get("file_path", str()))
            filename, file_extension = os.path.splitext(file_basename)
            file_extension = file_extension.lstrip(".")
            file_mimetype = self.get_media_type_from_file_ext(file_extension)

            name = description = filename

            bitstream_url = urljoin(self.host,
                                    f"/rest/items/{str(item_id)}/bitstreams?name={name}&description={description}")
            bitstream = dict(
                name=name,
                description=description,
                type="bitstream",
                format=file_mimetype,
                bundleName="ORIGINAL",
                policies=policy
            )

            # request new bitstream
            if self.dspace_type == 6:
                try:
                    response = requests.post(bitstream_url, data=bitstream, headers=headers,
                                             cookies={"JSESSIONID": self.login_details})
                except Exception as ex:
                    ghlper.logging_error(traceback.format_exc(), self.submission_id)
                    message = f"Error obtaining DSpace bitstream: '{str(ex)}'"
                    ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                    return dict(status='error', message=message)

            elif self.dspace_type == 5:
                try:
                    response = requests.post(bitstream_url, json=bitstream,
                                             headers={"rest-dspace-token": self.login_details,
                                                      "accept": "application/json"})
                except Exception as ex:
                    ghlper.logging_error(traceback.format_exc(), self.submission_id)
                    message = f"Error obtaining DSpace bitstream: '{str(ex)}'"
                    ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                    return dict(status='error', message=message)

            if response.status_code == 200:
                response_data = response.json()
            else:
                error_message = response.reason
                message = f"Error obtaining DSpace bitstream.'{error_message}'"
                ghlper.logging_error(message, self.submission_id)
                ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                return dict(status='error', message=message)

            data_id = response_data.get("id", str()) or response_data.get("uuid", str())

            if not data_id:
                message = "Error uploading datafile. Couldn't obtain bitstream identifier."
                ghlper.logging_error(message, self.submission_id)
                ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                return dict(status='error', message=message)

            data_url = urljoin(self.host, f"/rest/bitstreams/{str(data_id)}/data")

            # upload file
            try:
                with open(df.get("file_path", str()), 'rb') as file_stream:
                    if self.dspace_type == 6:
                        response = requests.put(data_url, data=file_stream, headers=headers,
                                                 cookies={"JSESSIONID": self.login_details})
                    elif self.dspace_type == 5:
                        response = requests.put(data_url, data=file_stream,
                                                 headers={"rest-dspace-token": self.login_details})
            except Exception as ex:
                ghlper.logging_error(traceback.format_exc(), self.submission_id)
                message = f"Error uploading datafile: '{str(ex)}'"
                ghlper.update_submission_status(status='error', message=message, submission_id=self.submission_id)
                return dict(status='error', message=message)

            if response.status_code == 200:
                self._update_dspace_submission(submission_record, self.host, data_id, item_id)

        logout_url = urljoin(self.host, "/rest/logout")
        if self.dspace_type == 6:
            requests.post(logout_url, cookies={"JSESSIONID": self.login_details})
        elif self.dspace_type == 5:
            requests.post(logout_url, headers={"rest-dspace-token": self.login_details})
        Submission().mark_submission_complete(self.submission_id)

        status_message = "Submission is marked as complete!"
        ghlper.logging_info(status_message, self.submission_id)
        ghlper.update_submission_status(status='success', message=status_message, submission_id=self.submission_id)

        return dict(status='success', message=status_message)

    def _add_to_dspace(self, sub, new_or_existing):
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        # get data required and perform login
        dspace_url = sub['destination_repo']['url']
        email = sub['destination_repo']['username']
        password = sub['destination_repo']['password']
        login_url = dspace_url + "/rest/login"

        # try to login using v6 method
        # special characters must be urlencoded (but only for version 6!)
        param_string = "?email=" + quote(email) + "&password=" + password
        resp = requests.post(login_url + param_string)
        # store session identifier for future requests
        if resp.status_code != 200:
            # now try using v5 method
            params = {"email": email, "password": password}
            resp = requests.post(login_url, json=params)
            if resp.status_code != 200:
                # there is actually a problem with the login process
                return {"status": 401, "message": "error logging into dSpace: error" + str(resp.status_code)}
        try:
            login_details = resp.cookies["JSESSIONID"]
            dspace_type = 6
        except KeyError:
            login_details = resp.content
            dspace_type = 5

        # get item identifier, this is where we will deposit bitstream
        if new_or_existing == "existing":
            # if existing we should already have item id
            try:
                item_id = sub['meta']['identifier']
            except KeyError as e:
                return {"status": 404, "message": "No dSpace Item identifier found, please try selecting item again."}

        elif new_or_existing == "new":
            # if new we must create a new item in the given collection
            dspace_meta = self._create_dspace_meta(sub)
            # sub["meta"]["identifier"] in this case is the collection id
            collection_id = sub["meta"]["identifier"]
            # get name and description
            description = ""
            for el in dspace_meta["metadata"]:
                if "description" in el["key"]:
                    description = el["value"]
            if description == "":
                description = "No description provided"

            # create the item
            new_item_url = dspace_url + "/rest/collections/" + str(collection_id) + "/items"
            if dspace_type == 6:
                resp_item = requests.post(new_item_url, json=dspace_meta,
                                          headers={"Content-Type": "application/json",
                                                   "accept": "application/json"},
                                          cookies={"JSESSIONID": login_details})
            elif dspace_type == 5:
                resp_item = requests.post(new_item_url, json=dspace_meta,
                                          headers={"rest-dspace-token": login_details,
                                                   "Content-Type": "application/json",
                                                   "accept": "application/json"})
            if resp_item.status_code == 200:
                # get item id of the item we just created
                try:
                    item_id = json.loads(resp_item.content.decode('utf-8'))['id']
                except KeyError:
                    item_id = json.loads(resp_item.content.decode('utf-8'))['uuid']
            else:
                return {"status": resp_item.status_code, "message": resp_item.reason}

        # now upload files
        for s in sub['bundle']:
            # for each file in submission bundle
            f = DataFile().get_record(ObjectId(s))
            # name is name without path
            name = f['name']
            description = f['name']
            # location is path/filename
            location = f['file_location']

            # make bitstream first, n.b. that name and description need to be added as url params, not json data
            bitstream_url = dspace_url + "/rest/items/" + str(
                item_id) + "/bitstreams?name=" + name + "&description=" + description
            # make sure json is set here or dspace will return XML response
            headers = {"Content-Type": "application/json", "accept": "application/json"}
            policy = [{"action": "DEFAULT_*", "epersonId": -1, "groupId": 0, "resourceId": 47166,
                       "resourceType": "bitstream", "rpDescription": None, "rpName": None, "rpType": "TYPE_INHERITED",
                       "startDate": None, "endDate": None}]

            # get correct bitstream file extension lookup
            filename, file_extension = os.path.splitext(name)
            if "." in file_extension:
                file_extension = file_extension.replace(".", "")
            ext = self.get_media_type_from_file_ext(file_extension)

            bitstream = {"name": name,
                         "description": description,
                         "type": "bitstream",
                         "format": ext,
                         "bundleName": "ORIGINAL",
                         "policies": policy,
                         }

            # request new bitstream
            if dspace_type == 6:
                resp = requests.post(bitstream_url, data=bitstream, headers=headers,
                                     cookies={"JSESSIONID": login_details})
            elif dspace_type == 5:
                resp = requests.post(bitstream_url, json=bitstream,
                                     headers={"rest-dspace-token": login_details, "accept": "application/json"})

            if resp.status_code == 200:
                # get bitstream id and open file to be uploaded
                c = resp.content.decode('utf-8')
                data = json.loads(c)

                if "uuid" in data:
                    data_id = data["uuid"]
                else:
                    data_id = data["id"]

                data_url = dspace_url + "/rest/bitstreams/" + str(data_id) + "/data"

                # upload file
                with open(location, 'rb') as file_stream:
                    if dspace_type == 6:
                        data_resp = requests.put(data_url, data=file_stream, headers=headers,
                                                 cookies={"JSESSIONID": login_details})
                    elif dspace_type == 5:
                        data_resp = requests.put(data_url, data=file_stream,
                                                 headers={"rest-dspace-token": login_details})
                if data_resp.status_code == 200:
                    self._update_dspace_submission(sub, dspace_url, data_id, item_id)
            else:
                return {"status": resp.status_code, "message": resp.reason}
        logout_url = dspace_url + '/rest/logout'
        if dspace_type == 6:
            requests.post(logout_url, cookies={"JSESSIONID": login_details})
        elif dspace_type == 5:
            requests.post(logout_url, headers={"rest-dspace-token": login_details})
        Submission().mark_submission_complete(sub["_id"])
        return True

    def _create_dspace_meta(self, sub):
        # need to create metadata fragment for dspace
        used_keys = []
        out = dict()
        arr = []
        #  get language of submission fields
        for f in sub["meta"]["fields"]:
            if f["dc"] == "dc.language":
                lang = f.get("vals", "")
                #  check if lang is array if so take first element
                # if type(lang) != type(""):
                #    lang = lang[0]
                if isinstance(lang, list):
                    lang = lang[0] if lang else ""
                break
        # iterate fields and convert to format required by dspace
        for f in sub["meta"]["fields"]:
            val = f.get("vals", "")
            #  check if vals is array
            if isinstance(val, list):
                val = val[0] if val else ""
                # if type(val) != type(""):
            #     if val != None:
            #         val = val[0]
            #     else:
            #         val = ""

            key = f.get("dc", "")

            # remove dc prefix and add correct prefix (some fields require dcterms)
            temp = key.split("dc.")[1]
            key = f.get("prefix", "dc") + "." + temp
            # remove spaces, types and make lowercase
            key = key.replace(" ", ".")
            key = key.replace(".type=", ".")
            key = key.lower()

            # deal with special cases
            if "dc.contributor" in key:
                key = "dcterms.contributor"
            elif "dc.relation.references" in key:
                key = "dcterms.references"
                url = get_base_url()
                val = urljoin(url, 'copo/resolve/' + str(sub["_id"]))

            elif "conformsto" in key:
                key = "dcterms.conformsto"
            elif "dc.date.availability" in key:
                key = "dc.date.available"
            elif "dc.date.completion" in key:
                key = "dc.date.issued"
            elif "dcterms.creator" in key:
                key = "dc.contributor.author"
            elif "dc.creator.affiliation" in key:
                key = "dc.contributor"
            elif "dc.relation.isrequiredby" in key:
                key = "dcterms.isRequiredBy"
            elif "dc.relation.isreplacedby" in key:
                key = "dcterms.isReplacedBy"
            elif "dc.relation.ispartof" in key:
                url = get_base_url()
                val = urljoin(url, 'copo/resolve/' + str(sub["_id"]))

            # add field as entry in list of dicts
            el = {
                "key": key,
                "value": val,
                "language": lang
            }
            arr.append(el)
            used_keys.append(key)
        out["metadata"] = arr
        return out

    def _update_dspace_submission(self, sub, dspace_url, data_id, item_id):
        data_url = dspace_url + "/rest/bitstreams/" + str(data_id)
        meta_url = dspace_url + "/rest/items/" + str(item_id) + "?expand=all"
        resp = requests.get(data_url)
        data = json.loads(resp.content.decode('utf-8'))
        if "uuid" not in data:
            data["uuid"] = data.pop("id")
        data['dspace_instance'] = dspace_url
        data["item_id"] = item_id
        data["meta_url"] = meta_url
        Submission().insert_dspace_accession(sub, data)

    def get_dspace_communites(self):
        numeric_limit = 50
        url = self.host['url']
        url = url + '/rest/communities?limit=' + str(numeric_limit)
        resp = requests.get(url)

        if resp.status_code == 200:
            items = json.loads(resp.content.decode('utf-8'))
            for i in items:
                if 'uuid' in i:
                    i['id'] = i.pop('uuid')
                    print(i['link'])
            return json.dumps(items)
        else:
            return {"error": self.error_msg}

    def get_dspace_subcommunities_and_collections(self, community_id):
        url = self.host['url']
        url = url + '/rest/communities/' + community_id + '?expand=collections'
        resp = requests.get(url)

        if resp.status_code == 200:
            tmp = json.loads(resp.content.decode('utf-8'))
            out = tmp['subcommunities'] + tmp['collections']

        return json.dumps(out)

    def get_dspace_collection(self, collection_id):
        url = self.host['url']
        url = url + '/rest/communities/' + collection_id + '/collections'
        resp = requests.get(url)
        if resp.status_code == 200:
            items = json.loads(resp.content.decode('utf-8'))

            for i in items:
                if 'uuid' in i:
                    i['id'] = i.pop('uuid')
                    print(i['link'])
            return json.dumps(items)
        elif resp.status_code == 404:
            return json.dumps({"error": self.not_found})
        else:
            return json.dumps({"error": self.error_msg})

    def get_dspace_items(self, collection_id):
        url = self.host['url']
        url = url + '/rest/collections/' + collection_id + '/items'
        resp = requests.get(url)
        if resp.status_code == 200:
            items = json.loads(resp.content.decode('utf-8'))

            for i in items:
                if 'uuid' in i:
                    i['id'] = i.pop('uuid')
                    print(i['link'])
            return json.dumps(items)
        elif resp.status_code == 404:
            return json.dumps({"error": self.not_found})
        else:
            return json.dumps({"error": self.error_msg})

    def get_media_type_from_file_ext(self, ext):
        """
        function returns the mimetype matching an extension
        :param ext:
        :return:
        """
        mime_type = dict(
            pdf="application/pdf",
            ai="application/postscript",
            eps="application/postscript",
            ps="application/postscript",
            xls="application/vnd.ms-excel",
            xlsx="application/vnd.ms-excel",
            ppt="application/vnd.ms-powerpoint",
            gif="image/gif",
            jpg="image/jpeg",
            jpeg="image/jpeg",
            png="image/png",
            tif="image/tiff",
            tiff="image/tiff",
            bmp="image/x-ms-bmp",
            html="text/html",
            htm="text/html",
            asc="text/plain",
            txt="text/plain",
            xml="text/xml",
            doc="application/msword",
            docx="application/msword",
        )

        return mime_type.get(ext.lower(), str())

    def dc_dict_to_dc(self, sub_id):
        # get file metadata, call converter to strip out dc fields
        s = Submission().get_record(ObjectId(sub_id))
        f_id = s["bundle"][0]
        items = CgCoreSchemas().extract_repo_fields(str(f_id), "dSpace")
        Submission().update_meta(sub_id, json.dumps(items))
