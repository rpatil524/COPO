from django.conf.urls import url

import web.apps.web_copo.views as views

urlpatterns = [
    url(r'^$', views.copo_docs, name='copo_docs'),
]
