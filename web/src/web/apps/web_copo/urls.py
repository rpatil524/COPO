from django.conf.urls import patterns, url
from . import views
from web.apps.web_copo.utils import ajax_handlers


urlpatterns = patterns('web.apps.web_copo.views',
                       url(r'^$', 'index', name='index'),
                       url(r'^test_submission', 'test_submission', name='test_submission'),
                       url(r'^test', 'test', name='test'),
                       url(r'^logout/', 'copo_logout', name='logout'),
                       url(r'^register/', 'copo_register', name='register'),
                       url(r'^profile/update_counts/', 'get_profile_counts', name='update_counts'),
                       url(r'^view_orcid_profile/$', 'view_orcid_profile', name='view_orcid_profile'),
                       url(r'^error/', views.goto_error, name='error_page'),
                       url(r'^register_to_irods/$', 'register_to_irods', name='register_to_irods'),
                       # urls from October 2015 refactor below
                       url(r'^copo_profile/(?P<profile_id>[a-z0-9]+)/view', views.view_copo_profile,
                           name='view_copo_profile'),
                       url(r'^copo_publications/(?P<profile_id>[a-z0-9]+)/view', 'copo_publications',
                           name='copo_publications'),
                       url(r'^copo_data/(?P<profile_id>[a-z0-9]+)/view', 'copo_data',
                           name='copo_data'),
                       url(r'^copo_samples/(?P<profile_id>[a-z0-9]+)/view', 'copo_samples',
                           name='copo_samples'),
                       url(r'^copo_submissions/(?P<profile_id>[a-z0-9]+)/view', 'copo_submissions',
                           name='copo_submissions'),
                       url(r'^copo_people/(?P<profile_id>[a-z0-9]+)/view', 'copo_people',
                           name='copo_people'),
                       url(r'^get_source_count/$', ajax_handlers.get_source_count,
                           name="get_source_count"),
                       url(r'^ajax_search_ontology/(?P<ontology_names>[a-z0-9]+(,[a-z0-9]+)*)/$',
                           ajax_handlers.search_ontology_ebi, name='ajax_search_ontology'),
                       url(r'^ajax_search_ontology_test/$', ajax_handlers.test_ontology, name='test_ontology'),
                       url(r'^copo_forms/$', views.copo_forms, name="copo_forms"),
                       url(r'^copo_visualize/$', views.copo_visualize, name="copo_visualize"),
                       url(r'^authenticate_figshare/$', 'authenticate_figshare', name='authenticate_figshare'),

                       )

