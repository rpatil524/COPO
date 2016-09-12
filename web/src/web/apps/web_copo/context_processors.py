__author__ = 'felix.shaw@tgac.ac.uk - 27/05/15'
from dal import Profile_Status_Info
from dal.figshare_da import Figshare
import ast
import requests

def get_status(request):

    # call method to obtain number of profiles which have outstanding issues
    issues = Profile_Status_Info().get_profiles_status()
    if issues['num_issues'] == 0:
        return {'num_issues': ''}
    else:
        return {'num_issues': issues['num_issues'], 'issue_description_list': issues['issue_description_list']}


def add_partial_submissions_to_context(request):
    return {'partial_submissions':'ommitted'}
'''
def complete_oauth(request):
    code = request.session['figshare_oauth_code']
    state = request.session['fighsare_oauth_state']
    data = {
        'client_id'
    }
    r = requests.post('https://api.figshare.com/v2/token')

def finish_oauth_authentication(request):
    # check whether we want to continue with oauth dance
    continue_sub = ast.literal_eval(request.GET.get('figshare_oauth', 'false').capitalize())
    figshare_code = request.session.get('figshare_oauth_code', 'default')
    if figshare_code != 'default' and continue_sub:
        # we need to continue with the oauth dance
        print(figshare_code)
    return {}
'''
