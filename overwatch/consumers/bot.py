import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.template.loader import render_to_string

from overwatch.models import Bot, BotPlacedOrder, BotTrade


class BotConsumer(JsonWebsocketConsumer):
    bot = None

    def connect(self):
        """
        Add channel to the necessary groups. Initiate data scan
        """
        # get the bot from the websocket url
        try:
            self.bot = Bot.objects.get(
                pk=self.scope['url_route']['kwargs']['pk']
            )
        except Bot.DoesNotExist:
            self.close()
            return

        # accept the websocket connection
        self.accept()

        # add the channel to the necessary groups
        async_to_sync(self.channel_layer.group_add)('bot_{}'.format(self.bot.pk), self.channel_name)
        async_to_sync(self.channel_layer.group_add)('cloudwatch_logs_{}'.format(self.bot.pk), self.channel_name)

        # clear the bot data
        self.clear({})
        # clear the log data
        self.logs_clear({})

        # get the bot price and order data
        self.get_heart_beats({})
        self.get_price_info({})
        self.get_balance_info({})
        self.get_placed_orders({})
        self.get_trades({})

        # get the latest cloudwatch logs
        async_to_sync(get_channel_layer().send)(
            'cloudwatch-logs',
            {
                "type": "get.cloudwatch.logs",
                "bot_pk": self.bot.pk
            },
        )

    def disconnect(self, close_code):
        """
        disconnect from the websocket so remove from groups
        """
        async_to_sync(self.channel_layer.group_discard)('bot_{}'.format(self.bot.pk), self.channel_name)
        async_to_sync(self.channel_layer.group_discard)('cloudwatch_logs_{}'.format(self.bot.pk), self.channel_name)
        self.close()

    def clear(self, event):
        """
        Instruct the javascript on the bot_detail page to clear the bot data holders
        """
        self.send(
            json.dumps(
                {
                    'message_type': 'bot_clear'
                }
            )
        )

    def logs_clear(self, event):
        """
        Instruct javascript on bot_detail page to clear the cloudwatch_logs holder
        """
        self.send(
            json.dumps(
                {
                    'message_type': 'cloudwatch_logs_clear'
                }
            )
        )

    def get_heart_beats(self, event):
        """
        Send the 15 latest heartbeats to the front end
        """
        # clear the heartbeat container
        self.send(json.dumps({'message_type': 'heartbeat_clear'}))

        # get the latest 15 heartbeats and send them to the javascript on the bot_detail page
        for heartbeat in sorted(self.bot.botheartbeat_set.all()[:15], key=lambda x: x.time):
            self.send(
                json.dumps(
                    {
                        'message_type': 'heartbeat',
                        'heartbeat': render_to_string('overwatch/fragments/heartbeat.html', {'heartbeat': heartbeat})
                    }
                )
            )

    def get_price_info(self, event):
        """
        calculate latest price infor and send to front end
        """
        self.send(
            json.dumps(
                {
                    'message_type': 'price_info',
                    'price_peg': self.bot.rendered_price(usd=True),
                    'price': self.bot.rendered_price(usd=False),
                    'price_sparkline': self.bot.price_sparkline(),
                    'bid_price_peg': self.bot.rendered_bid_price(usd=True),
                    'bid_price': self.bot.rendered_bid_price(usd=False),
                    'ask_price_peg': self.bot.rendered_ask_price(usd=True),
                    'ask_price': self.bot.rendered_ask_price(usd=False)
                }
            )
        )

    def get_balance_info(self, event):
        """
        get the latest balance info and send it to the front end
        """
        self.send(
            json.dumps(
                {
                    'message_type': 'balance_info',
                    'bid_balance_peg': '{} / {}'.format(
                        self.bot.rendered_bid_balance(on_order=True, usd=True),
                        self.bot.rendered_bid_balance(on_order=False, usd=True)
                    ),
                    'bid_balance': '({} / {})'.format(
                        self.bot.rendered_bid_balance(on_order=True, usd=False),
                        self.bot.rendered_bid_balance(on_order=False, usd=False)
                    ),
                    'ask_balance_peg': '{} / {}'.format(
                        self.bot.rendered_ask_balance(on_order=True, usd=True),
                        self.bot.rendered_ask_balance(on_order=False, usd=True)
                    ),
                    'ask_balance': '({} / {})'.format(
                        self.bot.rendered_ask_balance(on_order=True, usd=False),
                        self.bot.rendered_ask_balance(on_order=False, usd=False)
                    )
                }
            )
        )
        self.send(
            json.dumps(
                {
                    'message_type': 'balances_chart',
                    'chart': '<embed type="image/svg+xml" src="{}" />'.format(
                        self.bot.get_balances_chart()
                    )
                }
            )
        )

    def send_log_line(self, event):
        """
        send a single cloudwatch log line to the front end
        """
        self.send(
            json.dumps(
                {
                    'message_type': 'cloudwatch_logs_add_line',
                    'time': event.get('time'),
                    'message': event.get('message')
                }
            )
        )

    def get_placed_orders(self, event):
        """
        send placed_order table entries or the data url containing the placed_orders_chart to the front end
        """
        # this send just redraws the datatable
        self.send(
            json.dumps(
                {
                    'message_type': 'placed_order',
                }
            )
        )
        # this send pushes the chart data url
        self.send(
            json.dumps(
                {
                    'message_type': 'placed_order_chart',
                    'chart': '<embed type="image/svg+xml" src="{}"/>'.format(
                        self.bot.get_placed_orders_chart(hours=event.get('hours', 48))
                    )
                }
            )
        )

    def get_trades(self, event):
        """
        send trade table entries or the data url containing the trades_chart to the front end
        """
        # this send just redraws the datatable
        self.send(
            json.dumps(
                {
                    'message_type': 'trade',
                }
            )
        )
        # this send pushes the chart data url
        self.send(
            json.dumps(
                {
                    'message_type': 'trades_chart',
                    'chart': '<embed type="image/svg+xml" src="{}" />'.format(
                        self.bot.get_trades_chart(days=event.get('days'))
                    )
                }
            )
        )

    def get_errors(self, event):
        """
        send the message to redraw the errors table
        """
        self.send(
            json.dumps(
                {
                    'message_type': 'bot_error'
                }
            )
        )
