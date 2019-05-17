__author__ = 'felix.shaw@tgac.ac.uk - 22/09/15'

import json
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

    description_targets = json.loads(request.POST.get("description_targets", "[]"))

    broker_request = datf.BrokerRequests(context=context,
                                         description_targets=description_targets,
                                         description_token=request.POST.get("description_token", str()),
                                         profile_id=request.POST.get("profile_id", str()),
                                         auto_fields=request.POST.get("auto_fields", dict()),
                                         target_id=request.POST.get("target_id", str()),
                                         cell_reference=request.POST.get("cell_reference", str()),
                                         )

    context = broker_request.post_context(request_action)
    out = jsonpickle.encode(context, unpicklable=False)

    return HttpResponse(out, content_type='application/json')


def sample_wiz(request):
    context = dict()
    request_action = request.POST.get("request_action", str())
    description_file = str()

    if request.method == 'POST' and request.FILES:
        description_file = request.FILES.get("csv", str())

    context = samp.BrokerRequests(context=context,
                                  target_id=request.POST.get("target_id", str()),
                                  resolver_uri=request.POST.get("resolver_uri", str()),
                                  description_token=request.POST.get("description_token", str()),
                                  profile_id=request.POST.get("profile_id", str()),
                                  auto_fields=request.POST.get("auto_fields", dict()),
                                  update_metadata=request.POST.get("update_metadata", dict()),
                                  target_rows=json.loads(request.POST.get("target_rows", "[]")),
                                  cell_reference=request.POST.get("cell_reference", str()),
                                  column_reference=request.POST.get("column_reference", str()),
                                  bundle_name=request.POST.get("bundle_name", str()),
                                  sample_names=request.POST.get("sample_names", str()),
                                  description_file=description_file,
                                  ).post_context(request_action)

    out = jsonpickle.encode(context, unpicklable=False)

    return HttpResponse(out, content_type='application/json')


def forward_to_figshare(request):
    # https://figshare.com/account/applications/authorize?client_id=978ec401ab6ad6c1d66f0b6cef3015d71a4734d7&scope=all&response_type=code&redirect_url=www.example.com

    # get details
    redirect_url = request.META['HTTP_REFERER']
    # Figshare will not redirect to a non HTTPS url so check for this
    if not 'https' in redirect_url:
        redirect_url = redirect_url.replace("http", "https")
    redirect_url = FIGSHARE_API_URLS['access_token'].format(**locals())

    # create submission to continue upon return from Figshare OAUTH
    return_url = request.META['HTTP_REFERER']
    return_url = FIGSHARE_API_URLS['login_return'].format(**locals())
    files = request.session['description_bundle']
    file_ids = [x['recordID'] for x in files]

    kwarg = dict(profile_id=request.session['profile_id'], datafile_ids=file_ids, redirect_url=redirect_url,
                 complete='false', token_obtained='false')
    Submission().save_record(dict(), **kwarg)

    return HttpResponseRedirect(redirect_url)
