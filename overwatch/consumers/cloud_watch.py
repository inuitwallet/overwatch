import datetime
import json

import boto3
from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer

from overwatch.models import Bot


class CloudWatchConsumer(WebsocketConsumer):
    group_name = None

    def connect(self):
        """
        Connect the websocket and set up the boto3 collection objects
        :return:
        """
        self.accept()
        self.clear({})

        self.group_name = 'cloudwatch_logs_{}'.format(self.scope['url_route']['kwargs']['pk'])
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)
        self.close()

    def send_log_line(self, event):
        self.send(
            json.dumps(
                {
                    'message_type': 'cloudwatch_logs_add_line',
                    'time': event.get('time'),
                    'message': event.get('message')
                }
            )
        )

    def clear(self, event):
        self.send(
            json.dumps(
                {
                    'message_type': 'cloudwatch_logs_clear'
                }
            )
        )
