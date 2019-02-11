# Created by fshaw at 13/09/2018
from dal.copo_da import Submission, DataFile
import requests, os
import json
from web.apps.web_copo.schemas.utils import data_utils
from bson import ObjectId
from urllib.request import quote
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas


class DspaceSubmit(object):
    host = None
    headers = None
    numeric_limit = 50
    error_msg = "Cannot communicate with server. Are you connected to a network?"
    not_found = "Nothing Found for Entry"

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
        new_or_existing = s['meta']['new_or_existing']
        return self._add_to_dspace(s, new_or_existing)

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
            #  now try using v5 method
            params = {"email": email, "password": password}
            resp = requests.post(login_url, json=params)
            if resp.status_code != 200:
                # there is actually a problem with the login process
                return {"status": 1, "message": "error logging into dSpace: error" + str(resp.status_code)}
        try:
            login_details = resp.cookies["JSESSIONID"]
            dspace_type = 6
        except KeyError:
            login_details = resp.content
            dspace_type = 5
        # get item identifier, this is where we will deposit bitstream
        if new_or_existing == "existing":
            item_id = sub['meta']['identifier']
        elif new_or_existing == "new":
            dspace_meta = self._create_dspace_meta(sub)
            # create item
            collection_id = sub["meta"]["identifier"]
            # get name
        for s in sub['bundle']:
            for el in dspace_meta["metadata"]:
                if el["key"] == "dc.title":
                    name = el.get("value")

            new_item_url = dspace_url + "/rest/collections/" + str(collection_id) + "/items"
            if dspace_type == 6:
                resp_item = requests.post(new_item_url, json=dspace_meta,
                                          headers={"Content-Type": "application/json",
                                                   "accept": "application/json"}, cookies={"JSESSIONID": login_details})
            elif dspace_type == 5:
                resp_item = requests.post(new_item_url, json=dspace_meta,
                                          headers={"rest-dspace-token": login_details,
                                                   "Content-Type": "application/json",
                                                   "accept": "application/json"})
            if resp_item.status_code == 200:
                try:
                    item_id = json.loads(resp_item.content.decode('utf-8'))['id']
                except KeyError:
                    item_id = json.loads(resp_item.content.decode('utf-8'))['uuid']
            else:
                return {"status": 1, "message": "error creating new dspace item"}

            # for each file in submission bundle
            f = DataFile().get_record(ObjectId(s))
            # name is name without path
            name = f['name']
            # location is path/filename
            location = f['file_location']
            # get description from dc metadata
            try:
                description = f['description']['attributes']['subject_description']['description']
            except KeyError:
                description = "No Description Provided"

            # make bitstream first, n.b. that name and description need to be added as url params, not json data
            bitstream_url = dspace_url + "/rest/items/" + str(
                item_id) + "/bitstreams?name=" + name + "&description=" + description
            # make sure json is set here or dspace will return XML response
            headers = {"Content-Type": "application/json", "accept": "application/json"}
            policy = [{"action": "DEFAULT_*", "epersonId": -1, "groupId": 0, "resourceId": 47166,
                       "resourceType": "bitstream", "rpDescription": None, "rpName": None, "rpType": "TYPE_INHERITED",
                       "startDate": None, "endDate": None}]
            filename, file_extension = os.path.splitext(name)
            bitstream = {"name": name,
                         "description": name,
                         "type": "bitstream",
                         "format": file_extension,
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
                    self._update_dspace_submission(sub, dspace_url, data_id)
            else:
                return (str(resp.status_code) + " ," + resp.reason + " ," + resp.content.decode('utf-8'))
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
        #  get language of submission fields
        for f in sub["meta"]["fields"]:
            if f["dc"] == "dc.language":
                lang = f.get("vals", "")
                #  check if lang is array if so take first element
                if type(lang) != type(""):
                    lang = lang[0]
        # iterate fields and convert to format required by dspace
        for f in sub["meta"]["fields"]:
            val = f.get("vals", "")
            #  check if vals is array
            if type(val) != type(""):
                val = val[0]

            # key = f.get("dc", "").replace(' type=', '.')
            key = f.get("dc", "")
            # if val != "":
            # if key not in used_keys:
            el = {
                "key": key,
                "value": val,
                "language": lang
            }
            arr.append(el)
            used_keys.append(key)
        out["metadata"] = arr
        return out

    def _update_submission(self, sub, data_resp):
        print(data_resp)

    def _update_dspace_submission(self, sub, dspace_url, data_id):
        data_url = dspace_url + "/rest/bitstreams/" + str(data_id)
        resp = requests.get(data_url)
        data = json.loads(resp.content.decode('utf-8'))
        if "uuid" not in data:
            data["uuid"] = data.pop("id")
        data['dspace_instance'] = dspace_url
        Submission().insert_dspace_accession(sub, data)

    def _make_dspace_metadata(self, sub):
        pass

    def get_dspace_communites(self):
        url = self.host['url']
        url = url + '/rest/communities?limit=' + str(self.numeric_limit)
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

    def dc_dict_to_dc(self, sub_id):
        # get file metadata, call converter to strip out dc fields
        s = Submission().get_record(ObjectId(sub_id))
        f_id = s["bundle"][0]
        items = CgCoreSchemas().extract_repo_fields(str(f_id), "dSpace")
        '''
        meta = list()
        for i in items:
            if i["dc"] == "dc.title":
                i.update({"dspacename": i["dc"]})
                meta.append(i)
            elif i["dc"] == "dc.creator":
                meta.append(
                    {"dc": "dc.creator", "dspacename": "dc.contributor.author", "vals": i["vals"][0]})

            elif i["dc"] == "dc.date type=completion":
                i.update({"dspacename": "dc.date.accessioned"})
                meta.append(i)
            elif i["dc"] == "dc.rights license":
                i.update({"dspacename": "license"})
                meta.append(i)
            elif i["dc"] == "dc.source":
                i.update({"dspacename": "source"})
                meta.append(i)
            elif i["dc"] == "dc.description":
                i.update({"dspacename": i["dc"]})
                meta.append(i)
            elif i["dc"] == "dc.subject":
                i.update({"dspacename": i["dc"]})
                meta.append(i)
            else:
                meta.append(i)
            '''
        Submission().update_meta(sub_id, json.dumps(items))
