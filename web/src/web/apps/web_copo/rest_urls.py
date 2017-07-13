from django.conf.urls import url

import api.handlers.general as api
import web.apps.web_copo.repos.figshare as figshare
import web.apps.web_copo.rest.EnaRest as rest
import web.apps.web_copo.views as views
import api.annotate_views as a_views
import web.apps.web_copo.wizard_views as wizard
import submission.submissionDelegator as submit
import web.apps.web_copo.utils.ajax_handlers as ajax
from web.apps.web_copo.rest.EnaRest import CopoChunkedUploadCompleteView, CopoChunkedUploadView

urlpatterns = [
    url(r'^data_wiz/', wizard.data_wiz, name='data_wiz'),
    url(r'^sample_wiz/', wizard.sample_wiz, name='sample_wiz'),
    url(r'^receive_data_file/', rest.receive_data_file, name='receive_data_file'),
    url(r'^receive_data_file_chunked/', CopoChunkedUploadView.as_view(), name='receive_data_file'),
    url(r'^complete_upload/', CopoChunkedUploadCompleteView.as_view(), name='complete_data_file'),
    url(r'^hash_upload/', rest.hash_upload, name='hash_upload'),
    url(r'^inspect_file/', rest.inspect_file, name='inspect_file'),
    url(r'^zip_file/', rest.zip_file, name='zip_file'),
    url(r'^check_figshare_credentials/', figshare.check_figshare_credentials, name='check_figshare_credentials'),
    url(r'^set_figshare_credentials/', figshare.set_figshare_credentials, name='set_figshare_credentials'),
    url(r'^small_file_upload/', api.upload_to_figshare_profile, name='receive_data_file'),
    url(r'^forward_to_figshare/', wizard.forward_to_figshare, name='forward_to_figshare'),
    url(r'^get_upload_information/', ajax.get_upload_information, name='get_upload_information'),
    url(r'^submit_to_repo/', submit.delegate_submission, name='delegate_submission'),
    url(r'^test_submission/', views.test_submission, name='test_ena_submission'),
    url(r'^resume_chunked/', rest.resume_chunked, name='resume_chunked'),
    url(r'^get_partial_uploads/', rest.get_partial_uploads, name='get_partial_uploads'),
    url(r'^get_excel_data/', ajax.get_excel_data, name='get_excel_data'),
    url(r'^save_ss_annotation', a_views.save_ss_annotation, name='save_ss_annotation'),
    url(r'^delete_ss_annotation/', a_views.delete_ss_annotation, name='delete_ss_annotation'),
    url(r'^copo_get_submission_table_data/', views.copo_get_submission_table_data, name='get_submissions'),
    url(r'^get_accession_data/', ajax.get_accession_data, name='get_accession_data'),
    url(r'^set_session_variable/', ajax.set_session_variable, name='set_session_variable')
]
