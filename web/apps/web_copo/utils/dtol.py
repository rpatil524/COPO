# Created by fshaw at 03/04/2020
from django.http import HttpResponse
import pandas, json
from web.apps.web_copo.lookup import lookup
import jsonpath_rw_ext as jp

def loadCsv(file):
    raise NotImplementedError



def loadExcel(file):
    try:
        data = pandas.read_excel(file)
    except pandas.XLRDError as e:
        return HttpResponse(status=500,
                            content="Unable to load file. Please makes sure you are uploading a valid Excel file")
    validate(data)
    return HttpResponse()

def validate(data):
    # need to load validation field set
    with open(lookup.WIZARD_FILES["sample_details"]) as json_data:
        s = json.load(json_data)
        fields = jp.match("$.properties[*]", s)
        for f in fields:
            print(f)