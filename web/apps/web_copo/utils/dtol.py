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
    v = validate(data)
    if v["status"] == 422:
        return HttpResponse(status=v["status"], content=v["msg"])
    elif v["status"] > 499:
        return HttpResponse(status=v["status"], content="Server error. If this persists please contact the administrator")
    elif v["status"] == 200:
        return HttpResponse(status=200)

def validate(data):
    # need to load validation field set
    with open(lookup.WIZARD_FILES["sample_details"]) as json_data:
        fields = ""
        try:
            # get definitive list of DTOL fields
            s = json.load(json_data)
            fields = jp.match('$.properties[?(@.specifications[*] == "dtol" & @.required=="true")].versions', s)
            columns = list(data.columns)
            for item in fields:
                if item[0] not in columns:
                    return {"status": 422, "msg": "Field not found - " + item[0]}
        except:
            return {"status": 500, "msg": "server error"}
        return {"status": 200, "msg": "OK"}

