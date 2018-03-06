from django.conf import settings
from allauth.socialaccount.models import SocialAccount
from dal import Orcid


class OrcidOAuth:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

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


        # response = self.get_response(request)
        #
        # # Code to be executed for each request/response after
        # # the view is called.
        #
        # return response





# class OrcidOAuth(object):
#     '''
#     Class for Orcid related housekeeping
#     '''
#     def process_request(self, request):
#         '''
#         Once per session check to see if Orcid details have been updated recently
#         Args:
#             request: Django HttpRequest object
#
#         Returns: None
#
#         '''
#         if not request.session.get('orcid_details_stored'):
#             url = request.get_full_path()
#             if url.startswith('/copo', 0, 5):
#                 user = request.user.id
#                 if user is not None:
#                     try:
#                         sa = SocialAccount.objects.get(user_id=user)
#                         extra_data = sa.extra_data
#                         Orcid().store_orcid_profile(extra_data, user)
#                         request.session['orcid_details_stored'] = True
#                     except:
#                         pass


