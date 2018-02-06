from django.test import TestCase
from .test_utilities.get_test_db_connection import get_client
from django.conf import settings
from dal.copo_da import Profile

class Ena_Tests(TestCase):

    db_name = settings.MONGO_TEST_DB_NAME

    def setUp(self):
        self.client = get_client()
        self.db = self.client[self.db_name]
        settings.MONGO_CLIENT = self.client

    def test_can(self):
        self.db.test.insert_one({'str': "str123"})


    def tearDown(self):
        self.client.drop_database(self.db_name)
        self.client.close()