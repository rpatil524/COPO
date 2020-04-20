from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json


class SubmissionConsumer(WebsocketConsumer):
    def connect(self):
        self.profile_id = self.scope['url_route']['kwargs']['profile_id']
        self.group_name = 'submission_status_%s' % self.profile_id

        # join group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # leave group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    # receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)

        # send message to group
        async_to_sync(self.channel_layer.group_send)(
            self.group_name,
            {
                'type': text_data_json['type'],
                'message': text_data_json['message']
            }
        )

    # receive message from group
    def submission_status(self, event):
        # send message to WebSocket
        self.send(text_data=json.dumps(event))

    # receive message from group
    def file_transfer_status(self, event):
        # send message to WebSocket
        self.send(text_data=json.dumps(event))
