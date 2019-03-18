# Created by fshaw at 17/12/2018
from django.test import TestCase
from dal.copo_da import Submission, Profile, DataFile
from submission.dataverseSubmission import DataverseSubmit
from submission.submissionDelegator import delegate_submission
from django.conf import settings
from django.contrib.auth.models import User
import os, json
from web.apps.web_copo.schemas.utils.cg_core.cg_schema_generator import CgCoreSchemas


class CGCoreTests(TestCase):

    @classmethod
    def setUpClass(cls):
        settings.UNIT_TESTING = True
        # create user
        cls.user = User.objects.create_user(username='jonny', first_name="jonny", last_name="appleseed",
                                            email='jonny@appleseed.com', password='jonnyappleseed')
        cls.user.save()

        # create profile
        p_dict = {"copo_id": "000000000", "description": "Test Description", "user_id": 1, "title": "Test Title"}
        cls.pid = Profile().save_record(dict(), **p_dict)

        # create datafile
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "dummy_datafile_cgcore.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["file_location"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures", "fish.png")
        p_dict["name"] = "fish.png"
        profile = Profile().get_collection_handle().find_one({"copo_id": "000000000"})
        p_dict["profile_id"] = str(cls.pid["_id"])
        cls.d = DataFile().get_collection_handle().insert(p_dict)

        # create submission
        p = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures",
                         "dummy_cgcore_dataverse_submission_existing.json")
        with open(p) as f:
            p_dict = json.loads(f.read())
        p_dict["bundle_meta"][0]["file_path"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures",
                                                             "fish.png")
        p_dict["bundle_meta"][0]["file_id"] = str(cls.d)
        p_dict["profile_id"] = str(cls.pid["_id"])
        p_dict["bundle"].append(str(cls.d))
        cls.s_dv = Submission().get_collection_handle().insert(p_dict)

    def test_cgcore_to_dccore_conversion(self):
        df = DataFile().get_record(self.d)
        self.assertIsNotNone(df)
        tt = CgCoreSchemas().extract_dublin_core(str(self.d))
        self.assertIsInstance(tt, type([]))
        self.assertNotEqual(len(tt), 0)

    def test_cg_core_to_dataverse_conversion(self):
        # the method below will extract dc fields and add them to the meta field of the supplied sub id
        DataverseSubmit(submission_id=self.s_dv).dc_dict_to_dc()
        s = Submission().get_record(self.s_dv)
        self.assertGreater(len(s["meta"]), 0)
        self.assertTrue("dsTitle" in s["meta"])

    def test_submit_existing_cgcore_dataverse(self):
        # method will test the submission of a copo cgcore record to an existing dataset within a dataverse
        s = Submission().get_record(self.s_dv)
        request = self.client.post(path='/rest/submit_to_repo/', data={"sub_id": s["_id"]})
        s = Submission().get_record(self.s_dv)
        self.assertTrue("result" in s["accessions"][0])
        self.assertTrue("id" in s["accessions"][0]["result"])



    @classmethod
    def tearDownClass(cls):
        u = User.objects.get(pk=1)
        u.delete()
        Profile().get_collection_handle().remove({"copo_id": "000000000"})
        DataFile().get_collection_handle().remove({"_id": cls.d})
        Submission().get_collection_handle().remove({"_id": cls.s_dv})
