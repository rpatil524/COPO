from django.test import TestCase
from .test_utilities import test_database_utils
from django.conf import settings
from dal.copo_da import Profile
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.test import Client
from django_tools.middlewares import ThreadLocal

import os


class Ena_Tests(TestCase):
    db_name = settings.MONGO_TEST_DB_NAME

    webpage = Client()

    # temp_user="temporary"
    # temp_password="temporary"
    # temp_email="temporary@gmail.com"

    def setUp(self):
        self.db_utils = test_database_utils.Utils(self.db_name)
        self.db_utils.load_fixtures('web/src/tests/test_data/ena_test_data.json')
        # this setting should redirect all dal activity to the test db
        settings.MONGO_CLIENT = self.client
        #  may need to login here

    def test_ena_submission(self):
        print('testing')

    def tearDown(self):
        self.db_utils.client.drop_database(self.db_name)
        self.db_utils.client.close()
