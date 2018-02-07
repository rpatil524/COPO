# Created by fshaw at 05/02/2018
from django.conf import settings
from pymongo import MongoClient
import json


class Utils:

    def __init__(self, db_name, host=settings.MONGO_HOST, port=settings.MONGO_PORT):
        # GetDB - simple function to wrap getting a database
        # connection from the connection pool.
        self.client = MongoClient(host=host,
                                  port=port,
                                  maxIdleTimeMS=1000 * 60)
        self.db = self.client[db_name]

    def get_pymongo_client(self):
        return self.client

    def get_pymongo_db(self):
        return self.db

    def load_fixtures(self, file_location):
        # load test data from json file
        with open(file_location) as json_data:
            d = json.load(json_data)
            self.db.Profiles.insert_one(d['profile'])
            self.db.SourceCollection.insert_many(d['source'])
            self.db.SampleCollection.insert_many(d['sample'])
