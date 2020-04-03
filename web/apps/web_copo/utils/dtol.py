# Created by fshaw at 03/04/2020
from django.http import HttpResponse
import pandas


def loadCsv(file):
    return HttpResponse()


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