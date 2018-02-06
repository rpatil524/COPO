# Created by fshaw at 05/02/2018
from django.conf import settings
from pymongo import MongoClient


def get_client():
    """ GetDB - simple function to wrap getting a database
    connection from the connection pool.
    """
    client = MongoClient(host=settings.MONGO_HOST,
                         port=settings.MONGO_PORT,
                         maxIdleTimeMS=1000 * 60)
    return client


