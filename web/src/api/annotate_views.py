from django.http import HttpResponse
import bson.json_util as j
from dal.copo_da import Annotation
from dal.mongo_util import change_mongo_id_format_to_standard, convert_text
from django.conf import settings
import os
import pexpect


def post_annotations(request):
    document_name = request.COOKIES.get('document_name')
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


    data['uid'] = str(request.user.id)
    data['document_name'] = document_name
    data['deleted'] = 'false'
    if 'id' in data:
        data['target_id'] = data.pop('id')

    if request.method == "DELETE":
        data['deleted'] = 'true'
        if Annotation().save_record({}, **data):
            response = HttpResponse('')
            response.content = ''
            response.status_code = 204

    r = Annotation().save_record({}, **data)
    r['id'] = r.pop('_id')
    r['text'] = r['shortform'] + ' :-: ' + r['@id']

    return HttpResponse(j.dumps(r))



def search_all(request):
    document_name = request.COOKIES.get('document_name')
    data = Annotation().get_annotations_for_page(document_name, request)
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
    print(cmd)
    resp = pexpect.run(cmd)
    print(resp)
    # now open the resulting file, parse and send to frontend
    file_name = os.path.splitext(fname)[0]
    html_name = file_name + '.html'
    with open(html_name) as p:
        html = p.read()

    out = dict()
    out['html'] = html
    out['doc_name'] = os.path.splitext(f.name)[0]

    return HttpResponse(j.dumps(out))


