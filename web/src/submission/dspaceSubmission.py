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
            self._add_to_dspace(s)
        else:
            # create new
            self._create_and_add_to_dspace(s)
        return True

    def _add_to_dspace(self, sub):

        dspace_url = sub['destination_repo']['url']
        email = sub['destination_repo']['username']
        password = sub['destination_repo']['password']
        login_url = dspace_url + "/rest/login"
        resp = requests.post(login_url, {"email": email, "password": password})
        login_details = resp.cookies["JSESSIONID"]
        item_id = sub['meta']['identifier']

        for s in sub['bundle']:
            f = DataFile().get_record(ObjectId(s))
            name = f['name']
            location = f['file_location']
            description = f['description']['attributes']['subject_description']['description']
            # files = {name: open(location, 'rb')}

            bitstream_url = dspace_url + "/rest/items/" + item_id + "/bitstreams?name=" + name + "&description=" + description
            headers = {"Content-Type": "application/json", "accept": "application/json"}
            policy = [{"action": "DEFAULT_*", "epersonId": -1, "groupId": 0, "resourceId": 47166,
                       "resourceType": "bitstream", "rpDescription": None, "rpName": None, "rpType": "TYPE_INHERITED",
                       "startDate": None, "endDate": None}]
            bitstream = {"name": name,
                         "type": "bitstream",
                         "bundleName": "ORIGINAL",
                         "policies": policy,
                         }

            resp = requests.post(bitstream_url, data=bitstream, headers=headers, cookies={"JSESSIONID": login_details})
            if resp.status_code == 200:
                c = resp.content.decode('utf-8')
                data = json.loads(c)
                fi = open(location, 'rb')
                if "uuid" in data:
                    data_url = dspace_url + "/rest/bitstreams/" + data["uuid"] + "/data"
                else:
                    data_url = dspace_url + "/rest/bitstreams/" + data["id"] + "/data"
                data_resp = requests.put(data_url, data=fi, headers=headers, cookies={"JSESSIONID": login_details})
                if data_resp.status_code == 200:
                    self._update_submission(sub, data_resp)
            else:
                return (str(resp.status_code) + " ," + resp.reason + " ," + resp.content)
        logout_url = dspace_url + '/rest/logout'
        requests.post(logout_url, cookies={"JSESSIONID": login_details})

        return True

    def _create_and_add_to_dspace(self, sub):
        print(sub)
        return True

    def _update_submission(self, sub, data_resp):
        print(data_resp)

    def get_dspace_communites(self):
        url = self.host['url']
        url = url + '/rest/communities?limit=1000'
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
