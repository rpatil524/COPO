__author__ = 'felix.shaw@tgac.ac.uk - 29/01/2016'

from dal.mongo_util import get_collection_ref

OAuthCollectionName = 'OAuthToken'


class OAuthToken:
    def __init__(self):
        self.OAuthToken = get_collection_ref('OAuthToken')

    def get_figshare_by_user(self, user):
        doc = self.OAuthToken.find_one({'service': 'figshare', 'user': user})
        if doc:
            return doc
        else:
            return False

    def cyverse_get_token(self, user):
        doc = self.OAuthToken.find_one({'service': 'cyverse', 'user': user})
        if doc:
            return doc
        else:
            return False

    def cyverse_save_token(self, user, token):
        return self.OAuthToken.insert({'service': 'cyverse', 'user': user, 'token': token})

