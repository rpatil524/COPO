__author__ = 'felix.shaw@tgac.ac.uk - 29/04/2016'
from django.conf import settings
from dal.figshare_da import Figshare
from web.apps.web_copo.lookup.lookup import FIGSHARE_API_URLS
import requests
from dal.copo_da import Submission
from web.apps.web_copo.schemas.utils import data_utils
import ast
import web.apps.web_copo.lookup.lookup as lkup

FIGSHARE_CREDENTIALS = settings.FIGSHARE_CREDENTIALS
figshare = lkup.VOCAB['REPO_NAMES']['figshare']['value']


class SetFigshareOauth:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        url = request.get_full_path()
        if url.startswith('/copo', 0, 5):

            doc = Submission().get_incomplete_submissions_for_user(request.user.id, figshare)
            data_dict = dict()
            token = None

            if doc.count() > 0:

                if 'code' in request.GET and 'state' in request.GET:

                    token_obtained = True

                    for d in doc:
                        if d.get('token_obtained') == 'false':
                            token_obtained = False
                            break

                    if not token_obtained:

                        # get new token from Figshare
                        code = request.GET.get('code')
                        client_id = FIGSHARE_CREDENTIALS['client_id']
                        token_url = FIGSHARE_API_URLS['authorization_token']

                        # now get token
                        data = {
                            'client_id': client_id,
                            'code': code,
                            'client_secret': FIGSHARE_CREDENTIALS['client_secret'],
                            'grant_type': 'authorization_code',
                            'scope': 'all'
                        }
                        try:
                            r = requests.post(token_url, data)
                            data_dict = ast.literal_eval(r.content.decode('utf-8'))
                            token = data_dict['token']
                            t = Figshare().put_token_for_user(user_id=data_utils.get_current_user().id, token=token)
                            if t:
                                # mark fighshare submissions for this user as token obtained
                                Submission().mark_all_token_obtained(user_id=request.user.id)

                                # if all is well, the access token will be stored in FigshareSubmussionCollection
                        except Exception as e:
                            print(e)

                    else:
                        # retrieve token
                        token = Figshare().get_token_for_user(user_id=data_utils.get_current_user().id)

                        # request.session['partial_submissions'] = doc
            else:
                request.session['partial_submissions'] = None

        # response = self.get_response(request)
        #
        # # Code to be executed for each request/response after
        # # the view is called.
        #
        # return response

# class SetFigshareOauth(object):
#     def process_request(self, request):
#         url = request.get_full_path()
#         if url.startswith('/copo', 0, 5):
#
#             doc = Submission().get_incomplete_submissions_for_user(request.user.id, figshare)
#             data_dict = dict()
#             token = None
#
#             if doc.count() > 0:
#
#                 if 'code' in request.GET and 'state' in request.GET:
#
#                     token_obtained = True
#
#                     for d in doc:
#                         if d.get('token_obtained') == 'false':
#                             token_obtained = False
#                             break
#
#                     if not token_obtained:
#
#                         # get new token from Figshare
#                         code = request.GET.get('code')
#                         client_id = FIGSHARE_CREDENTIALS['client_id']
#                         token_url = FIGSHARE_API_URLS['authorization_token']
#
#                         # now get token
#                         data = {
#                             'client_id': client_id,
#                             'code': code,
#                             'client_secret': FIGSHARE_CREDENTIALS['client_secret'],
#                             'grant_type': 'authorization_code',
#                             'scope': 'all'
#                         }
#                         try:
#                             r = requests.post(token_url, data)
#                             data_dict = ast.literal_eval(r.content.decode('utf-8'))
#                             token = data_dict['token']
#                             t = Figshare().put_token_for_user(user_id=ThreadLocal.get_current_user().id, token=token)
#                             if t:
#                                 # mark fighshare submissions for this user as token obtained
#                                 Submission().mark_all_token_obtained(user_id=request.user.id)
#
#                                 # if all is well, the access token will be stored in FigshareSubmussionCollection
#                         except Exception as e:
#                             print(e)
#
#                     else:
#                         # retrieve token
#                         token = Figshare().get_token_for_user(user_id=ThreadLocal.get_current_user().id)
#
#
#                         # request.session['partial_submissions'] = doc
#             else:
#                 request.session['partial_submissions'] = None
