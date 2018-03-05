__author__ = 'felix.shaw@tgac.ac.uk - 27/05/2016'

from django.http import HttpResponse
from dal.copo_da import Submission
import dal.figshare_da as fda
from . import enaSubmission, figshareSubmission, dataverseSubmission
from django.core.urlresolvers import reverse
import jsonpickle


def delegate_submission(request):
    # get submission object
    sub_id = request.POST.get('sub_id')
    if not sub_id:
        sub_id = request.GET.get('sub_id')

    # tonietuk's intercept starts
    if not sub_id:
        return HttpResponse({'status': 0})
    # tonietuk's intercept ends

    sub = Submission().get_record(sub_id)

    repo = sub['repository']

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

    # Submit to ENA Sequence reads - splits the submission task to micro-tasks to overcome the timeout issues observed
    elif repo == 'ena':
        ena_status = request.POST.get("ena_status", "commenced")
        result = enaSubmission.EnaSubmit4Reads(submission_id=sub_id, status=ena_status).submit()
        return HttpResponse(jsonpickle.dumps({'status': result}))

    # Submit to ENA
    elif 'ena' in repo:
        result = enaSubmission.EnaSubmit().submit(
            sub_id=sub_id,
            dataFile_ids=sub['bundle'],
        )
        if result == True:
            return HttpResponse(jsonpickle.dumps({'status': 1}))
        else:
            return HttpResponse(jsonpickle.dumps({'status': result}))

    ## Submit to Dataverse
    elif repo == 'dcterms':
        result = dataverseSubmission.DataverseSubmit().submit(
            sub_id=sub_id,
            dataFile_ids=sub['bundle']
        )
        if result == True:
            return HttpResponse(jsonpickle.dumps({'status': 1}))
        else:
            return HttpResponse(jsonpickle.dumps({'status': result}))

    # return default
    return HttpResponse({'status': 0})
