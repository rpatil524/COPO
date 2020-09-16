__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'

import sys

from bson.errors import InvalidId

from api.utils import get_return_template, extract_to_template, finish_request
from dal.copo_da import Sample, Source
from web.apps.web_copo.lookup.lookup import API_ERRORS
from web.apps.web_copo.lookup import dtol_lookups as  lookup


def get(request, id):
    """
    Method to handle a request for a single sample object from the API
    :param request: a Django HTTPRequest object
    :param id: the id of the Sample object (can be string or ObjectID)
    :return: an HttpResponse object embedded with the completed return template for Sample
    """

    # farm request to appropriate sample type handler
    try:
        ss = Sample().get_record(id)
        source = ss['source']
        sample = ss['sample']

        # get template for return type
        t_source = get_return_template('SOURCE')
        t_sample = get_return_template('SAMPLE')

        # extract fields for both source and sample
        tmp_source = extract_to_template(object=source, template=t_source)
        tmp_sample = extract_to_template(object=sample, template=t_sample)
        tmp_sample['source'] = tmp_source

        out_list = []
        out_list.append(tmp_sample)

        return finish_request(out_list)
    except TypeError as e:
        print(e)
        return finish_request(error=API_ERRORS['NOT_FOUND'])
    except InvalidId as e:
        print(e)
        return finish_request(error=API_ERRORS['INVALID_PARAMETER'])
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise


def format_date(input_date):
    # format of date fields exported to STS
    return input_date.strftime("%Y-%m-%d, %H:%M:%S")


def filter_for_STS(sample_list):
    # add field here which should be time formatted
    time_fields = ["time_created", "time_verified"]
    export = lookup.DTOL_EXPORT_TO_STS_FIELDS
    out = list()
    for s in sample_list:
        if isinstance(s, InvalidId):
            break
        s_out = dict()
        for k, v in s.items():
            # always export copo id
            if k == "_id":
                s_out["copo_id"] = str(v)
            # check if field is listed to be exported to STS
            if k in export:
                if k in time_fields:
                    s_out[k] = format_date(v)
                else:
                    s_out[k] = v
        out.append(s_out)
    return out


def get_for_manifest(request, manifest_id):
    # get all samples tagged with the given manifest_id
    sample_list = Sample().get_by_manifest_id(manifest_id)
    out = filter_for_STS(sample_list)
    return finish_request(out)


def get_by_biosample_id(request, biosample_id):
    # get sample associated with given biosample_id. This will return nothing if ENA submission has not yet occured
    sample = Sample().get_by_biosample_id(biosample_id)
    out = list()
    if sample:
        out = filter_for_STS([sample])
    return finish_request(out)


def get_by_copo_id(request, copo_id):
    # get sample by COPO id if known
    sample = Sample().get_record(copo_id)
    out = list()
    if sample:
        if not isinstance(sample, InvalidId):
            out = filter_for_STS([sample])
    return finish_request(out)

def get_by_dtol_field(request, dtol_field, value):
    # generic method to return all samples where given "dtol_field" matches "value"
    out = list()
    sample_list = Sample().get_by_dtol_field(dtol_field, value)
    if sample_list:
        out = filter_for_STS(sample_list)
    return finish_request(out)


def get_all(request):
    """
    Method to handle a request for all
    :param request: a Django HttpRequest object
    :return: A dictionary containing all samples in COPO
    """

    out_list = []

    # get sample and source objects
    try:
        sample_list = Sample().get_samples_across_profiles()
    except TypeError as e:
        print(e)
        return finish_request(error=API_ERRORS['NOT_FOUND'])
    except InvalidId as e:
        print(e)
        return finish_request(error=API_ERRORS['INVALID_PARAMETER'])
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise

    for s in sample_list:
        # get template for return type
        t_source = get_return_template('SOURCE')
        t_sample = get_return_template('SAMPLE')

        # get source for sample
        source = Source().GET(s['source_id'])
        # extract fields for both source and sample
        tmp_source = extract_to_template(object=source, template=t_source)
        tmp_sample = extract_to_template(object=s, template=t_sample)
        tmp_sample['source'] = tmp_source

        out_list.append(tmp_sample)

    return finish_request(out_list)
