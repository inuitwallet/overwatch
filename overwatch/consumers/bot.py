import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.template.loader import render_to_string

from overwatch.models import Bot


class BotConsumer(JsonWebsocketConsumer):
    bot = None

    def connect(self):
        try:
            self.bot = Bot.objects.get(
                pk=self.scope['url_route']['kwargs']['pk']
            )
        except Bot.DoesNotExist:
            self.close()
            return

        self.accept()

        async_to_sync(self.channel_layer.group_add)('bot_{}'.format(self.bot.pk), self.channel_name)

        self.clear({})

        self.get_heart_beats({})
        self.get_price_info({})
        self.get_balance_info({})

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)('bot_{}'.format(self.bot.pk), self.channel_name)
        self.close()

    def clear(self, event):
        self.send(
            json.dumps(
                {
                    'message_type': 'bot_clear'
                }
            )
        )

    def get_heart_beats(self, event):
        self.send(json.dumps({'message_type': 'heartbeat_clear'}))

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
