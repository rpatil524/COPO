import json
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from jsonpickle import encode
from submission.submissionDelegator import delegate_submission
from dal.orcid_da import Orcid
from api.handlers.general import *
from django_tools.middlewares import ThreadLocal
from dal.copo_da import ProfileInfo, Profile, Submission
from dal.broker_da import BrokerDA, BrokerVisuals
from .lookup.lookup import HTML_TAGS
from exceptions_and_logging.logger import Logtype, Loglvl
from exceptions_and_logging.CopoRuntimeError import CopoRuntimeError
from django.conf import settings
from allauth.account.forms import LoginForm
from dal.copo_da import Annotation
from bson import json_util as j
from dal.figshare_da import Figshare
from web.apps.web_copo.lookup.lookup import FIGSHARE_API_URLS
import requests
import ast
import web.apps.web_copo.lookup.lookup as lkup

LOGGER = settings.LOGGER


@login_required
def index(request):
    context = {'user': request.user}
    request.META['test'] = 'test'

    # check if there are partial_deposits, if so forward user back to that
    if True:
        context['partial_submission_redirect_url'] = 'http://www.google.com'
    else:
        context['partial_submission_redirect_url'] = None

    context['haha'] = 'testing123'

    return render(request, 'copo/index.html', context)


def login(request):
    context = {
        'login_form': LoginForm(),
    }
    return render(request, 'copo/auth/login.html', context)


def test_pdf(request):
    return render(request, 'copo/test_page.html', {})


def test(request):
    try:
        LOGGER.log('Test Error Message 123', type=Logtype.FILE, level=Loglvl.INFO)
    except CopoRuntimeError as l:
        return render(request, 'copo/error_page.html', {'message': str(l)})

    return render(request, 'copo/test_page.html')


def test_submission(request):
    delegate_submission(request)
    return render(request, 'copo/test_page.html', {})


def forward_to_info(request):
    message = request.GET['message']
    control = request.GET['control']
    return render(request, 'copo/info_page.html', {'message': message, 'control': control})


def authenticate_figshare(request):
    return render(request, 'copo/info_page.html',
                  {'message': 'COPO needs permission to submit to Figshare on your behalf.<br/>' +
                              'Please sign into Figshare and try again.',
                   'control': HTML_TAGS['oauth_required']})


def test_figshare_submit(request):
    # from submission.figshareSubmission import FigshareSubmit as fs
    # from dal.figshare_da import Figshare as f
    #
    # token = f().get_token_for_user(request.user.id)['token']
    #
    # fs().submit(["5732ee6268236b786d9d567c"], token)
    return render(request, 'copo/test_page.html', {})


@login_required
def view_copo_profile(request, profile_id):
    request.session["profile_id"] = profile_id

    profile = Profile().get_record(profile_id)
    if not profile:
        return render(request, 'copo/error_page.html')
    context = {"p_id": profile_id, 'counts': ProfileInfo(profile_id).get_counts(), "profile": profile}
    return render(request, 'copo/copo_profile.html', context)


@login_required
def get_profile_counts(request):
    profile_id = request.session["profile_id"]
    counts = ProfileInfo(profile_id).get_counts()
    return HttpResponse(encode(counts))


@login_required
def copo_publications(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)

    return render(request, 'copo/copo_publications.html', {'profile_id': profile_id, 'profile': profile})


@login_required
def copo_annotation(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)

    return render(request, 'copo/copo_annotations.html', {'profile_id': profile_id, 'profile': profile})


@login_required
def copo_people(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)

    return render(request, 'copo/copo_people.html', {'profile_id': profile_id, 'profile': profile})


@login_required
def copo_samples(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)
    return render(request, 'copo/copo_sample_2.html', {'profile_id': profile_id, 'profile': profile})


@login_required
def copo_data(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)
    return render(request, 'copo/copo_data.html', {'profile_id': profile_id, 'profile': profile})


def copo_docs(request):
    context = dict()
    return render(request, 'copo/copo_docs.html', {'context': context})


@login_required
def copo_visualize(request):
    context = dict()

    task = request.POST.get("task", str())

    profile_id = request.session.get("profile_id", str())

    context["quick_tour_flag"] = request.session.get("quick_tour_flag", True)
    request.session["quick_tour_flag"] = context["quick_tour_flag"]  # for displaying tour message across site

    broker_visuals = BrokerVisuals(context=context,
                                   profile_id=profile_id,
                                   component=request.POST.get("component", str()),
                                   target_id=request.POST.get("target_id", str()),
                                   quick_tour_flag=request.POST.get("quick_tour_flag", False),
                                   datafile_ids=json.loads(request.POST.get("datafile_ids", "[]"))
                                   )

    task_dict = dict(table_data=broker_visuals.do_table_data,
                     profiles_counts=broker_visuals.do_profiles_counts,
                     wizard_messages=broker_visuals.do_wizard_messages,
                     metadata_ratings=broker_visuals.do_metadata_ratings,
                     description_summary=broker_visuals.do_description_summary,
                     un_describe=broker_visuals.do_un_describe,
                     attributes_display=broker_visuals.do_attributes_display,
                     help_messages=broker_visuals.get_component_help_messages,
                     update_quick_tour_flag=broker_visuals.do_update_quick_tour_flag,
                     get_component_info=broker_visuals.do_get_component_info,
                     get_profile_info=broker_visuals.do_get_profile_info,
                     )

    if task in task_dict:
        context = task_dict[task]()

    out = jsonpickle.encode(context)
    return HttpResponse(out, content_type='application/json')


