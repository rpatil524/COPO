__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'
import sys

from bson.errors import InvalidId

from api.utils import get_return_template, extract_to_template, finish_request
from dal.copo_da import Sample, Source
from web.apps.web_copo.lookup.lookup import API_ERRORS


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
        if type(ss) is not InvalidId:
            return do_standard_sample(ss)
        else:
            # if user supplied an ENA accession
            ss = Sample().get_dtol_type(id)
            if ss:
                return do_dtol_sample(ss)
            else:
                return finish_request()
    except TypeError as e:
        print(e)
        return finish_request(error=API_ERRORS['NOT_FOUND'])
    except InvalidId as e:
        print(e)
        return finish_request(error=API_ERRORS['INVALID_PARAMETER'])
    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise

def do_dtol_sample(ss):
    resp = finish_request(ss)
    return resp


def do_standard_sample(ss):
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

