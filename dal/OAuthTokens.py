__author__ = 'felix.shaw@tgac.ac.uk - 29/01/2016'

from dal.mongo_util import get_collection_ref
import datetime
import requests
from web.apps.web_copo.schemas.utils import data_utils
import json

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
        return self.OAuthToken.insert(
            {'service': 'cyverse', 'user': user, 'token': token, 'issued': datetime.datetime.now()})

    def cyverse_update_token(self, old_token, new_token):
        return self.OAuthToken.replace_one({'_id': old_token['_id']},
                                           {'service': 'cyverse', 'user': data_utils.get_user().user,
                                            'token': new_token,
                                            'issued': datetime.datetime.now()})

    def check_token(self, token):
        now = datetime.datetime.now()
        then = token['issued']
        # cyverse tokens expire 4 hours after issue, so check if refresh is needed
        delta = now - then
        max_delta = datetime.timedelta(seconds=14350)
        if delta > max_delta:
            post_data = {'grant_type': 'refresh_token', 'refresh_token': token['token']['refresh_token'],
                         'scope': 'PRODUCTION'}
            resp = requests.post("https://agave.iplantc.org/oauth2/token", data=post_data, auth=('KOm9gFBPVwq6sfCMgumZRJG5j8wa', 'gAnX96MinyBfZ_gsvkr0nEDLpR8a'))
            if resp.status_code == 200:
                new_token = json.loads(resp.content.decode('utf-8'))
                update_status = self.cyverse_update_token(token, new_token)
                if update_status['acknowledged'] == True:
                    return new_token
        else:
            return token
