# Created by fshaw at 21/11/2018
import os, re, string, json, uuid
import requests
from dal.copo_da import Submission
from dal.copo_da import DataFile
import datetime
from bson import ObjectId
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas


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

        if s["meta"]["new_or_existing"] == "new":
            # create and get item_id
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
            elif resp.status_code == 400:
                instance = re.findall("https", fullurl)
                if len(instance) == 0:
                    fullurl = fullurl.replace("http", "https")
                resp = requests.post(fullurl, json=data, headers=self.headers)
                if resp.status_code != 200:
                    details = json.loads(resp.content.decode("utf-8"))
                    try:
                        msg = details["error"]["message"]
                    except KeyError:
                        msg = details["error"]["name"][0]

                    return json.dumps({"status": resp.status_code, "message": msg})
                else:
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
                return json.dumps({"status": 500, "message": resp.reason + " - " + resp.text})
        else:
            data = {"package_id": s["meta"]["identifier"]}

        # now we have a dataset id to which to add the datafile
        for f in s["bundle"]:
            # data = dict()
            df = DataFile().get_record(ObjectId(f))
            # upload file
            f = {'file': open(df["file_location"], 'rb')}

            try:
                ext = file_name, file_ext = os.path.splitext(df["name"])
                ext = ext[1].split('.')[1]
            except:
                ext = ""
            now = str(datetime.date.today())
            data["name"] = df["name"]
            data["created"] = now
            data["format"] = ext
            data["upload"] = f
            fullurl = self.host["url"] + "resource_create"
            data["url"] = str(uuid.uuid4())
            try:
                print(self.headers)
                resp = requests.post(fullurl,
                                     data=data,
                                     files=f,
                                     headers=self.headers
                                     )
            except (TypeError, ValueError) as e:
                print(e)
                # for some reason this fails the first time
                resp = requests.post(fullurl,
                                     data=data,
                                     files=f,
                                     headers=self.headers
                                     )
            except TypeError as t:
                print(t)
            if resp.status_code == 200:
                details = json.loads(resp.content.decode("utf-8"))
                self._update_and_complete_submission(details, sub_id)
            elif resp.status_code == 400:
                # try again checking for https
                instance = re.findall("https", fullurl)
                if len(instance) == 0:
                    fullurl = fullurl.replace("http", "https")
                resp = requests.post(fullurl,
                                     data=data,
                                     files=f,
                                     headers=self.headers
                                     )
                if resp.status_code != 200:
                    msg = json.loads(resp.content.decode("utf-8"))["error"]["message"]
                    return {"status": resp.status_code, "message": msg}
                details = json.loads(resp.content.decode("utf-8"))
                self._update_and_complete_submission(details, sub_id)
            elif resp.status_code == 409:
                fullurl = self.host["url"] + "package_show"
                resp = requests.post(fullurl, data={"id": dataset_id})
                #  now iterate through resources to get matching name
                resources = json.dumps(resp.content.decode("utf-8"))["result"]["resources"]
                fullurl = self.host["url"] + "resource_update"
                # Submission().mark_submission_complete(ObjectId(sub_id))
            else:
                return json.dumps({"status": resp.status_code, "message": resp.reason + " - " + resp.text})

        Submission().mark_submission_complete(ObjectId(sub_id))
        return True

    def _update_and_complete_submission(self, details, sub_id):
        if details["success"] == False:
            return False
        Submission(ObjectId(sub_id)).insert_ckan_accession(sub_id, details)

        return True

    def _get_all_datasets(self):
        fullurl = self.host['url'] + "package_list?"
        resp = requests.get(fullurl)
        if resp.status_code == 200:
            return resp.content.decode('utf-8')
        else:
            return json.dumps({"status": resp.status_code, "message": "error getting datasets"})

    def _create_ckan_metadata(self, s):
        # get file

        out = dict()
        out["name"] = str(uuid.uuid4())
        out["state"] = "active"
        out["tags"] = []
        out["private"] = False
        out["author_email"] = "felix.shaw@tgac.ac.uk"
        out["maintainer_email"] = "felix.shaw@tgac.ac.uk"
        out["url"] = "http://copo-project.org" + '/copo/resolve:' + str(s["_id"])

        extras = list()

        for item in s["meta"]["fields"]:
            if item["dc"] == "dc.type":
                out["type"] = item["vals"]
            elif item["dc"] == "dc.title":
                out["title"] = item["vals"][0]

            elif item["dc"] == "dc.description":
                out["notes"] = item["vals"]
            elif item["dc"] == "dc.subject":
                # subject can be a list so handle this
                if type(item["vals"]) == type(list()):
                    for idx, el in enumerate(item["vals"]):
                        extras.append({"key": "subject_" + str(idx + 1), "value": el})
                else:
                    extras.append({"key": "subject", "value": el})
            elif item["dc"] == "dc.creator":

                for idx, author in enumerate(item["vals"]):
                    if idx == 0:
                        out["author"] = author
                        out["maintainer"] = author
                    else:
                        extras.append({"key": "additional_author_" + str(idx + 1), "value": author})
                        extras.append({"key": "additional_maintainer_" + str(idx + 1), "value": author})

            elif item["dc"] == "dc.publisher":

                for idx, pub in enumerate(item["vals"]):
                    if idx == 0:
                        out["publisher"] = pub
                    else:
                        extras.append({"key": "additional_publisher_" + str(idx + 1), "value": pub})

            elif item["dc"] == "dc.language":
                pass
            else:
                extras.append({"key": item["copo_id"], "value": item["vals"]})
        out["extras"] = extras
        # out["extras"] = []

        '''
        for key in out:
            # ckan throws a wobbly if there is punctuation in field values, so remove
            if type(out[key]) == type(""):
                out[key] = out[key].translate(str.maketrans("", "", string.punctuation))
                out[key] = out[key].lower()
        '''
        return out

    def dc_dict_to_dc(self, sub_id):
        # get file metadata, call converter to strip out dc fields
        s = Submission().get_record(ObjectId(sub_id))
        f_id = s["bundle"][0]
        items = CgCoreSchemas().extract_repo_fields(str(f_id), "ckan")
        temp_id = "copo:" + str(sub_id)
        # add the submission_id to the dataverse metadata to allow backwards treversal from dataverse
        items.append({"dc": "relation", "copo_id": "relation", "vals": temp_id})
        Submission().update_meta(sub_id, json.dumps(items))
