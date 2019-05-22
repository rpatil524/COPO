from dal.copo_da import DataFile
import pandas
from django.http import HttpResponse
import json

def refresh_display(request):
    file_id = request.GET["file_id"]
    file = DataFile().get_record(file_id)
    path = file["file_location"]
    data = list()
    x1 = pandas.ExcelFile(path)
    sheet_names = x1.sheet_names
    for name in sheet_names:
        data.append(x1.parse(name).to_csv())
    return HttpResponse(json.dumps(data))