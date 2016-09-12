__author__ = 'felix.shaw@tgac.ac.uk - 01/12/2015'
# this python file is for small utility functions which will be called from Javascript
import json

import requests
from django.http import HttpResponse
from django_tools.middlewares import ThreadLocal
from jsonpickle import encode
from dateutil import parser

import web.apps.web_copo.lookup.lookup as ol
from django.conf import settings
from dal.copo_da import ProfileInfo, RemoteDataFile, Submission


def get_source_count(self):
    profile_id = ThreadLocal.get_current_request().session['profile_id']
    num_sources = ProfileInfo(profile_id).source_count()
    return HttpResponse(encode({'num_sources': num_sources}))


def search_ontology(request):
    term = request.GET['query']
    url = settings.ELASTIC_SEARCH_URL
    q = json.dumps({"query":{"match_phrase_prefix":{"name": term}}})
    #q = '{"query": { "multi_match": { "fields": ["name", "accession_id", "aspect", "definition"], "query": "' + term + '", "type": "phrase_prefix"}}}'
    data = requests.post(url, q)
    return HttpResponse(data.text)


def search_ontology_ebi(request, ontology_names):
    term = request.GET['q']
    if ontology_names == "999":
        ontology_names = str()

    ontologies = ol.ONTOLOGY_LKUPS['ontologies_to_search']
    fields = ol.ONTOLOGY_LKUPS['fields_to_search']
    query = ol.ONTOLOGY_LKUPS['ebi_ols_autocomplete'].format(**locals())
    data = requests.get(query).text
    return HttpResponse(data)


def test_ontology(request):
    x = {'a':'x', 'b':'y', 'c':'z'}
    return HttpResponse(encode(x))


def get_upload_information(request):

    submission_id = request.GET.get('submission_id')

    # get submission collection and check status
    sub = Submission().get_record(submission_id)
    if sub:
        if sub['complete'] == False:
            rem = RemoteDataFile().get_by_sub_id(submission_id)
            if rem:
                speeds = rem['transfer_rate'][-100:]
                complete = rem['pct_completed']
                data = {'speeds': speeds, 'complete': complete, 'finished': False, 'found': True}
                return HttpResponse(json.dumps(data))
        else:
            elapsed = str(parser.parse(sub['completed_on']) - parser.parse(sub['commenced_on']))
            data = {'upload_time': str(elapsed), 'completed_on': sub['completed_on'], 'article_id': sub.get('article_id'), 'finished': True, 'found': True}
            return HttpResponse(json.dumps(data))

    data = {'found': False}
    return HttpResponse(json.dumps(data))
