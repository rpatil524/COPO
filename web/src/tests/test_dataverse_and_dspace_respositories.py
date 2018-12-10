# Created by fshaw at 05/11/2018
from django.test import TestCase, RequestFactory
import os, json
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import datetime
from dal.copo_da import Profile, DataFile, Repository, Submission
from django.conf import settings
from submission.submissionDelegator import delegate_submission
from django.http import request
import requests


class TestDataverse(TestCase):
    "Basic tests"

    @classmethod
    def setUpClass(cls):
        cls.factory = RequestFactory()
        settings.UNIT_TESTING = True

        # create user
        cls.user = User.objects.create_user(username='jonny', first_name="jonny", last_name="appleseed",
                                            email='jonny@appleseed.com', password='jonnyappleseed')
        cls.user.save()

        # create profile
        p_dict = {"copo_id": "000000000", "description": "Test Description", "user_id": cls.user.id, "title": "Test Title"}
        cls.pid = Profile().save_record(dict(), **p_dict)

        # create datafile
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_datafile.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["file_location"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "fish.png")
        p_dict["name"] = "fish.png"
        profile = Profile().get_collection_handle().find_one({"copo_id": "000000000"})
        p_dict["profile_id"] = str(cls.pid["_id"])
        cls.d = DataFile().get_collection_handle().insert(p_dict)

        # create dataverse repository
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_dataverse_repo.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        cls.r = Repository().save_record(dict(), **p_dict)

        # create submission record for dataverse
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_dataverse_submission.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["bundle_meta"][0]["file_path"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures",
                                                             "fish.png")
        p_dict["bundle_meta"][0]["file_id"] = str(cls.d)
        p_dict["profile_id"] = str(cls.pid["_id"])
        p_dict["bundle"].append(str(cls.d))
        cls.s_dv = Submission().get_collection_handle().insert(p_dict)

        # create submission record for new dspace
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_dspace_submission.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["bundle_meta"][0]["file_path"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures",
                                                             "fish.png")
        p_dict["bundle_meta"][0]["file_id"] = str(cls.d)
        p_dict["profile_id"] = str(cls.pid["_id"])
        p_dict["bundle"].append(str(cls.d))
        p_dict["meta"]["new_or_existing"] = "new"
        # query for item id
        resp = requests.post("http://demo.dspace.org/rest/collections")
        collections = json.loads(resp.content.decode("utf-8"))
        collection = collections[0]
        p_dict["meta"]["identifier"] = collection["uuid"]
        cls.s_ds_new = Submission().get_collection_handle().insert(p_dict)

        # create submission record for existing dspace
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_dspace_submission.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["bundle_meta"][0]["file_path"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures",
                                                             "fish.png")
        p_dict["bundle_meta"][0]["file_id"] = str(cls.d)
        p_dict["profile_id"] = str(cls.pid["_id"])
        p_dict["bundle"].append(str(cls.d))
        p_dict["meta"]["new_or_existing"] = "existing"
        # query for item id
        resp = requests.post("http://demo.dspace.org/rest/items")
        items = json.loads(resp.content.decode("utf-8"))
        item = items[0]
        p_dict["meta"]["identifier"] = item["uuid"]
        p_dict["item_id"] = item["uuid"]
        cls.s_ds_existing = Submission().get_collection_handle().insert(p_dict)
        cls.ckan_api = "http://demo.ckan.org/api/3/action/"

    def test_get_user(self):
        u = self.user
        self.assertNotEqual(u, None, "User not found")
        u1 = authenticate(username='jonny', password='jonnyappleseed')
        self.assertIsInstance(u1, User, "error authenticating user")

    def test_get_profile(self):
        p = Profile().get_record(self.pid["_id"])
        self.assertEquals(p["description"], "Test Description", "Error creating profile")

    def test_get_datafile(self):
        df = DataFile().get_record(self.d)
        self.assertEquals(df["name"], "fish.png")

    def test_get_repository(self):
        r = Repository().get_record(self.r["_id"])
        self.assertEquals(r["url"], "https://demo.dataverse.org", "Error retrieving repository")

    def test_get_submission(self):
        s = Submission().get_record(self.s_dv)
        self.assertEquals(s["repository"], "dataverse", "Error retrieving subission record")

    def test_dataverse_submission(self):
        s = Submission().get_record(self.s_dv)
        request = self.client.post(path='/rest/submit_to_repo/', data={"sub_id": s["_id"]})
        self.assertEqual(request.status_code, 200, "error submitting to dataverse")
        s = Submission().get_record(self.s_dv)
        self.assertTrue("accessions" in s, "accessions not in submission")
        self.assertTrue(s["accessions"]["dataset_doi"].startswith("doi"), "doi not present in submission")
        self.assertTrue(s["accessions"]["dataset_edit_uri"].startswith("http"), "edit uri not present in submission")

    def test_dspace_new_submission(self):
        request = self.client.post(path='/rest/submit_to_repo/', data={"sub_id": self.s_ds_new})
        self.assertEqual(request.status_code, 200)
        s = Submission().get_record(self.s_ds_new)
        self.assertTrue(s["accessions"][0]["dspace_instance"].startswith("http"))
        self.assertTrue("uuid" in s["accessions"][0])
        self.assertTrue(s["accessions"][0]["retrieveLink"].startswith("/rest/bitstreams/"))

    def test_dspace_existing_submission(self):
        request = self.client.post(path='/rest/submit_to_repo/', data={"sub_id": self.s_ds_existing})
        self.assertEqual(request.status_code, 200)
        s = Submission().get_record(self.s_ds_existing)
        self.assertTrue(s["accessions"][0]["dspace_instance"].startswith("http"))
        self.assertTrue("uuid" in s["accessions"][0])
        self.assertTrue(s["accessions"][0]["retrieveLink"].startswith("/rest/bitstreams/"))

    @classmethod
    def tearDownClass(cls):
        u = User.objects.get(pk=1)
        u.delete()
        Profile().get_collection_handle().remove({"copo_id": "000000000"})
        DataFile().get_collection_handle().remove({"test_file": True})
        Repository().get_collection_handle().remove({"_id": cls.r["_id"]})
        Submission().get_collection_handle().remove({"_id": cls.s_dv})
        Submission().get_collection_handle().remove({"_id": cls.s_ds_new})
        Submission().get_collection_handle().remove({"_id": cls.s_ds_existing})
