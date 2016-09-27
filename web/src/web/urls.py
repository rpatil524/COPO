from django.conf.urls import url, include
from django.contrib import admin
from django.conf import settings
from django.views.generic import TemplateView
import web.apps.web_copo.views as views
from  django.views.static import serve

urlpatterns = [url(r'^copo/', include('web.apps.web_copo.urls', namespace='copo')),
               url(r'^admin/', include(admin.site.urls)),
               url(r'^rest/', include('web.apps.web_copo.rest_urls', namespace='rest')),
               url(r'^api/', include('api.urls', namespace='api')),
               url(r'^accounts/', include('allauth.urls')),
               url(r'^accounts/profile/', views.index),
               url(r'^$', TemplateView.as_view(template_name="landing_page.html"), name='index')
               ]

if settings.DEBUG is False:  # if DEBUG is True it will be served automatically
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]
