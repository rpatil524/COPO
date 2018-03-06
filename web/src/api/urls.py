__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'
from .annotate_views import search_all, post_annotations, handle_upload
from django.urls import path, re_path
from .handlers import sample, person

app_name = 'api'

urlpatterns = [
    re_path(r'^person/get/(?P<id>[a-z0-9]+)', person.get, name='person/get'),
    path('person/get/', person.get_all, name='person/get/all'),
    re_path(r'^sample/get/(?P<id>[a-z0-9]+)', sample.get, name='sample/get'),
    path('sample/get/', sample.get_all, name='sample/get/all'),
    path('search/', search_all, name='search_all'),
    path('annotations/', post_annotations, name='post_annotations'),
    path('upload_annotation_file/', handle_upload, name='handle_upload'),
]
