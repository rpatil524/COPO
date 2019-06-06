from dal.copo_da import DataFile
import pandas
from django.http import HttpResponse
import json

# how many rows of each sheet should be shown to the user
truncate_after = 5


def refresh_display(request):
    file_id = request.GET["file_id"]
    file = DataFile().get_record(file_id)
    path = file["file_location"]
    data = list()
    x1 = pandas.ExcelFile(path)
    sheet_names = x1.sheet_names
    for name in sheet_names:
        d = pandas.read_excel(path, name).fillna(0)
        out = list()
        out.append(d.columns.tolist())
        out.extend(d.values[0:5].tolist())

        data.append(out)
    return HttpResponse(json.dumps({"data": data, "names": sheet_names}))
