# Created by fshaw at 05/02/2018
from django.conf import settings
from pymongo import MongoClient


def get_db(db_name=None):
    """ GetDB - simple function to wrap getting a database
    connection from the connection pool.
    """
    return MongoClient(
        host=settings.MONGO_HOST,
        port=settings.MONGO_PORT,
        maxIdleTimeMS=1000 * 60)
    (db_name or [settings.MONGO_TEST_DB_NAME])
