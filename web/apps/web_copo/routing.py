from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/submission_status/<str:profile_id>/', consumers.SubmissionConsumer),
    path('ws/sample_status/<str:profile_id>', consumers.SampleConsumer)
]
