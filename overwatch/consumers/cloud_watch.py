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


class CloudWatchLogsConsumer(SyncConsumer):
    def get_cloudwatch_logs(self, event):
        try:
            bot = Bot.objects.get(pk=event['bot_pk'])
        except Bot.DoesNotExist:
            return

        if not bot.logs_group:
            return

        print('getting logs for Bot {}'.format(bot))

        async_to_sync(get_channel_layer().group_send)(
            'cloudwatch_logs_{}'.format(bot.pk),
            {
                'type': 'clear',
            }
        )

        logs_client = boto3.client(
            'logs',
            region_name=bot.aws_region,
            aws_access_key_id=bot.aws_access_key,
            aws_secret_access_key=bot.aws_secret_key,
        )

        streams = logs_client.describe_log_streams(
            logGroupName=bot.logs_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        ).get('logStreams', [])

        if not streams:
            return

        latest_stream = streams[0].get('logStreamName')

        self.stream_events(bot.pk, logs_client, bot.logs_group, latest_stream)

    def stream_events(self, bot_pk, client, group, stream, next_token=None):
        if next_token:
            events = client.get_log_events(
                logGroupName=group,
                logStreamName=stream,
                startFromHead=False,
                limit=50,
                nextToken=next_token
            )
        else:
            events = client.get_log_events(
                logGroupName=group,
                logStreamName=stream,
                startFromHead=False,
                limit=50
            )

        if not events.get('events'):
            return

        self.send_events(bot_pk, events)

        return self.stream_events(bot_pk, client, group, stream, events.get('nextForwardToken'))

    @staticmethod
    def send_events(bot_pk, events):
        for event in events.get('events', []):
            message = event.get('message').strip()

            if not message:
                continue

            async_to_sync(get_channel_layer().group_send)(
                'cloudwatch_logs_{}'.format(bot_pk),
                {
                    'type': 'send.log.line',
                    'time': datetime.datetime.utcfromtimestamp(
                        int(event.get('timestamp') / 1000)
                    ).strftime('%Y-%m-%d %H:%M:%S'),
                    'message': str(message)
                }
            )
