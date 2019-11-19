__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'

import json

import jsonpickle
from django.http import HttpResponse

from web.apps.web_copo.lookup.lookup import API_RETURN_TEMPLATES


def get_return_template(type):
    """
    Method to return a python object representation of the given api template return type
    :param type: a string naming the template type
    :return: an python object representation of the json contained in the template
    """
    path = API_RETURN_TEMPLATES[type.upper()]
    with open(path) as data_file:
        data = json.load(data_file)
    return data


def extract_to_template(object=None, template=None):
    """
    Method to examine fields in object and extract those which match the field names in template along with their values
    :param object: the object to search
    :param template: the fields to look for
    :return: the template with the values completed
    """
    for f in object:
        for t in template:
            if f == t:
                template[t] = object[t]

    return template


def finish_request(template=None, error=None):
    """
    Method to tidy up data before returning API caller
    :param template: completed template of resource data
    :param error_info: error created if any
    :return: the complete API return
    """
    wrapper = get_return_template('WRAPPER')
    if error is None:
        wrapper['number_found'] = len(template)
        wrapper['items'] = template
        wrapper['status']['error'] = False
    else:
        wrapper['status']['error'] = True
        wrapper['status']['error_detail'] = error
        wrapper['number_found'] = None
        wrapper['items'] = None

    return HttpResponse(jsonpickle.encode(wrapper))

