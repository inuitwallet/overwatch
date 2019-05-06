from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from django.template import Template, Context

from overwatch.models import Bot


class BotListConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()
        async_to_sync(self.channel_layer.group_add)('bot_list', self.channel_name)
        self.get_bots_data()

    def disconnect(self, code):
        self.close()

    def get_bots_data(self):
        for bot in Bot.objects.filter(active=True):
            self.send_bot_data({'bot': bot.pk})

    def send_bot_data(self, event):
        try:
            bot = Bot.objects.get(pk=event['bot'])
        except Bot.DoesNotExist:
            return

        self.send_json(
            {
                'message_type': 'data_update',
                'bot': bot.pk,
                'activity': Template(
                    '{{ heartbeat | timesince }}'
                ).render(
                    Context({'heartbeat': bot.latest_heartbeat})
                ),
                'price': bot.rendered_price(usd=False),
                'price_usd': bot.rendered_price(usd=True),
                'ask_balance': bot.rendered_ask_balance(on_order=True),
                'bid_balance': bot.rendered_bid_balance(on_order=True),
                'profit': bot.rendered_profit()
            }
        )
