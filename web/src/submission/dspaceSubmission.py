# Created by fshaw at 13/09/2018
from django.http import HttpResponse
from dal.copo_da import Submission, DataFile
import requests
import json
from web.apps.web_copo.schemas.utils import data_utils
from bson import ObjectId


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
        if 'dspace_item_name' in s['meta']:
            # submit to existing
            return self._add_to_dspace(s)
        else:
            # create new
            return self._create_and_add_to_dspace(s)
        return True

    def _add_to_dspace(self, sub):

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        # get data required and perform login
        dspace_url = sub['destination_repo']['url']
        email = sub['destination_repo']['username']
        password = sub['destination_repo']['password']
        login_url = dspace_url + "/rest/login"
        params = {"email": email, "password": password}
        resp = requests.post(login_url, json=params)
        # store session identifier for future requests
        if resp.status_code != 200:
            return {"status": 1, "message": "error logging into dSpace"}
        else:
            try:
                login_details = resp.cookies["JSESSIONID"]
                dspace_type = 6
            except KeyError:
                login_details = resp.content
                dspace_type = 5
        # get item identifier, this is where we will deposit bitstream
        item_id = sub['meta']['identifier']

        for s in sub['bundle']:
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
            bitstream_url = dspace_url + "/rest/items/" + str(item_id) + "/bitstreams?name=" + name + "&description=" + description
            # make sure json is set here or dspace will return XML response
            headers = {"Content-Type": "application/json", "accept": "application/json"}
            policy = [{"action": "DEFAULT_*", "epersonId": -1, "groupId": 0, "resourceId": 47166,
                       "resourceType": "bitstream", "rpDescription": None, "rpName": None, "rpType": "TYPE_INHERITED",
                       "startDate": None, "endDate": None}]
            bitstream = {"name": name,
                         "type": "bitstream",
                         "bundleName": "ORIGINAL",
                         "policies": policy,
                         }

            # request new bitstream
            if dspace_type == 6:
                resp = requests.post(bitstream_url, data=bitstream, headers=headers, cookies={"JSESSIONID": login_details})
            elif dspace_type == 5:
                resp = requests.post(bitstream_url, json=bitstream, headers={"rest-dspace-token": login_details, "accept": "application/json"})

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
                        data_resp = requests.put(data_url, data=file_stream, headers={"rest-dspace-token": login_details})
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

    def _create_and_add_to_dspace(self, sub):
        print(sub)
        return True

    def _update_submission(self, sub, data_resp):
        print(data_resp)

    def _update_dspace_submission(self, sub, dspace_url, data_id):
        data_url = dspace_url + "/rest/bitstreams/" + str(data_id)
        resp = requests.get(data_url)
        data = json.loads(resp.content.decode('utf-8'))
        data["uuid"] = data.pop("id")
        data['dspace_instance'] = dspace_url
        Submission().insert_dspace_accession(sub, data)

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
