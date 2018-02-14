from django.test import TestCase
from .test_utilities import test_database_utils
from django.conf import settings
from dal.copo_da import Profile, Submission, DataFile, Sample, Source
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.test import Client
from django_tools.middlewares import ThreadLocal
from submission.enaSubmission import EnaSubmit
from bson import ObjectId

import os


class Ena_Tests(TestCase):
    webpage = Client()
    sub_id = None
    user = None
    db_json = None

    def setUp(self):
        self.db_utils = test_database_utils.Utils()
        # this method returns the submission_id of the submission record added
        self.sub_id, self.profile_id = self.db_utils.load_ena_fixtures('web/src/tests/test_data/ena_test_data.json')
        # this setting should redirect all dal activity to the test db
        settings.UNIT_TESTING = True
        settings.TEST_USER = User.objects.create_user('test_user')

    def test_db_recall(self):
        p = Profile().get_all_records()
        self.assertEqual(1, len(p), "Profile Recall Failed")

    def test_df_recall(self):
        dfs = DataFile().get_for_profile(self.profile_id)
        self.assertEqual(2, dfs.count(), "Datafile Recall Failed")

    def test_db_update(self):
        p_list = Profile().get_all_records()
        p = p_list[0]
        title = 'updated_test'
        description = 'updated_description'
        copo_id = 123456789
        p['title'] = title
        p['description'] = description
        p['copo_id'] = copo_id
        p['target_id'] = str(p['_id'])
        Profile().save_record(dict(), **p)
        p_updated = Profile().get_record(p['_id'])
        p.pop('target_id')
        self.assertEqual(p, p_updated, "Profile Update Failed")

    def test_ena_submission(self):
        s = Submission().get_record(self.sub_id)
        EnaSubmit().submit(self.sub_id, s['bundle'])

        # TODO - change from paired to non-paired in test data

        self.assertEqual(1, 1)
    def tearDown(self):
        self.db_utils.db.client.drop_database(settings.MONGO_DB_TEST)
        self.db_utils.db.client.close()
