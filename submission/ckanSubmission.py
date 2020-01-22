# Created by fshaw at 21/11/2018
import os, re, string, json, uuid
import requests
from dal.copo_da import Submission
from dal.copo_da import DataFile
import datetime
from bson import ObjectId
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas
from urllib.parse import urljoin
from web.apps.web_copo.schemas.utils.data_utils import get_base_url
from urllib.parse import urljoin
from urllib import parse
import unicodedata
from django.conf import Settings
from django_tools.middlewares import ThreadLocal


class CkanSubmit:
    host = None
    headers = None
    url = None

    def __init__(self, sub_id=None):
        if sub_id:
            self.host = Submission().get_dataverse_details(sub_id)
            self.headers = {'X-CKAN-API-Key': self.host['apikey']}
            self.hostname = self.host["url"]
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
                print(resp.reason)
                fullurl = self.host["url"] + "package_show"
                resp = requests.post(fullurl, json={"name_or_id": data["name"]})
                data = json.loads(resp.content.decode("utf-8"))
                dataset_id = data["result"]["id"]
                data = {
                    "package_id": dataset_id
                }
                fullurl = self.host["url"] + "resource_create"
            else:
                return json.dumps({"status": resp.status_code, "message": resp.reason + " - " + resp.text})
        else:
            data = {"package_id": s["meta"]["identifier"]}

        # now we have a dataset id to which to add the datafile
        for f in s["bundle"]:

            # data = dict()
            df = DataFile().get_record(ObjectId(f))
            # upload file

            # get correct bitstream file extension lookup
            try:
                filename, file_extension = os.path.splitext(df["name"])
                if "." in file_extension:
                    file_extension = file_extension.replace(".", "")
                ext = self.get_media_type_from_file_ext(file_extension)
            except:
                ext = ""
            now = str(datetime.date.today())
            print(df["name"])
            data["name"] = df["name"]
            data["created"] = now
            data["mimetype"] = ext

            fullurl = self.host["url"] + "resource_create"
            url = parse.urlparse(self.host["url"])

            #data["url"] = urljoin(self.hostname, "dataset/" + str(uuid.uuid4()))

            with open(df["file_location"], 'rb') as f:
                files = [
                    ('upload', (df["name"], f, ext))
                ]
                # data["upload"] = files
                try:
                    print(self.headers)

                    resp = requests.post(fullurl,
                                         data=data,
                                         files=files,
                                         headers=self.headers
                                         )
                    # print(resp.json()['headers'])
                except (TypeError, ValueError) as e:
                    print(e)
                    # for some reason this fails the first time
                    resp = requests.post(fullurl,
                                         data=data,
                                         files=files,
                                         headers=self.headers
                                         )
                except TypeError as t:
                    print(t)
                if resp.status_code == 200:
                    req = ThreadLocal.get_current_request()
                    details = json.loads(resp.content.decode("utf-8"))
                    details["result"]["repo_url"] = self.host["url"]
                    #details["result"]["url"] = req.build_absolute_uri("/") + "rest/get_accession_data?sub_id=" + sub_id
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
                    details["result"]["repo_url"] = self.host["url"]
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
        out["name"] = str(uuid.uuid4()).encode('ascii', 'replace')
        #out["name"] = "jfklsdjfklsdjfksldjfk"
        out["state"] = "active"
        out["tags"] = []
        out["private"] = False

        out["author_email"] = "felix.shaw@tgac.ac.uk"
        out["maintainer_email"] = "felix.shaw@tgac.ac.uk"

        url = get_base_url()
        out["url"] = urljoin(url, 'copo/resolve/' + str(s["_id"]))

        extras = list()

        for item in s["meta"]["fields"]:
            if item["dc"] == "dc.type":
                out["type"] = "dataset"
                print("setting type to 'dataset' due to ckan nomenclature")
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
            elif item["dc"] == "dc.relation":
                # add the submission_id to the dataverse metadata to allow backwards treversal from dataverse
                url = get_base_url()
                temp_id = urljoin(url, 'copo/resolve/' + str(s["_id"]))
                extras.append({"key": "relation", "value": temp_id})
            elif item["dc"] == "notes":
                # pass this as it will lead to a multiple key error
                pass
            else:
                if type(item["vals"]) == type(""):
                    extras.append({"key": item["copo_id"], "value": item["vals"]})
                elif type(item["vals"]) == type([]):
                    for idx, val in enumerate(item["vals"]):
                        if type(val) == type(""):
                            extras.append({"key": item["dc"] + "_" + str(idx + 1), "value": val})
                        else:
                            extras.append({"key": item["dc"] + "_" + str(idx + 1), "value": val[idx]})
        out["extras"] = extras

        return out

    def dc_dict_to_dc(self, sub_id):
        # get file metadata, call converter to strip out dc fields
        s = Submission().get_record(ObjectId(sub_id))
        f_id = s["bundle"][0]
        items = CgCoreSchemas().extract_repo_fields(str(f_id), "ckan")

        Submission().update_meta(sub_id, json.dumps(items))

    def get_media_type_from_file_ext(self, ext):
        if ext == "pdf":
            return "application/pdf"
        elif ext == "ai" or ext == "eps" or ext == "ps":
            return "application/postscript"
        elif ext == "xls" or ext == "xlsx":
            return "application/vnd.ms-excel"
        elif ext == "ppt":
            return "application/vnd.ms-powerpoint"
        elif ext == "gif":
            return "image/gif"
        elif ext == "jpg" or ext == "jpeg":
            return "image/jpeg"
        elif ext == "png":
            return "image/png"
        elif ext == "tif" or ext == "tiff":
            return "image/tiff"
        elif ext == "bmp":
            return "image/x-ms-bmp"
        elif ext == "html" or ext == "htm":
            return "text/html"
        elif ext == "asc" or ext == "txt":
            return "text/plain"
        elif ext == "xml":
            return "text/xml"
        elif ext == "doc" or ext == "docx":
            return "application/msword"
        else:
            return ""

    def get_submitted_package_details(self, package_id):
        fullurl = urljoin(self.host["url"], "package_show?id=" + package_id)
        resp = requests.get(fullurl)
        return resp.content.decode('utf-8')