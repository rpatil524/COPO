# Created by fshaw at 20/11/2018
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
from web.apps.web_copo.utils import ajax_handlers


class TestCKAN(TestCase):
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
        p_dict = {"copo_id": "000000000", "description": "Test Description", "user_id": 1, "title": "Test Title"}
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

        # create submission record for existing ckan
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_ckan_submission.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["bundle_meta"][0]["file_path"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures",
                                                             "fish.png")
        p_dict["bundle_meta"][0]["file_id"] = str(cls.d)
        p_dict["profile_id"] = str(cls.pid["_id"])
        p_dict["bundle"].append(str(cls.d))
        p_dict["meta"]["new_or_existing"] = "existing"
        cls.s_ckan_existing = Submission().get_collection_handle().insert(p_dict)

        # create submission record for new ckan
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_ckan_submission.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["bundle_meta"][0]["file_path"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures",
                                                             "fish.png")
        p_dict["bundle_meta"][0]["file_id"] = str(cls.d)
        p_dict["profile_id"] = str(cls.pid["_id"])
        p_dict["bundle"].append(str(cls.d))
        p_dict["meta"]["new_or_existing"] = "new"
        p_dict.pop("item_id")
        cls.s_ckan_new = Submission().get_collection_handle().insert(p_dict)

    def test_get_ckan_datasets(self):
        resp = self.client.get(path='/copo/get_ckan_items/', data={"submission_id": self.s_ckan_existing})
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.content.decode("utf-8"))
        self.assertIs(type(resp["result"]), type(list()))

    def test_dspace_existing_submission(self):
        # pass to submit method
        s = Submission().get_record(self.s_ckan_new)
        request = self.client.post(path='/rest/submit_to_repo/', data={"sub_id": s["_id"]})

    def test_dspace_new_submission(self):
        pass

    @classmethod
    def tearDownClass(cls):
        u = User.objects.get(pk=1)
        u.delete()
        Profile().get_collection_handle().remove({"copo_id": "000000000"})
        DataFile().get_collection_handle().remove({"test_file": True})
        # Submission().get_collection_handle().remove({"_id": cls.s_dv})
        Submission().get_collection_handle().remove({"_id": cls.s_ckan_new})
        Submission().get_collection_handle().remove({"_id": cls.s_ckan_existing})
