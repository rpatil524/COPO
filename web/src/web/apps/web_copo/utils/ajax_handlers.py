__author__ = 'felix.shaw@tgac.ac.uk - 01/12/2015'
# this python file is for small utility functions which will be called from Javascript
import json
import jsonpickle
from datetime import datetime
from bson import json_util, ObjectId

import requests
from django.http import HttpResponse, HttpResponseBadRequest
from web.apps.web_copo.schemas.utils import data_utils
from jsonpickle import encode
from dateutil import parser
from dal.copo_da import Profile
import web.apps.web_copo.lookup.lookup as ol
from django.conf import settings
from dal.copo_da import ProfileInfo, RemoteDataFile, Submission, DataFile, Sample, Source, CopoGroup, Annotation, Repository
from submission.figshareSubmission import FigshareSubmit
from dal.figshare_da import Figshare
from dal import mongo_util as util
from pandas import read_excel
from submission.dataverseSubmission import DataverseSubmit
from django.contrib.auth.models import User
from web_copo.models import UserDetails
from django.db.models import Q
from django.contrib.auth.models import Group
from django.core import serializers


def get_source_count(self):
    profile_id = data_utils.get_current_request().session['profile_id']
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
    # TODO - add return here for when OLS is down
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
                    time_threshold = 15  # acceptable threshold, after perceived inactivity,
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
                try:
                    sub_info_dict["accessions"] = sub['accessions']
                except:
                    sub_info_dict["accessions"] = "unavailable"
                try:
                    sub_info_dict["completed_on"] = sub['completed_on'].strftime('%d %b, %Y, %H:%M')
                except:
                    sub_info_dict["completed_on"] = "unavailable"
                try:
                    sub_info_dict["article_id"] = sub['article_id']
                except:
                    sub_info_dict["article_id"] = "unavailable"

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
    user = data_utils.get_current_user().id
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


def get_dataset_details(request):
    profile_id = request.GET['profile_id']
    resp = Profile().check_for_dataset_details(profile_id)
    return HttpResponse(json.dumps(resp))


def get_samples_for_study(request):
    # get all samples which have corresponding profile_id number
    profile_id = request.POST['profile_id']
    samples = Sample().get_from_profile_id(profile_id=profile_id)
    output = list()
    for s in samples:
        source = Source().get_record(s['derivesFrom'][0])
        # s.update(source)
        d = {"organism": source["organism"], "_id": s["_id"], "name": s["name"]}
        output.append(d)
    return HttpResponse(json_util.dumps(output))


def set_session_variable(request):
    try:
        key = request.POST['key']
        value = request.POST['value']
        request.session[key] = value
    except:
        pass

    key = request.POST['key']
    try:
        value = request.POST['value']
    except:
        value = None
    request.session[key] = value
    return HttpResponse(True)


def get_continuation_studies():
    user = data_utils.get_current_user()
    profiles = Profile().get_for_user(user.id)
    output = list()
    for p in profiles:
        output.append(
            {
                "value": p.title,
                "label": p._id
            }
        )
    return output


def create_group(request):
    name = request.GET['group_name']
    description = request.GET['description']
    uid = CopoGroup().create_shared_group(name=name, description=description)

    if uid:
        return HttpResponse(json.dumps({'id': str(uid), 'name': name}))
    else:
        return HttpResponseBadRequest('Error Creating Group - Try Again')


def delete_group(request):
    id = request.GET['group_id']
    deleted = CopoGroup().delete_group(group_id=id)
    if deleted:
        return HttpResponse(json.dumps({'deleted': True}))
    else:
        return HttpResponseBadRequest('Error Deleting Group - Try Again')


def add_profile_to_group(request):
    group_id = request.GET['group_id']
    profile_id = request.GET['profile_id']
    resp = CopoGroup().add_profile(group_id=group_id, profile_id=profile_id)
    if resp:
        return HttpResponse(json.dumps({'resp': 'Added to Group'}))
    else:
        return HttpResponseBadRequest(json.dumps({'resp': 'Server Error - Try again'}))


def remove_profile_from_group(request):
    group_id = request.GET['group_id']
    profile_id = request.GET['profile_id']
    resp = CopoGroup().remove_profile(group_id=group_id, profile_id=profile_id)
    if resp:
        return HttpResponse(json.dumps({'resp': 'Removed from Group'}))
    else:
        return HttpResponseBadRequest(json.dumps({'resp': 'Server Error - Try again'}))


def get_profiles_in_group(request):
    group_id = request.GET['group_id']
    grp_info = CopoGroup().get_profiles_for_group_info(group_id=group_id)
    return HttpResponse(json_util.dumps({'resp': grp_info}))


def get_users_in_group(request):
    group_id = request.GET['group_id']
    usr_info = CopoGroup().get_users_for_group_info(group_id=group_id)
    return HttpResponse(json_util.dumps({'resp': usr_info}))


def get_users(request):
    q = request.GET['q']
    x = list(User.objects.filter(
        Q(first_name__istartswith=q) | Q(last_name__istartswith=q) | Q(username__istartswith=q)).exclude(
        is_superuser=True).values_list('id', 'first_name', 'last_name', 'email', 'username'))
    if not x:
        return HttpResponse()
    return HttpResponse(json.dumps(x))


def add_user_to_group(request):
    group_id = request.GET['group_id']
    user_id = request.GET['user_id']
    grp_info = CopoGroup().add_user_to_group(group_id=group_id, user_id=user_id)
    return HttpResponse(json_util.dumps({'resp': grp_info}))


