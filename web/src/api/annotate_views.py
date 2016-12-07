from django.http import HttpResponse
import bson.json_util as j
from dal.copo_da import Annotation
from dal.mongo_util import change_mongo_id_format_to_standard, convert_text
from django.conf import settings
import os
import pexpect
import datetime


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
    data['@id'] = ref
    data["shortform"] = short


    if 'quote' in data:
        quote = data.pop('quote')
        data['text'] = quote

    if request.method == "DELETE":
        # DELETE ANNOTATION
        annotation_id = data.pop('id')
        r = Annotation().update_annotation(document_id, annotation_id, {}, True)
        response = HttpResponse('')
        response.content = ''
        response.status_code = 204
        return response
    elif 'id' in data:
        # EDIT ANNOTATION
        annotation_id = data.pop('id')
        r = Annotation().update_annotation(document_id, annotation_id, data)
    else:
        # CREATE ANNOTATION
        r = Annotation().add_to_annotation(document_id, data)

    r['id'] = r.pop('_id')
    r['text'] = r['shortform'] + ' :-: ' + r['@id']

    return HttpResponse(j.dumps(r))



def search_all(request):
    document_id = request.COOKIES.get('document_id')
    print(document_id)
    data = Annotation().get_annotations_for_page(document_id)
    data = change_mongo_id_format_to_standard(data)
    data = convert_text(data)
    d = {
        "total": len(data),
        "rows": data
    }
    return HttpResponse(j.dumps(d))


def handle_upload(request):

    f = request.FILES['file']
    # TODO - this should be changed to a uuid
    fname = os.path.join(settings.MEDIA_ROOT, f.name)
    with open(fname, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

    cmd = 'pdftotext -htmlmeta ' + fname
    resp = pexpect.run(cmd)
    # now open the resulting file, parse and send to frontend
    file_name = os.path.splitext(fname)[0]
    html_name = file_name + '.html'
    with open(html_name) as p:
        html = p.read()
    out = dict()

    file_name = os.path.splitext(f.name)[0]
    if not Annotation().annotation_exists(file_name, str(request.user.id)):
        out['html'] = html
        out['document_name'] = file_name
        out['profile_id'] = request.session['profile_id']
        out['deleted'] = '0'
        out['date_created'] = datetime.datetime.now()
        out['uid'] = str(request.user.id)
        out = Annotation(request.session['profile_id']).save_record({}, **out)

    else:
        out = Annotation().get_annotation_by_name(file_name, request.user.id)





    return HttpResponse(j.dumps(out))
