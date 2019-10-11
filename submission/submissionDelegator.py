__author__ = 'felix.shaw@tgac.ac.uk - 27/05/2016'

from django.http import HttpResponse
from dal.copo_da import Submission
from . import enaSubmission, figshareSubmission, dataverseSubmission, dspaceSubmission, ckanSubmission
from django.urls import reverse
import jsonpickle, json


def delegate_submission(request):
    # get submission object
    sub_id = request.POST.get('sub_id')
    if not sub_id:
        sub_id = request.GET.get('sub_id')

    if not sub_id:
        return HttpResponse({'status': 0})

    sub = Submission().get_record(sub_id)

    repo = sub['repository']

    error = None

    ## Submit to Figshare
    if repo == 'figshare':

        # check figshare credentials
        if figshareSubmission.FigshareSubmit(sub_id).isValidCredentials(user_id=request.user.id):

            figshareSubmission.FigshareSubmit(sub_id).submit(
                sub_id=sub_id,
                dataFile_ids=sub['bundle'],

            )
            return HttpResponse(jsonpickle.dumps({'status': 1}))

        else:
            # forward to control view
            return HttpResponse(jsonpickle.dumps({'status': 1, 'url': reverse('copo:authenticate_figshare')}))

    # Submit to ENA Sequence reads
    elif repo == 'ena':
        result = schedule_submission(submission_id=sub_id, submission_repo='ena')

        if result.get("status", True) is True:
            return HttpResponse(jsonpickle.dumps({'status': 0}))
        else:
            return HttpResponse(jsonpickle.dumps({'status': 1, 'message': result.get("message", str())}))

    # Submit to ENA
    elif 'ena' in repo:
        result = enaSubmission.EnaSubmit().submit(
            sub_id=sub_id,
            dataFile_ids=sub['bundle'],
        )
        if result is True:
            return HttpResponse(jsonpickle.dumps({'status': 1}))
        else:
            error = result


    ## Submit to Dataverse
    elif repo == 'dataverse':
        result = dataverseSubmission.DataverseSubmit(submission_id=sub_id).submit()
        if result is True:
            return HttpResponse(jsonpickle.dumps({'status': 0}))
        else:
            if isinstance(result, str):
                message = result
                status = 404
            elif isinstance(result, dict):
                message = result.get("message", str())
                status = result.get("status", 404)

            message = "\n " + message
            return HttpResponse(message, status=status)

    ## Submit to dspace
    elif repo == 'dspace':
        result = dspaceSubmission.DspaceSubmit().submit(
            sub_id=sub_id,
            dataFile_ids=sub['bundle']
        )
        if result == True:
            return HttpResponse(jsonpickle.dumps({'status': 0}))
        else:
            error = result


    # Submit to CKAN
    elif repo == 'ckan':
        result = ckanSubmission.CkanSubmit(sub_id).submit(
            sub_id=sub_id,
            dataFile_ids=sub['bundle']
        )
        if result == True:
            return HttpResponse(jsonpickle.dumps({'status': 0}))
        else:
            error = json.loads(result)

    # return error
    return HttpResponse(error["message"], status=error["status"])


def schedule_submission(submission_id=str(), submission_repo=str()):
    """
    function adds submission to a queue for processing
    :return:
    """

    from submission.helpers import generic_helper as ghlper
    import web.apps.web_copo.schemas.utils.data_utils as d_utils

    context = dict(status=True, message='')

    if not submission_id:
        context = dict(status=False, message='Submission identifier not found!')
        return context

    collection_handle = ghlper.get_submission_queue_handle()
    doc = collection_handle.find_one({"submission_id": submission_id})

    if not doc:  # submission not already in queue, add to queue
        fields = dict(
            submission_id=submission_id,
            date_modified=d_utils.get_datetime(),
            repository=submission_repo,
            processing_status='pending'
        )

        collection_handle.insert(fields)
        context['message'] = 'Submission has been added to the processing queue. Status update will be reported.'
    else:
        context['message'] = 'Submission is already in the processing queue. Status updates will be reported.'

    ghlper.update_submission_status(status='info', message=context['message'], submission_id=submission_id)
    ghlper.logging_info(context['message'], submission_id)

    return context