def remove_user_from_group(request):
    group_id = request.GET['group_id']
    user_id = request.GET['user_id']
    grp_info = CopoGroup().remove_user_from_group(group_id=group_id, user_id=user_id)
    return HttpResponse(json_util.dumps({'resp': grp_info}))


def get_ontologies(request):
    resp = requests.get('http://www.ebi.ac.uk/ols/api/ontologies?size=5000&sort=ontologyId')
    data = json_util.dumps(json_util.loads(resp.content.decode('utf-8'))['_embedded']['ontologies'])
    return HttpResponse(data)


def export_generic_annotation(request):
    ant_id = request.POST["annotation_id"]
    doc = Annotation().get_annotations_for_page(ant_id)
    out = {"raw": json.loads(doc["raw"]), "annotations": doc["annotation"]}
    return HttpResponse(json_util.dumps(out))


def create_new_repo(request):
    name = request.POST['name']
    type = request.POST['type']
    url = request.POST['url']
    apikey = request.POST['apikey']
    username = request.POST['username']
    password = request.POST['password']
    uid = request.user.id
    args = {'name': name, 'type': type, 'url': url, 'apikey': apikey, 'username': username, 'password': password,
            'uid': uid}
    Repository().save_record(dict(), **args)
    out = {'name': name, 'type': type, 'url': url}
    return HttpResponse(json_util.dumps(out))


def get_repos_data(request):
    uid = request.user.id
    u_type = request.GET["u_type"]
    if u_type == "managers":
        doc = Repository().get_by_uid(uid)
    elif u_type == "submitters":
        u = User.objects.get(pk=uid)
        repo_ids = u.userdetails.repo_manager
        doc = list()
        for r in repo_ids:
            doc.append(Repository().get_record(ObjectId(r)))
    return HttpResponse(json_util.dumps(doc))


def add_user_to_repo(request):
    repo_id = request.GET['repo_id']
    user_id = request.GET['user_id']
    first_name = request.GET['first_name']
    last_name = request.GET['last_name']
    username = request.GET['username']
    email = request.GET['email']
    u_type = request.GET['u_type']
    u = User.objects.get(pk=user_id)
    if u_type == "managers":
        dms = Group.objects.get(name='data_managers')
        dms.user_set.add(u)
        # User.UserDetails is an extension to User via a one-to-one django field....look in models.py
        repos = u.userdetails.repo_manager
        if repos == None:
            u.userdetails.repo_manager = [repo_id]
            u.save()
        else:
            if repo_id not in repos:
                u.userdetails.repo_manager.append(repo_id)
                u.save()
    elif u_type == "submitters":
        repos = u.userdetails.repo_submitter
        if repos == None:
            u.userdetails.repo_submitter = [repo_id]
            u.save()
        else:
            if repo_id not in repos:
                u.userdetails.repo_submitter.append(repo_id)
                u.save()

    out = {"out": "0", "user_id": user_id, "first_name": first_name, "last_name": last_name, "username": username,
           "email": email}
    return HttpResponse(json_util.dumps(out))


def remove_user_from_repo(request):
    repo_id = request.GET['repo_id']
    user_id = request.GET['uid']
    u = User.objects.get(pk=user_id)
    u.userdetails.repo_manager.remove(repo_id)
    u.save()
    if len(u.userdetails.repo_manager) == 0:
        # remove from admins group
        dms = Group.objects.get(name='data_managers')
        dms.user_set.remove(u)

    return HttpResponse(json_util.dumps({"out": "1"}))


def get_users_in_repo(request):
    repo_id = request.GET['repo_id']
    u_type = request.GET['user_type']
    if u_type == 'managers':
        data = UserDetails.objects.filter(repo_manager__contains=[repo_id])
    elif u_type == 'submitters':
        data = UserDetails.objects.filter(repo_submitter__contains=[repo_id])
    u_list = list()
    for d in data:
        u_list.append({'uid': d.user.id, 'first_name': d.user.first_name, 'last_name': d.user.last_name})
    #data = serializers.serialize('json', u_list)
    return HttpResponse(json_util.dumps(u_list))


def get_repos_for_user(request):
    #u_type = request.GET['u_type']
    uid = str(request.user.id)
    group_id = request.GET['group_id']
    doc = CopoGroup().get_repos_for_group_info(uid, group_id)
    return HttpResponse(json_util.dumps({'resp': doc}))


def add_repo_to_group(request):
    group_id = request.GET['group_id']
    repo_id = request.GET['repo_id']
    resp = CopoGroup().add_repo(group_id=group_id, repo_id=repo_id)
    if resp:
        return HttpResponse(json.dumps({'resp': 'Added to Group'}))
    else:
        return HttpResponseBadRequest(json.dumps({'resp': 'Server Error - Try again'}))


def remove_repo_from_group(request):
    group_id = request.GET['group_id']
    repo_id = request.GET['repo_id']
    resp = CopoGroup().remove_repo(group_id=group_id, repo_id=repo_id)
    if resp:
        return HttpResponse(json.dumps({'resp': 'Removed from Group'}))
    else:
        return HttpResponseBadRequest(json.dumps({'resp': 'Server Error - Try again'}))


def get_repo_info(request):
    repo_id = request.GET['repo_id']
    repo = Repository().get_record(ObjectId(repo_id))
    out = {'repo_type': repo['type'], 'repo_url': repo['url']}
    return HttpResponse(json.dumps(out))