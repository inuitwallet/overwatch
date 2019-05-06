from channels.generic.websocket import JsonWebsocketConsumer
from django.template import Template, Context

from overwatch.models import Bot


class BotListConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()
        self.get_bots_data()

    def disconnect(self, code):
        self.close()

    def get_bots_data(self):
        for bot in Bot.objects.all():
            # send the latest heartbeat
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
