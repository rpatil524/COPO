__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'

from .annotate_views import search_all, post_annotations, handle_upload
from django.urls import path, re_path
from .handlers import sample, person

app_name = 'api'

urlpatterns = [
    re_path(r'^person/get/(?P<id>[a-z0-9]+)', person.get, name='person/get'),
    path('person/get/', person.get_all, name='person/get/all'),
    re_path(r'sample/get/(?P<id>[A-Za-z0-9]+)', sample.get, name='sample/get'),
    re_path(r'manifest/(?P<manifest_id>[A-Z0-9a-f-]+)', sample.get_for_manifest, name='get_for_manifest'),
    re_path(r'sample/biosample_id/(?P<biosample_id>[A-Z0-9]+)', sample.get_by_biosample_id, name='get_by_biosample_id'),
    re_path(r'sample/copo_id/(?P<copo_id>[A-Za-z0-9]+)', sample.get_by_copo_id, name='get_by_biosample_id'),
    re_path(r'sample/dtol_field/(?P<dtol_field>[A-Za-z0-9-_]+)/(?P<value>[A-Za-z0-9-_]+)', sample.get_by_dtol_field, name='get_by_dtol_field'),
    path('sample/get/', sample.get_all, name='sample/get/all'),
    path('search/', search_all, name='search_all'),
    path('annotations/', post_annotations, name='post_annotations'),
    path('upload_annotation_file/', handle_upload, name='handle_upload'),

]
