import json

from channels.generic.websocket import JsonWebsocketConsumer

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
        self.send(json.dumps({'message_type': 'clear'}))
        self.get_price_info()
        self.get_balance_info()

    def receive(self):
        pass

    def disconnect(self, close_code):
        self.close()

    def get_price_info(self):
        self.send(
            json.dumps(
                {
                    'message_type': 'price_info',
                    'price_peg': self.bot.rendered_price(peg=True),
                    'price': self.bot.rendered_price(peg=False),
                    'bid_price_peg': self.bot.rendered_bid_price(peg=True),
                    'bid_price': self.bot.rendered_bid_price(peg=False),
                    'ask_price_peg': self.bot.rendered_ask_price(peg=True),
                    'ask_price': self.bot.rendered_ask_price(peg=False)
                }
            )
        )

    def get_balance_info(self):
        self.send(
            json.dumps(
                {
                    'message_type': 'balance_info',
                    'bid_balance_peg': '{} / {}'.format(
                        self.bot.rendered_bid_balance(on_order=True, peg=True),
                        self.bot.rendered_bid_balance(on_order=False, peg=True)
                    ),
                    'bid_balance': '({} / {})'.format(
                        self.bot.rendered_bid_balance(on_order=True, peg=False),
                        self.bot.rendered_bid_balance(on_order=False, peg=False)
                    ),
                    'ask_balance_peg': '{} / {}'.format(
                        self.bot.rendered_ask_balance(on_order=True, peg=True),
                        self.bot.rendered_ask_balance(on_order=False, peg=True)
                    ),
                    'ask_balance': '({} / {})'.format(
                        self.bot.rendered_ask_balance(on_order=True, peg=False),
                        self.bot.rendered_ask_balance(on_order=False, peg=False)
                    )
                }
            )
        )