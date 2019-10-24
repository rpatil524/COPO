from dal.copo_da import DataFile, Annotation
import pandas
from django.http import HttpResponse
import json
from bson import json_util
from dal.copo_da import TextAnnotation

# how many rows of each sheet should be shown to the user
truncate_after = 5


def refresh_display(request):

    file_id = request.GET["file_id"]
    file = DataFile().get_record(file_id)
    path = file["file_location"]
    data = list()
    filetype = None
    if file["name"].endswith("csv"):
        filetype = "csv"
    elif file["name"].endswith("txt"):
        filetype = "tab"
    elif file["name"].endswith(("xls", "xlsx")):
        filetype = "xls"
    if "ss_data" in request.session:
        # if data previously loaded then just load from session
        data = json_util.loads(request.session["ss_data"])
        sheet_names = json_util.loads(request.session["ss_sheet_names"])
    else:
        try:
            sheet_names = pandas.ExcelFile(path).sheet_names
        except Exception as e:
            # support CSV here (N.B. CSV does not support multiple sheets)
            sheet_names = [file["name"]]

        # read entire spreadsheet
        if filetype == "xls":
            for name in sheet_names:
                d = pandas.read_excel(path, sheet_name=name, nrows=4).fillna(0)
                out = list()
                out.append(d.columns.tolist())
                out.extend(d.values.tolist())
                data.append(out)
            try:
                request.session["ss_data"] = json_util.dumps(data)
                request.session["ss_sheet_names"] = json_util.dumps(sheet_names)
            except:
                pass
        elif filetype == "csv":
            d = pandas.read_csv(path)
            d = d.fillna('')
            out = list()
            out.append(d.columns.tolist())
            out.extend(d.values.tolist())
            data.append(out)
    return HttpResponse(json_util.dumps({"data": data, "names": sheet_names}))

def refresh_text_annotations(request):
    file_id = request.GET["file_id"]
    annotations = TextAnnotation().get_file_level_metadata_for_pdf(file_id)
    return HttpResponse(json_util.dumps({"annotations": annotations}))

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
    input = json.loads(request.body.decode("utf-8"))
    input["text"] = input["data"]["ontology_prefix"] + " - " + input["data"]["label"]
    id = TextAnnotation().add_term(input)
    annotation = json.dumps({
        "text": input["text"],
        "id": str(id),
        "uri": request.build_absolute_uri('?'),
        "user": request.user.id,
        "ranges": input["ranges"]
    })
    print(annotation)
    return HttpResponse(annotation, content_type="application/json")

def edit_or_delete_text_annotation(request, id):
    if request.method == 'PUT':
        data = json.loads(request.body.decode("utf-8"))
        data["text"] = data["data"]["ontology_prefix"] + " - " + data["data"]["label"]
        result = TextAnnotation().update_text_annotation(id, data)
        if result:
            return HttpResponse(json_util.dumps(data), status=200)
        else:
            return HttpResponse(status=500)
    elif request.method == 'DELETE':
        done = TextAnnotation().remove_text_annotation(id)
        if done:
            return HttpResponse(status=204)
        else:
            return HttpResponse(status=500)

def search_text_annotation(request):
    if "file_id" in request.GET:
        file_id = request.GET["file_id"]
    annotations = TextAnnotation().get_all_for_file_id(file_id)
    out = {"rows": annotations}
    return HttpResponse(json_util.dumps(out), content_type="application/json")