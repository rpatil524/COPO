from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from django.views.generic import TemplateView
import web.apps.web_copo.views as views

urlpatterns = patterns('',
                       url(r'^$', TemplateView.as_view(template_name="landing_page.html"), name='index'),
                       url(r'^copo/', include('web.apps.web_copo.urls', namespace='copo')),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^rest/', include('web.apps.web_copo.rest_urls', namespace='rest')),
                       url(r'^api/', include('api.urls', namespace='api')),
                       (r'^accounts/', include('allauth.urls')),
                       (r'^accounts/profile/', views.index),
                       )

if settings.DEBUG is False:   #if DEBUG is True it will be served automatically
    urlpatterns += patterns('',
            url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT}),
    )
