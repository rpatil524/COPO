__author__ = 'felix.shaw@tgac.ac.uk - 22/09/15'
import ast

import jsonpickle
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from dal.copo_da import Submission

from web.apps.web_copo.wizards.datafile import broker_requests as datf
from web.apps.web_copo.wizards.sample import broker_requests as samp
from web.apps.web_copo.lookup.lookup import FIGSHARE_API_URLS


def data_wiz(request):
    context = dict()
    request_action = request.POST.get("request_action", str())

    description_targets = ast.literal_eval(request.POST.get("description_targets", "[]"))
    description_bundle = ast.literal_eval(request.POST.get("description_bundle", "[]"))

    if description_bundle:
        request.session['description_bundle'] = description_bundle

    context = datf.BrokerRequests(context=context,
                                  description_targets=description_targets,
                                  description_bundle=description_bundle,
                                  description_token=request.POST.get("description_token", str()),
                                  stage_id=request.POST.get("stage_id", str()),
                                  stage_ref=request.POST.get("stage_ref", str()),
                                  auto_fields=request.POST.get("auto_fields", dict()),
                                  default_stage_form=request.POST.get("default_stage_form", False),
                                  target_id=request.POST.get("target_id", str())
                                  ).post_context(request_action)

    out = jsonpickle.encode(context)

    return HttpResponse(out, content_type='application/json')


def sample_wiz(request):
    context = dict()
    request_action = request.POST.get("request_action", str())

    generated_samples = ast.literal_eval(request.POST.get("generated_samples", "[]"))
    target_rows = ast.literal_eval(request.POST.get("target_rows", "[]"))

    context = samp.BrokerRequests(context=context,
                                  generated_samples=generated_samples,
                                  target_rows=target_rows,
                                  target_id=request.POST.get("target_id", str()),
                                  sample_type=request.POST.get("sample_type", str()),
                                  auto_fields=request.POST.get("auto_fields", dict()),
                                  initial_sample_attributes=request.POST.get("initial_sample_attributes", dict()),
                                  update_metadata=request.POST.get("update_metadata", dict()),
                                  number_to_generate=request.POST.get("number_to_generate", str()),
                                  column_reference=request.POST.get("column_reference", str()),
                                  bundle_name=request.POST.get("bundle_name", str()),
                                  resolved_object=request.POST.get("resolved_object", dict()),
                                  ).post_context(request_action)

    out = jsonpickle.encode(context)

    return HttpResponse(out, content_type='application/json')


def forward_to_figshare(request):
    # https://figshare.com/account/applications/authorize?client_id=978ec401ab6ad6c1d66f0b6cef3015d71a4734d7&scope=all&response_type=code&redirect_url=www.example.com

    # get details
    redirect_url = request.META['HTTP_REFERER']
    redirect_url = FIGSHARE_API_URLS['access_token'].format(**locals())

    # create submission to continue upon return from Figshare OAUTH
    return_url = request.META['HTTP_REFERER']
    return_url = FIGSHARE_API_URLS['login_return'].format(**locals())
    files = request.session['description_bundle']
    file_ids = [x['recordID'] for x in files]

    kwarg = dict(profile_id=request.session['profile_id'], datafile_ids=file_ids, redirect_url=redirect_url, complete='false', token_obtained='false')
    Submission().save_record(dict(), **kwarg)


    return HttpResponseRedirect(redirect_url)
