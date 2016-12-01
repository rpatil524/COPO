__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'
from .annotate_views import search_all, post_annotations, handle_upload
from django.conf.urls import url
from .handlers import sample, person

urlpatterns = [url(r'person/get/(?P<id>[a-z0-9]+)', person.get, name='person/get'),
               url(r'person/get/', person.get_all, name='person/get/all'),
               url(r'sample/get/(?P<id>[a-z0-9]+)', sample.get, name='sample/get'),
               url(r'sample/get/', sample.get_all, name='sample/get/all'),
               url(r'search', search_all, name='search_all'),
               url(r'annotations', post_annotations, name='post_annotations'),
               url(r'^upload_annotation_file/$', handle_upload, name='handle_upload'),

               ]
