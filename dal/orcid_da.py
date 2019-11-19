__author__ = 'felix.shaw@tgac.ac.uk - 24/06/15'

import json

from allauth.socialaccount.models import SocialAccount
from dal.base_resource import Resource
from dal.mongo_util import get_collection_ref

ORCID = get_collection_ref("OrcidCollections")


class Orcid(Resource):

    def store_orcid_profile(self, profile_data, user):


        social_account = SocialAccount.objects.get(user_id=user)
        profile_data = social_account.extra_data
        profile_data = json.dumps(profile_data).replace('-', '_')

        orcid_dict = {'user': user, 'op': json.loads(profile_data)}

        ORCID.update({'user': user},
                     orcid_dict,
                     True)


    def get_orcid_profile(self, user):

        u_id = user.id
        orc = ORCID.find_one({'user': u_id})
        if(orc is not None):
            return orc
        else:
            return ''

    def get_current_affliation(self, user):
        orc = self.get_orcid_profile(user)
        if orc:
            name = 'unknown'
            for a in orc['op']['orcid_profile']['orcid_activities']['affiliations']['affiliation']:
                if a['end_date'] is None:
                    return a['organization']['name']
            return name