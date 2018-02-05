from django.test import TestCase
from .test_utilities.get_test_db_connection import get_db
from django.conf import settings
from dal.copo_da import Profile

class Ena_Tests(TestCase):

    def setUp(self):
        self.db =get_db("BLAHBLAH")
        #settings.MONGO_CLIENT = self.db

    def test_can(self):
        self.db.insert({'a': 1})
        p_list = Profile().get_all_records()
        self.assertGreater(len(p_list), 0)

    def tearDown(self):
        print("Finishing")