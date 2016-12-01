from django.conf import settings
from allauth.socialaccount.models import SocialAccount
from dal import Orcid

class OrcidOAuth(object):
    '''
    Class for Orcid related housekeeping
    '''
    def process_request(self, request):
        '''
        Once per session check to see if Orcid details have been updated recently
        Args:
            request: Django HttpRequest object

        Returns: None

        '''
        if not request.session.get('orcid_details_stored'):
            url = request.get_full_path()
            if url.startswith('/copo', 0, 5):
                user = request.user.id
                if user is not None:
                    try:
                        sa = SocialAccount.objects.get(user_id=user)
                        extra_data = sa.extra_data
                        Orcid().store_orcid_profile(extra_data, user)
                        request.session['orcid_details_stored'] = True
                    except:
                        pass


