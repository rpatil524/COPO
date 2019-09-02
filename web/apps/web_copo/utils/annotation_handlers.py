from dal.copo_da import DataFile, Annotation
import pandas
from django.http import HttpResponse
import json
from bson import json_util

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
    return HttpResponse(json_util.dumps({"data": data, "names": sheet_names}))


def refresh_annotations(request):
    file_id = request.GET["file_id"]
    sheet_name = request.GET["sheet_name"]
    annotations = DataFile().get_file_level_metadata_for_sheet(file_id, sheet_name)
    return HttpResponse(json_util.dumps({"annotations": annotations}))


def refresh_annotations_for_user(request):
    file_id = request.GET["file_id"]
    sheet_name = request.GET["sheet_name"]
    filter = request.GET["filter"]
    uid = request.user.id
    if filter == "all":
        annotations = Annotation().get_terms_for_user_alphabetical(uid)
    elif filter == "by_count":
        annotations = Annotation().get_terms_for_user_ranked(uid)
    elif filter == "by_dataset":
        annotations = Annotation().get_terms_for_user_by_dataset(uid)
    return HttpResponse(json_util.dumps({"annotations": annotations}))


def send_file_annotation(request):
    col_idx = request.POST["col_idx"]
    sheet_name = request.POST["sheet_name"]
    col_header = request.POST["col_header"]
    iri = request.POST["iri"]
    label = request.POST["label"]
    id = request.POST["id"]
    obo_id = request.POST.get("obo_id", "")
    ontology_name = request.POST["ontology_name"]
    ontology_prexfix = request.POST["ontology_prefix"]
    short_form = request.POST["short_form"]
    type = request.POST["type"]
    file_id = request.POST["file_id"]
    file_name = request.POST["file_name"]
    description = request.POST["description"]
    data = {"column_idx": col_idx, "column_header": col_header, "sheet_name": sheet_name, "iri": iri,
            "obo_id": obo_id, "label": label, "id": id, "ontology_name": ontology_name,
            "ontology_prefix": ontology_prexfix,
            "short_form": short_form, "type": type, "description": description, "uid": request.user.id,
            "file_id": file_id, "file_name": file_name}
    if Annotation().add_or_increment_term(data):
        annotations = DataFile().update_file_level_metadata(file_id, data)
    else:
        annotations = {"status": 500, "message": "Could not add annotation"}
    return HttpResponse(json_util.dumps({"annotation": annotations}))


def delete_annotation(request):
    col_idx = request.GET["col_idx"]
    sheet_name = request.GET["sheet_name"]
    file_id = request.GET["file_id"]
    iri = request.GET["iri"]
    uid = request.user.id

    doc = Annotation().decrement_or_delete_annotation(uid, iri)
    doc = DataFile().delete_annotation(col_idx=col_idx, sheet_name=sheet_name, file_id=file_id)
    return HttpResponse("Hello World")

def new_text_annotation(request):
    print(request)
    return HttpResponse("Hello World")