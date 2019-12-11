import ccxt
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from overwatch.models import Bot, Exchange


class BotFormConsumer(JsonWebsocketConsumer):
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
        async_to_sync(self.channel_layer.group_add)('bot_form_{}'.format(self.bot.pk), self.channel_name)

    def disconnect(self, close_code):
        """
        disconnect from the websocket so remove from groups
        """
        async_to_sync(self.channel_layer.group_discard)('bot__form_{}'.format(self.bot.pk), self.channel_name)
        self.close()

    def receive_json(self, content, **kwargs):
        message_type = content.get('message_type')

        if message_type == 'get_markets':
            try:
                exchange_account = Exchange.objects.get(pk=content.get('exchange_account_pk'))
            except Exchange.DoesNotExist:
                print('No exchange Account found with pk {}'.format(content.get('exchange_account_pk')))
                return

            try:
                exchange = getattr(ccxt, exchange_account.exchange.lower())()
            except Exception as e:
                print('Bad stuff: {}'.format(e))
                return

            exchange.load_markets()

            # first, clear the existing markets
            self.send_json({'message_type': 'clear_markets'})

            # then send the available markets
            for market in exchange.symbols:
                self.send_json(
                    {
                        'message_type': 'new_market',
                        'text': market
                    }
                )

            # finally we send the selected market if there is one
            if self.bot.market:
                self.send_json(
                    {
                        'message_type': 'selected_market',
                        'text': self.bot.market
                    }
                )



