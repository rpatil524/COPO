__author__ = 'felix.shaw@tgac.ac.uk - 27/05/15'
from dal import Profile_Status_Info
from dal.figshare_da import Figshare
import ast
import requests
from urllib.parse import urljoin


def get_status(request):
    # call method to obtain number of profiles which have outstanding issues
    issues = Profile_Status_Info().get_profiles_status()
    if issues['num_issues'] == 0:
        return {'num_issues': ''}
    else:
        return {'num_issues': issues['num_issues'], 'issue_description_list': issues['issue_description_list']}


def add_partial_submissions_to_context(request):
    return {'partial_submissions': 'ommitted'}

