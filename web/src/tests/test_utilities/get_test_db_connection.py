# Created by fshaw at 05/02/2018
from django.conf import settings
from pymongo import MongoClient
import json


def get_client():
    #GetDB - simple function to wrap getting a database
    #connection from the connection pool.

    client = MongoClient(host=settings.MONGO_HOST,
                         port=settings.MONGO_PORT,
                         maxIdleTimeMS=1000 * 60)
    return client


def load_fixtures(file_location):
    # load test data from json file
    with open(file_location) as json_data:
        d = json.load(json_data)
        return d