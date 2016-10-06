__author__ = 'felix.shaw@tgac.ac.uk - 20/01/2016'

from django.conf.urls import url
from api.handlers import sample, person

urlpatterns = [url(r'person/get/(?P<id>[a-z0-9]+)', person.get, name='person/get'),
               url(r'person/get/', person.get_all, name='person/get/all'),
               url(r'sample/get/(?P<id>[a-z0-9]+)', sample.get, name='sample/get'),
               url(r'sample/get/', sample.get_all, name='sample/get/all'),
               ]
