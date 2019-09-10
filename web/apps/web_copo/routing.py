from django.urls import path

from . import consumers


websocket_urlpatterns = [
    path('ws/chat_room/<str:room_name>/', consumers.ChatConsumer),
]
