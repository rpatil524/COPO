# COPO python file created 20/04/2017 by fshaw

"""
    Utils for accepting and depositing data and metadata to and from services adhering to the SWORD protocol
    https://en.wikipedia.org/wiki/SWORD_(protocol)
"""

import requests
from django.conf import settings
import os
from django.http import HttpResponse
from submission.dataverseSubmission import DataverseSubmit

def test_module(request):
    DataverseSubmit.submit()
    return(HttpResponse(d))


class SWORD_Deposit(object):

    def __init__(self, host_api, host_service, api_token=None, use_https=True):

        # concatenate urls
        if use_https:
            self.http_prefix = 'https://'
        else:
            self.http_prefix = 'http://'
        self.api_host_url = host_api
        self.base_url = '{0}{1}'.format(self.http_prefix, self.api_host_url)
        self.sword_base_url = self.base_url + host_service.format(self.base_url)
        self.token = api_token

    def make_url_for_method(self, method):
        return self.sword_base_url + method

    def set_api_host_url(self, url):
        self.api_host_url = url

    def set_api_token(self, token):
        self.token = token

    def auth(self):
        return self.token, None

    def get_service_document(self):
        url = self.make_url_for_method('service-document')
        r = requests.post(url, auth=self.auth())



class SWORD_Accept(object):
    pass
