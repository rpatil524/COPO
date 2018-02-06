from django.test import TestCase
from .test_utilities.get_test_db_connection import get_client, load_fixtures
from django.conf import settings
from dal.copo_da import Profile
import os

class Ena_Tests(TestCase):

    db_name = settings.MONGO_TEST_DB_NAME
    d = os.getcwd()
    fix = load_fixtures('web/src/tests/test_data/ena_test_data.json')

    def setUp(self):
        self.client = get_client()
        self.db = self.client[self.db_name]
        # this setting should redirect all dal activity to the test db
        settings.MONGO_CLIENT = self.client

    def test_can(self):
        Profile().save_record(self.fix['profile'])


    def tearDown(self):
        self.client.drop_database(self.db_name)
        self.client.close()