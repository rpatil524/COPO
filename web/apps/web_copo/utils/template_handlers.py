# FS - 30/10/2019
from django.http import HttpResponse
from dal.copo_da import MetadataTemplate
from web.apps.web_copo import views
from django.urls import reverse


def new_metadata_template(request):
    template_name = request.GET["template_name"]
    # record = MetadataTemplate()._new(profile_id=request.session["profile_id"], user_id=request.user.id, template_name=template_name)
    d = {"profile_id": request.session["profile_id"], "uid": request.user.id,
                                             "template_name": template_name}
    record = MetadataTemplate().save_record({},**d)
    url = reverse("copo:author_template", args=[str(record["_id"])])
    return HttpResponse(url)
