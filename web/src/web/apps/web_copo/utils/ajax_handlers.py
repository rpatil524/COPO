__author__ = 'felix.shaw@tgac.ac.uk - 01/12/2015'
# this python file is for small utility functions which will be called from Javascript
import json
import jsonpickle
from datetime import datetime
from bson import json_util, ObjectId

import requests
from django.http import HttpResponse
from django_tools.middlewares import ThreadLocal
from jsonpickle import encode
from dateutil import parser

import web.apps.web_copo.lookup.lookup as ol
from django.conf import settings
from dal.copo_da import ProfileInfo, RemoteDataFile, Submission, DataFile
from submission.figshareSubmission import FigshareSubmit
from dal.figshare_da import Figshare
from dal import mongo_util as util
from pandas import read_excel


def get_source_count(self):
    profile_id = ThreadLocal.get_current_request().session['profile_id']
    num_sources = ProfileInfo(profile_id).source_count()
    return HttpResponse(encode({'num_sources': num_sources}))


def search_ontology(request):
    term = request.GET['query']
    url = settings.ELASTIC_SEARCH_URL
    q = json.dumps({"query": {"match_phrase_prefix": {"name": term}}})
    data = requests.post(url, q)
    return HttpResponse(data.text)


def search_ontology_ebi(request, ontology_names):
    term = request.GET['q']
    if ontology_names == "999":
        ontology_names = str()

    ontologies = ontology_names
    fields = ol.ONTOLOGY_LKUPS['fields_to_search']
    query = ol.ONTOLOGY_LKUPS['ebi_ols_autocomplete'].format(**locals())
    print(query)
    data = requests.get(query, timeout=1).text
    return HttpResponse(data)


def test_ontology(request):
    x = {'a': 'x', 'b': 'y', 'c': 'z'}
    return HttpResponse(encode(x))


def get_upload_information(request):
    context = dict()

    ids = json.loads(request.POST.get("ids", "[]"))
    sub_info_list = list()

    for id in ids:
        # get submission collection and check status
        sub = Submission().get_record(id)

        sub_info_dict = dict(submission_id=id, submission_status=False)

        if sub:
            # get bundle transfer status
            sub_info_dict["bundle_meta"] = sub.get("bundle_meta", list())
            sub_info_dict["bundle"] = sub.get("bundle", list())

            if str(sub.get("complete", False)).lower() == 'false':
                # could we be dealing with an uploading submission?
                rem = RemoteDataFile().get_by_sub_id(id)

                # summary of files uploaded
                sub_info_dict["uploaded_summary"] = str()
                if sub_info_dict["bundle_meta"]:
                    uploaded_files = [x["file_id"] for x in sub_info_dict['bundle_meta'] if x["upload_status"]]
                    sub_info_dict["uploaded_summary"] = str(len(uploaded_files)) + "/" + str(len(
                        sub_info_dict["bundle"])) + " datafiles uploaded"

                sub_info_dict["restart_submission"] = False  # flag for stalled submission needing a restart

                if rem:
                    sub_info_dict["active_submission"] = True
                    sub_info_dict["pct_completed"] = rem['pct_completed']

                    # summary of uploaded size and rate
                    sub_info_dict["upload_sizerate_summary"] = str()
                    if rem['bytes_transferred'] and rem['file_size_bytes'] and rem['transfer_rate']:
                        sub_info_dict["upload_sizerate_summary"] = str(rem['bytes_transferred']) + "/" + str(
                            rem['file_size_bytes']) + " uploaded @ " + str(rem['transfer_rate'])

                    # get current file being transferred
                    datafile_id = rem.get("datafile_id", str())
                    if datafile_id:
                        sub_info_dict["datafile"] = DataFile().get_record(datafile_id).get("name", str())

                    # is the transfer still active or has it stalled?
                    # to answer this question, calculate the delta between current time and last recorded activity
                    current_time = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    fmt = "%d-%m-%Y %H:%M:%S"
                    tdelta = datetime.strptime(current_time, fmt) - datetime.strptime(rem['current_time'], fmt)
                    time_threshold = 4  # acceptable threshold, after perceived inactivity,
                    # for the submission to be classified as valid
                    if tdelta.seconds / 60 > time_threshold:  # i.e. elapsed time = 'time_threshold' minutes
                        sub_info_dict["active_submission"] = False
                        sub_info_dict["submission_error"] = "Possible timeout in submission."

                    # check for error
                    if rem.get("error", str()):
                        sub_info_dict["active_submission"] = False
                        sub_info_dict["submission_error"] = rem["error"]

                    # has the actual upload of files concluded?
                    sub_info_dict["transfer_status"] = rem['transfer_status']
                else:
                    # submission was never started, or something happened along the line but we can't tell
                    sub_info_dict["active_submission"] = False
            else:
                # submission has finished
                sub_info_dict["submission_status"] = True
                sub_info_dict["accessions"] = sub['accessions']
                sub_info_dict["completed_on"] = sub['completed_on'].strftime('%d %b, %Y, %H:%M')
                sub_info_dict["article_id"] = sub['article_id']

            sub_info_list.append(sub_info_dict)

    context["submission_information"] = sub_info_list
    out = jsonpickle.encode(context)
    return HttpResponse(out, content_type='application/json')


def publish_figshare(request):
    sub_id = request.POST['submission_id']
    s = Submission().get_record(sub_id)
    resp = FigshareSubmit(sub_id).publish_article(s['accession'])
    return HttpResponse(
        json.dumps({'status_code': resp.status_code, 'location': json.loads(resp.content.decode('utf8'))['location']}))


def get_tokens_for_user(request):
    user = ThreadLocal.get_current_user().id
    # get Figshare Tokens
    t = util.cursor_to_list(Figshare().get_figshare_tokens_for_user(user))
    return HttpResponse(json_util.dumps({'figshare_tokens': t}))


def delete_token(request):
    tok_id = request.POST['token_id']
    resp = Figshare().delete_token(tok_id)
    return HttpResponse(json_util.dumps({'resp': resp.acknowledged}))


def get_excel_data(request):
    x = read_excel('/Users/fshaw/Dropbox/Shawtuk/dev/snps/test/test_data/ExampleSNPTable_small.xlsx', sheetname=0)
    return HttpResponse(json.dumps(x.values.tolist()))


def get_accession_data(request):
    sub_id = request.GET.get('sub_id')
    sub = Submission().get_file_accession(sub_id)

    return HttpResponse(json_util.dumps({'sub': sub}))


def set_session_variable(request):
    try:
        key = request.POST['key']
        value = request.POST['value']
        request.session[key] = value
    except:
        pass
    return HttpResponse(True)
