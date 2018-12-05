# Created by fshaw at 21/11/2018
import os
from django.conf import settings
import uuid
import requests
from dal.copo_da import Submission, DataFile
from web.apps.web_copo.schemas.utils import data_utils
from dal.copo_da import Profile, DataFile
import datetime
from bson import ObjectId, json_util
import xml.etree.ElementTree as et
from dataverse.exceptions import OperationFailedError
import json


class CkanSubmit:
    host = None
    headers = None
    url = None

    def __init__(self, sub_id=None):
        if sub_id:
            self.host = Submission().get_dataverse_details(sub_id)
            self.headers = {'X-CKAN-API-Key': self.host['apikey']}

            if self.host["url"].endswith(".org"):
                self.host["url"] = self.host["url"] + "/api/3/action/"


    def submit(self, sub_id, dataFile_ids=None):
        s = Submission().get_record(ObjectId(sub_id))
        if s["meta"]["new_or_existing"] == "existing":
            dataset_id = s["identifier"]
        else:
            # create dataverse and get item_id
            data = self._create_ckan_metadata(s)
            fullurl = self.host["url"] + "package_create"
            resp = requests.post(fullurl, json=data, headers=self.headers)
            if resp.status_code == 200:
                # package was created normally
                data = json.loads(resp.content.decode("utf-8"))
                dataset_id = data["result"]["id"]
                data = {
                    "package_id": dataset_id
                }
                fullurl = self.host["url"] + "resource_create"
            elif resp.status_code == 409:
                # there is a conflict so update rather than create
                fullurl = self.host["url"] + "package_show"
                resp = requests.post(fullurl, json={"name_or_id": data["name"]})
                data = json.loads(resp.content.decode("utf-8"))
                dataset_id = data["result"]["id"]
                data = {
                    "package_id": dataset_id
                }
                fullurl = self.host["url"] + "resource_create"
            else:
                return json.dumps({"status": 1, "message": resp.reason})

        # now we have a dataset id to which to add the datafile
        for f in s["bundle"]:
            df = DataFile().get_record(ObjectId(f))
            # upload file
            f = open(df["file_location"], 'rb')

            try:
                ext = file_name, file_ext = os.path.splitext(df["name"])
                ext = ext[1].split('.')[1]
            except:
                ext = ""
            now = str(datetime.date.today())
            data["name"] = df["name"]
            data["created"] = now
            data["format"] = ext
            try:
                resp = requests.post(fullurl,
                                     data=data,
                                     files=f,
                                     headers=self.headers
                                     )
            except ValueError:
                resp = requests.post(fullurl,
                                     data=data,
                                     files=f,
                                     headers=self.headers
                                     )
            if resp.status_code == 200:
                details = json.loads(resp.content.decode("utf-8"))
                self._update_and_complete_submission(details, sub_id)
            elif resp.status_code == 409:
                fullurl = self.host["url"] + "package_show"
                resp = resp.post(fullurl, data={"id": dataset_id})
                # now iterate through resources to get matching name
                resources = json.dumps(resp.content.decode("utf-8"))["result"]["resources"]
                fullurl = self.host["url"] + "resource_update"
            else:
                return json.dumps({"status": 1, "message": resp.reason})
        return Submission().mark_submission_complete(ObjectId(sub_id))

    def _update_and_complete_submission(self, details, sub_id):
        Submission(ObjectId(sub_id)).insert_ckan_accession(sub_id, details)

    def _get_all_datasets(self):
        fullurl = self.host['url'] + "package_list?"
        resp = requests.get(fullurl)
        if resp.status_code == 200:
            return resp.content.decode('utf-8')
        else:
            return json.dumps({"status": 1, "message": "error getting datasets"})

    def _create_ckan_metadata(self, s):
        # get file
        file = DataFile().get_record(ObjectId(s["bundle"][0]))
        out = dict()
        out["name"] = file.get("description", {}).get("attributes", {}).get("title_author_contributor", {}) \
            .get("title", "").replace(" ", "_")

        #out["name"] = str(uuid.uuid4())

        out["private"] = False
        out["author"] = file.get("description", {}).get("attributes", {}).get("title_author_contributor", {}) \
            .get("creator", "")
        out["author_email"] = file.get("description", {}).get("attributes", {}).get("title_author_contributor", {}) \
            .get("contributor", "")
        out["maintainer"] = file.get("description", {}).get("attributes", {}).get("title_author_contributor", {}) \
            .get("creator", "")
        out["maintainer_email"] = file.get("description", {}).get("attributes", {}).get("title_author_contributor", {}) \
            .get("contributor", "")
        out["notes"] = file.get("description", {}).get("attributes", {}).get("subject_description", {}) \
            .get("description", "")
        out["url"] = file.get("description", {}).get("attributes", {}).get("other_fields", {}) \
            .get("URI", "")
        out["version"] = ""
        # this can change to deleted to stop being shown in searches
        out["state"] = "active"
        out["type"] = ""
        out["tags"] = []
        out["extras"] = []
        return out
