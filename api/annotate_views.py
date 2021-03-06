import datetime
import json
import os
from os import path

import bson.json_util as j
import pexpect
from bson import ObjectId
from django.conf import settings
from django.http import HttpResponse
from numpy import NaN
from pandas import read_excel, read_csv
from xlrd import XLRDError

from dal.copo_da import Annotation
from dal.mongo_util import change_mongo_id_format_to_standard, convert_text


def post_annotations(request):
    document_name = request.COOKIES.get('document_name')
    document_id = request.COOKIES.get('document_id')
    data = j.loads(request.body.decode('utf-8'))
    text = data.pop('text')

    tmp = text.split(':-:')

    short = str.strip(tmp[0])
    if len(tmp) > 1:
        ref = str.strip(tmp[1])
    else:
        ref = ''
    data['term_accession'] = ref
    data["annotation_value"] = short
    data["term_source"] = 'xxx'

    if 'quote' in data:
        quote = data.pop('quote')
        data['text'] = quote

    if 'id' in data:
        # EDIT ANNOTATION
        annotation_id = data.pop('id')
        r = Annotation().update_annotation(document_id, annotation_id, data)
    else:
        # CREATE ANNOTATION
        r = Annotation().add_to_annotation(document_id, data)

    r['id'] = r.pop('_id')
    r['text'] = r['annotation_value'] + ' :-: ' + r['term_accession']

    return HttpResponse(j.dumps(r))


def search_all(request):
    document_id = ObjectId(request.COOKIES.get('document_id'))
    data = Annotation().get_annotations_for_page(document_id)
    ant = change_mongo_id_format_to_standard(data['annotation'])
    ant = convert_text(ant)
    d = {
        "total": len(data),
        "rows": ant,
        "annotation_id": data["_id"]
    }
    return HttpResponse(j.dumps(d))


def handle_upload(request):
    f = request.FILES['file']

    # TODO - this should be changed to a uuid

    # save file to media location
    save_name = path.join(settings.MEDIA_ROOT, "generic_annotations", f._name)
    # check if path exists
    if not path.exists(path.join(settings.MEDIA_ROOT, "generic_annotations")):
        os.makedirs(path.join(settings.MEDIA_ROOT, "generic_annotations"))

    with open(save_name, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    f.seek(0)

    file_name = os.path.splitext(f.name)[0]
    file_type = request.POST['file_type']
    skip_rows = request.POST['skip_rows']
    if file_type == "Spreadsheet":
        # load spreadsheet data and return to backend
        try:
            s = read_excel(f, skiprows=int(skip_rows))
        except XLRDError as e:
            s = read_csv(f, skiprows=(int(skip_rows)))

        s = s.replace(NaN, "")
        for column in s.iteritems():
            # check data type
            dt = column[1].dtype
            if str(dt).startswith('datetime'):
                # we are dealing with date objects
                s[column[0]] = s[column[0]].astype(str)

        raw = list()
        raw.append(s.columns.tolist())
        raw.extend(s.values.tolist())
        jraw = j.dumps(raw)
        raw = jraw

    elif file_type == "PDF Document":

        cmd = 'pdftotext -htmlmeta ' + save_name
        resp = pexpect.run(cmd)
        # now open the resulting file, parse and send to frontend
        file_name = os.path.splitext(save_name)[0]
        html_name = file_name + '.html'
        with open(html_name, "r", encoding='utf-8', errors='ignore') as p:
            raw = p.read()
    out = dict()

    if not Annotation().annotation_exists(file_name, str(request.user.id)):
        out['raw'] = raw
        out['type'] = file_type
        out['document_name'] = file_name
        out['profile_id'] = request.session['profile_id']
        out['deleted'] = '0'
        out['date_created'] = datetime.datetime.now()
        out['uid'] = str(request.user.id)
        out['file_location'] = save_name
        out = Annotation(request.session['profile_id']).save_record({}, **out)

    else:
        out = Annotation().get_annotation_by_name(file_name, request.user.id)

    try:
        os.remove(save_name)
        os.remove(html_name)
    except:
        print('cannot find temp file to delete.....no worries')

    return HttpResponse(j.dumps(out))

def save_ss_annotation(request):
    document_id = request.POST.get('document_id')
    column_header = request.POST.get('column_header')
    annotation_value = request.POST.get('annotation_value')
    term_source = request.POST.get('term_source')
    term_accession = request.POST.get('term_accession')

    fields = {'column_header': column_header, 'annotation_value': annotation_value, 'term_source': term_source, 'term_accession': term_accession}
    annotation_id = Annotation().add_to_annotation(id=document_id, fields=fields)['_id']

    return HttpResponse(annotation_id)

def delete_ss_annotation(request):
    # DELETE ANNOTATION
    annotation_id = request.POST.get('annotation_id')
    document_id = request.POST.get('document_id')
    r = Annotation().update_annotation(document_id, annotation_id, {}, True)
    out = dict()
    if r == '':
        out['deleted'] = True

    else:
        out['deleted'] = False

    return HttpResponse(json.dumps(out))