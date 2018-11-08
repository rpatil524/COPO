# Created by fshaw at 05/11/2018
from django.test import TestCase
import os, json
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import datetime
from dal.copo_da import Profile, DataFile
from django.conf import settings


class TestDataverse(TestCase):
    "Basic tests"

    @classmethod
    def setUpClass(cls):
        settings.UNIT_TESTING = True
        # create user
        user = User.objects.create_user(username='jonny', first_name="jonny", last_name="appleseed", email='jonny@appleseed.com', password='jonnyappleseed')
        user.save()
        # create profile
        p_dict = {"copo_id": "000000000", "description": "Test Description", "user_id": 1, "title": "Test Title"}
        cls.pid = Profile().save_record(dict(), **p_dict)
        # create datafile
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_datafile.json")
        with open(p) as f:
            f_raw = f.read()
        p_dict = json.loads(f_raw)
        p_dict["file_location"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "fish.png")
        p_dict["name"] = "fish.png"
        profile = Profile().get_collection_handle().find_one({"copo_id": "000000000"})
        p_dict["profile_id"] = str(cls.pid["_id"])
        cls.d = DataFile().get_collection_handle().insert(p_dict)


    def test_get_user(self):
        u = User.objects.get(username="jonny")
        self.assertNotEqual(u, None, "User not found")
        u1 = authenticate(username='jonny', password='jonnyappleseed')
        self.assertIsInstance(u1, User, "error authenticating user")

    def test_get_profile(self):
        p = Profile().get_record(self.pid["_id"])
        self.assertEquals(p["description"], "Test Description", "Error creating profile")

    def test_create_datafile(self):
        df = DataFile().get_record(self.d)
        self.assertEquals(df["name"], "fish.png")


    @classmethod
    def tearDownClass(cls):
        u = User.objects.get(pk=1)
        u.delete()
        Profile().get_collection_handle().remove({"copo_id": "000000000"})
        DataFile().get_collection_handle().remove({"test_file": True})