__author__ = 'felix.shaw@tgac.ac.uk - 29/04/2016'
from django.conf import settings
from dal.figshare_da import Figshare
from web.apps.web_copo.lookup.lookup import FIGSHARE_API_URLS
import requests
from dal.copo_da import Submission
from django_tools.middlewares import ThreadLocal
import ast
import web.apps.web_copo.lookup.lookup as lkup

FIGSHARE_CREDENTIALS = settings['FIGSHARE_CREDENTIALS']
figshare = lkup.VOCAB['REPO_NAMES']['figshare']['value']


class SetFigshareOauth(object):
    def process_request(self, request):

        doc = Submission().get_incomplete_submissions_for_user(request.user.id, figshare)
        data_dict = dict()
        token = None

        if doc.count() > 0:

            if 'code' in request.GET and 'state' in request.GET:

                token_obtained = True

                for d in doc:
                    if not d.get('token_obtained'):
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
                        t = Figshare().put_token_for_user(user_id=ThreadLocal.get_current_user().id, token=token)
                        if t:
                            # mark fighshare submissions for this user as token obtained
                            Submission().mark_all_token_obtained(user_id=request.user.id)

                            # if all is well, the access token will be stored in FigshareSubmussionCollection
                    except Exception as e:
                        print(e)

                else:
                    # retrieve token
                    token = Figshare().get_token_for_user(user_id=ThreadLocal.get_current_user().id)


                    # request.session['partial_submissions'] = doc
        else:
            request.session['partial_submissions'] = None
