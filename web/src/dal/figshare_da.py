__author__ = 'felix.shaw@tgac.ac.uk - 24/02/2016'
from dal.mongo_util import get_collection_ref
from dal.mongo_util import cursor_to_list
from bson import ObjectId
import requests


FigshareSubmissionName = 'FigshareCollection'
PartialSubmissionName = 'PartialSubmissionsCollection'
FigshareTokenCollection = 'FigshareOauthTokenCollection'


class Figshare:
    def __init__(self, profile_id=None):
        self.FigshareSubmission = get_collection_ref(FigshareSubmissionName)
        self.PartialSubmission = get_collection_ref(PartialSubmissionName)
        self.FigshareTokens = get_collection_ref(FigshareTokenCollection)



    def create_partial_submission(self, file_ids=None, user_id=None, url=None):
        """
        This method will be called when a Figshare submission was exited part way through e.g. to autheticate via OAUTH
        :return: True if the partial submission was created
        """
        return self.PartialSubmission.insert(
            {'file_id': file_ids, 'user_id': user_id, 'url': url, 'token_obtained': False, 'file_submitted': False})



    def get_partial_submissions_for_user(self, user_id):
        """
        Method to obtain partial submission by given user_id
        :param user_id:
        :return: dictionary containing the last submission
        """
        return cursor_to_list(self.PartialSubmission.find({'user_id': user_id}))



    def get_token_for_user(self, user_id):
        return self.FigshareTokens.find_one({'user': user_id})



    def delete_tokens_for_user(self, user_id):
        return self.FigshareTokens.delete_many({'user': user_id})



    def put_token_for_user(self, user_id, token):
        return self.FigshareTokens.update(
            {
                'user': user_id
            },
            {
                '$set': {
                    'token': token
                }
            },
            upsert=True)



    def token_obtained_for_partial_submission(self, id):
        self.PartialSubmission.update_one(
            {"_id": id},
            {
                "$set": {
                    "token_obtained": True
                }
            }
        )
