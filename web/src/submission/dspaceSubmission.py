# Created by fshaw at 13/09/2018
from django.http import HttpResponse
from dal.copo_da import Submission
import requests
import json


class DspaceSubmit(object):
    host = None
    headers = None

    error_msg = "Cannot communicate with server. Are you connected to a network?"
    not_found = "Nothing Found for Entry"

    def __init__(self, sub_id=None):
        if sub_id:
            self.host = Submission().get_dataverse_details(sub_id)
            self.headers = {'X-Dataverse-key': self.host['apikey']}

    def get_dspace_communites(self):
        url = self.host['url']
        url = url + '/rest/communities?limit=2'
        resp = requests.get(url)

        if resp.status_code == 200:
            return resp.content.decode('utf-8')
        else:
            return {"error": self.error_msg}

    def get_dspace_collection(self, collection_id):
        url = self.host['url']
        url = url + '/rest/collections/' + collection_id
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.content.decode('utf-8')
        elif resp.status_code == 404:
            return json.dumps({"error": self.not_found})
        else:
            return json.dumps({"error": self.error_msg})

    def get_dspace_items(self, collection_id):
        url = self.host['url']
        url = url + '/rest/collections/' + collection_id + '/items'
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.content.decode('utf-8')
        elif resp.status_code == 404:
            return json.dumps({"error": self.not_found})
        else:
            return json.dumps({"error": self.error_msg})
