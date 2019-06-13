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


def refresh_annotations(request):
    file_id = request.GET["file_id"]
    sheet_name = request.GET["sheet_name"]
    annotations = DataFile().get_file_level_metadata_for_sheet(file_id, sheet_name)
    return HttpResponse(json.dumps({"annotations": annotations}))


def send_file_annotation(request):
    col_idx = request.POST["col_idx"]
    sheet_name = request.POST["sheet_name"]
    col_header = request.POST["col_header"]
    iri = request.POST["iri"]
    file_id = request.POST["file_id"]
    print(col_idx + " " + sheet_name + " " + col_header + " " + iri + " " + file_id)
    data = {"column_idx": col_idx, "column_header": col_header, "sheet_name": sheet_name, "iri": iri}
    annotations = DataFile().update_file_level_metadata(file_id, data)
    return HttpResponse(json.dumps({"d": "Hello World"}))
