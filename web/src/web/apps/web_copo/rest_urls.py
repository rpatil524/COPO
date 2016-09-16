from web.apps.chunked_upload.views import *
from django.conf.urls import patterns, url

import api.handlers.general as api
import web.apps.web_copo.repos.figshare as figshare
import web.apps.web_copo.rest.EnaRest as rest
import web.apps.web_copo.views as views
import web.apps.web_copo.wizard_views as wizard
import submission.submissionDelegator as submit
import web.apps.web_copo.utils.ajax_handlers as ajax


urlpatterns = patterns('',
                       url(r'^ena_sample_form/', rest.get_ena_sample_controls, name='get_ena_sample_controls'),
                       url(r'^ena_new_study/', rest.save_ena_study, name='save_ena_study'),
                       url(r'^ena_new_sample/', rest.save_ena_sample_callback, name='save_ena_sample'),
                       url(r'^populate_samples_form/', rest.populate_samples_form, name='populate_samples_form'),
                       url(r'^get_sample_html/(?P<sample_id>\d+)', rest.get_sample_html, name='get_sample_html'),
                       url(r'^data_wiz/', wizard.data_wiz, name='data_wiz'),
                       url(r'^get_sample_html/', rest.get_sample_html, name='get_sample_html_param'),
                       url(r'^populate_data_dropdowns/', rest.populate_data_dropdowns, name='populate_data_dropdowns'),
                       url(r'^get_instrument_models/', rest.get_instrument_models, name='get_instrument_models'),
                       url(r'^get_experimental_samples/', rest.get_experimental_samples,
                           name='get_experimental_samples'),
                       url(r'^receive_data_file/', rest.receive_data_file, name='receive_data_file'),
                       url(r'^receive_data_file_chunked/', ChunkedUploadView.as_view(), name='receive_data_file'),
                       url(r'^complete_upload/', ChunkedUploadCompleteView.as_view(), name='complete_data_file'),
                       url(r'^hash_upload/', rest.hash_upload, name='hash_upload'),
                       url(r'^inspect_file/', rest.inspect_file, name='inspect_file'),
                       url(r'^zip_file/', rest.zip_file, name='zip_file'),
                       url(r'^save_experiment/', rest.save_experiment, name='save_experiment'),
                       url(r'^get_experiment_table_data/', rest.get_experiment_table_data,
                           name='get_experiment_table_data'),
                       url(r'^get_experiment_modal_data/', rest.populate_exp_modal, name='populate_exp_modal'),
                       url(r'^delete_file/', rest.delete_file, name='delete_file'),
                       url(r'^check_figshare_credentials/', figshare.check_figshare_credentials,
                           name='check_figshare_credentials'),
                       url(r'^set_figshare_credentials/', figshare.set_figshare_credentials,
                           name='set_figshare_credentials'),
                       url(r'^small_file_upload/', api.upload_to_figshare_profile, name='receive_data_file'),
                       url(r'^forward_to_figshare/', wizard.forward_to_figshare, name='forward_to_figshare'),
                       url(r'^get_upload_information/', ajax.get_upload_information, name='get_upload_information'),
                       url(r'^submit_to_repo/', submit.delegate_submission, name='delegate_submission'),
                       url(r'^test_submission', views.test_submission, name='test_ena_submission'),
                       )