@login_required
def copo_forms(request):
    context = dict()
    task = request.POST.get("task", str())

    profile_id = request.session.get("profile_id", str())

    if request.POST.get("profile_id", str()):
        profile_id = request.POST.get("profile_id")
        request.session["profile_id"] = profile_id

    broker_da = BrokerDA(context=context,
                         profile_id=profile_id,
                         component=request.POST.get("component", str()),
                         target_id=request.POST.get("target_id", str()),
                         target_ids=json.loads(request.POST.get("target_ids", "[]")),
                         datafile_ids=json.loads(request.POST.get("datafile_ids", "[]")),
                         auto_fields=request.POST.get("auto_fields", dict()),
                         visualize=request.POST.get("visualize", str()),
                         id_handle=request.POST.get("id_handle", str()),
                         user_id=request.user.id,
                         id_type=request.POST.get("id_type", str()),
                         user_email=request.POST.get("user_email", str())
                         )

    task_dict = dict(resources=broker_da.do_form_control_schemas,
                     save=broker_da.do_save_edit,
                     edit=broker_da.do_save_edit,
                     delete=broker_da.do_delete,
                     form=broker_da.do_form,
                     form_and_component_records=broker_da.do_form_and_component_records,
                     doi=broker_da.do_doi,
                     initiate_submission=broker_da.do_initiate_submission,
                     user_email=broker_da.do_user_email,
                     component_record=broker_da.do_component_record,
                     )

    if task in task_dict:
        context = task_dict[task]()

    out = jsonpickle.encode(context)

    return HttpResponse(out, content_type='application/json')


@login_required
@staff_member_required
def copo_admin(request):
    context = dict()
    task = request.POST.get("task", str())

    # broker_visuals = BrokerVisuals(context=context,
    #                                component=request.POST.get("component", str()),
    #                                target_id=request.POST.get("target_id", str()),
    #                                datafile_ids=json.loads(request.POST.get("datafile_ids", "[]"))
    #                                )
    #
    # task_dict = dict(table_data=broker_visuals.do_table_data,
    #                  profiles_counts=broker_visuals.do_profiles_counts,
    #                  wizard_messages=broker_visuals.do_wizard_messages,
    #                  metadata_ratings=broker_visuals.do_metadata_ratings,
    #                  description_summary=broker_visuals.do_description_summary,
    #                  un_describe=broker_visuals.do_un_describe,
    #                  attributes_display=broker_visuals.do_attributes_display,
    #                  help_messages=broker_visuals.get_component_help_messages,
    #                  )
    #
    # if task in task_dict:
    #     context = task_dict[task]()

    out = jsonpickle.encode(context)
    return HttpResponse(out, content_type='application/json')


@login_required
def copo_submissions(request, profile_id):
    request.session["profile_id"] = profile_id
    profile = Profile().get_record(profile_id)
    submission = Submission(profile_id=profile_id).get_all_records()
    return render(request, 'copo/copo_submission.html',
                  {'profile_id': profile_id, 'submission': submission, 'profile': profile})


@login_required
def copo_get_submission_table_data(request):
    profile_id = request.POST.get('profile_id')
    submission = Submission(profile_id=profile_id).get_all_records()
    for s in submission:
        s['date_created'] = s['date_created'].strftime('%d %b %Y - %I:%M %p')
        s['date_modified'] = s['date_modified'].strftime('%d %b %Y - %I:%M %p')
        if s['complete'] == 'false' or s['complete'] == False:
            s['status'] = 'Pending'
        else:
            s['status'] = 'Submitted'

    out = j.dumps(submission)
    return HttpResponse(out)


@login_required
def goto_error(request, message="Something went wrong, but we're not sure what!"):
    try:
        LOGGER.log(message)
    finally:
        context = {'message': message}
        return render(request, 'copo/error_page.html', context)


def copo_logout(request):
    logout(request)
    return render(request, 'copo/auth/logout.html', {})


def copo_register(request):
    if request.method == 'GET':
        return render(request, 'copo/register.html')
    else:
        # create user and return to auth page
        firstname = request.POST['frm_register_firstname']
        lastname = request.POST['frm_register_lastname']
        email = request.POST['frm_register_email']
        username = request.POST['frm_register_username']
        password = request.POST['frm_register_password']

        user = User.objects.create_user(username, email, password)
        user.set_password(password)
        user.last_name = lastname
        user.first_name = firstname
        user.save()

        return render(request, 'copo/templates/account/auth.html')


@login_required
def view_orcid_profile(request):
    user = ThreadLocal.get_current_user()
    op = Orcid().get_orcid_profile(user)
    data_dict = {'op': op}
    # data_dict = jsonpickle.encode(data_dict)

    return render(request, 'copo/orcid_profile.html', data_dict)


def register_to_irods(request):
    status = register_to_irods()
    return_structure = {'exit_status': status}
    out = jsonpickle.encode(return_structure)
    return HttpResponse(out, content_type='json')


def view_oauth_tokens(request):
    return render(request, 'copo/copo_tokens.html', {})


def annotate_data(request):
    doc = Annotation().get_record(request.POST.get('target_id'))
    return HttpResponse(j.dumps(doc))
