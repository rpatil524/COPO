"""module contains simple and generic functions to facilitate data submission"""

__author__ = 'etuka'
__date__ = '25 September 2019'

from bson import ObjectId
import dal.mongo_util as mutil
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import web.apps.web_copo.schemas.utils.data_utils as d_utils
from web.apps.web_copo.lookup.copo_enums import Loglvl, Logtype

lg = settings.LOGGER


def get_submission_handle():  # this can be safely called by forked process
    mongo_client = mutil.get_mongo_client()
    collection_handle = mongo_client['SubmissionCollection']

    return collection_handle


def get_submission_queue_handle():  # this can be safely called by forked process
    mongo_client = mutil.get_mongo_client()
    collection_handle = mongo_client['SubmissionQueueCollection']

    return collection_handle


def get_description_handle():  # this can be safely called by forked process
    mongo_client = mutil.get_mongo_client()
    collection_handle = mongo_client['DescriptionCollection']

    return collection_handle


def get_person_handle():  # this can be safely called by forked process
    mongo_client = mutil.get_mongo_client()
    collection_handle = mongo_client['PersonCollection']

    return collection_handle


def get_datafiles_handle():  # this can be safely called by forked process
    mongo_client = mutil.get_mongo_client()
    collection_handle = mongo_client['DataFileCollection']

    return collection_handle


def get_samples_handle():  # this can be safely called by forked process
    mongo_client = mutil.get_mongo_client()
    collection_handle = mongo_client['SampleCollection']

    return collection_handle


def get_sources_handle():  # this can be safely called by forked process
    mongo_client = mutil.get_mongo_client()
    collection_handle = mongo_client['SourceCollection']

    return collection_handle


def logging_info(message=str(), submission_id=str()):
    """
    function provides a consistent way of logging submission status/information
    :param message:
    :param submission_id:
    :return:
    """

    lg.log('[Submission: ' + submission_id + '] ' + message, level=Loglvl.INFO, type=Logtype.FILE)

    return True


def logging_error(message=str(), submission_id=str()):
    """
    function provides a consistent way of logging error during submission
    :param message:
    :param submission_id:
    :return:
    """

    try:
        lg.log('[Submission: ' + submission_id + '] ' + message, level=Loglvl.ERROR, type=Logtype.FILE)
    except Exception as e:
        pass

    return True


def log_general_info(message):
    """
    logs info not tied to a specific submission record
    :param message:
    :return:
    """

    lg.log('[Submission:] ' + message, level=Loglvl.INFO, type=Logtype.FILE)

    return True


def log_general_error(message):
    """
    logs error not tied to a specific submission record
    :param message:
    :return:
    """
    try:
        lg.log('[Submission: ] ' + message, level=Loglvl.ERROR, type=Logtype.FILE)
    except Exception as e:
        pass

    return True


def update_submission_status(status=str(), message=str(), submission_id=str()):
    """
    function updates status of submission
    :param status: the message type: 'info', 'error'
    :param message: status message
    :param submission_id: the target record id
    :return:
    """

    if not submission_id:
        return True

    collection_handle = get_submission_handle()
    doc = collection_handle.find_one({"_id": ObjectId(submission_id)},
                                     {"transcript": 1, "profile_id": 1})

    if not doc:
        return True

    submission_record = doc
    transcript = submission_record.get("transcript", dict())
    status = dict(type=status, message=message)
    transcript['status'] = status

    if not message:
        transcript.pop('status', '')

    submission_record['transcript'] = transcript
    submission_record['date_modified'] = d_utils.get_datetime()

    collection_handle.update(
        {"_id": ObjectId(str(submission_record.pop('_id')))},
        {'$set': submission_record})

    # notify client agent on status change
    try:
        notify_status_change(profile_id=submission_record.get("profile_id", str()),
                             submission_id=submission_id)
    except Exception as e:
        log_general_error(str(e))

    return True


def notify_status_change(profile_id=str(), submission_id=str()):
    """
    this function notifies the client agent of potential change to submission status for the target record
    :param profile_id:
    :param submission_id:
    :return:
    """

    if submission_id and profile_id:
        event = dict(type='submission_status')
        event["submission_id"] = submission_id

        group_name = 'submission_status_%s' % profile_id

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group_name,
            event
        )

    return True
