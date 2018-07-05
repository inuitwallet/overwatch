import datetime
import json
import time
from threading import Thread

import boto3
from channels.generic.websocket import WebsocketConsumer
from django.conf import settings

from oversight.models import Bot


class ChatConsumer(WebsocketConsumer):

    collect_logs = True

    def connect(self):
        try:
            bot = Bot.objects.get(
                pk=self.scope['url_route']['kwargs']['pk']
            )
        except Bot.DoesNotExist:
            self.close()
            return

        if not bot.logs_group:
            self.close()
            return

        self.accept()
        self.collect_logs = True

        self.send(json.dumps({'message_type': 'clear'}))

        logs_client = boto3.client(
            'logs',
            region_name='eu-west-1',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        streams = logs_client.describe_log_streams(
            logGroupName=bot.logs_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        ).get('logStreams', [])

        if not streams:
            self.close()
            return None

        latest_stream = streams[0].get('logStreamName')

        Thread(
            target=self.stream_events,
            kwargs={
                'client': logs_client,
                'group': bot.logs_group,
                'stream': latest_stream
            }
        ).start()

    def disconnect(self, close_code):
        self.collect_logs = False

    def stream_events(self, client, group, stream):
        events = client.get_log_events(
            logGroupName=group,
            logStreamName=stream,
            startFromHead=False,
            limit=50
        )

        self.send_events(events)

        while 'nextForwardToken' in events:
            events = client.get_log_events(
                logGroupName=group,
                logStreamName=stream,
                startFromHead=True,
                nextToken=events.get('nextForwardToken')
            )

            self.send_events(events)
            time.sleep(1)

        if not self.collect_logs:
            return

    def send_events(self, events):
        for event in events.get('events', []):
            message = event.get('message').strip()

            if not message:
                continue

            self.send(
                json.dumps({
                    'message_type': 'log_line',
                    'time': datetime.datetime.utcfromtimestamp(
                        int(event.get('timestamp') / 1000)
                    ).strftime('%Y-%m-%d %H:%M:%S'),
                    'message': message
                })
            )

            time.sleep(0.05)

