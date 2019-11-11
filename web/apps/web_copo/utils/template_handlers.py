# FS - 30/10/2019
from django.http import HttpResponse
from dal.copo_da import MetadataTemplate
from web.apps.web_copo import views
from django.urls import reverse
from bson import json_util
from dal.copo_da import MetadataTemplate


def new_metadata_template(request):
    template_name = request.GET["template_name"]
    # record = MetadataTemplate()._new(profile_id=request.session["profile_id"], user_id=request.user.id, template_name=template_name)
    d = {"profile_id": request.session["profile_id"], "uid": request.user.id,
         "template_name": template_name}
    record = MetadataTemplate().save_record({}, **d)
    url = reverse("copo:author_template", args=[str(record["_id"])])
    return HttpResponse(url)


def update_metadata_template_name(request):
    template_name = request.GET["template_name"]
    template_id = request.GET["template_id"]
    new_name = MetadataTemplate().update_name(template_name=template_name, template_id=template_id)["template_name"]
    return HttpResponse(new_name)


def update_template(request):
    data = json_util.loads(request.POST["data"])
    template_id = request.POST["template_id"]
    record = MetadataTemplate().update_template(template_id=template_id, data=data)
    if (record):
        return HttpResponse(json_util.dumps({"data": data, "template_id": template_id}))
    else:
        return HttpResponse(status=500)
