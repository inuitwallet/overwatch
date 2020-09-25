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
        # get the bot from the websocket url if it exists
        pk = self.scope.get("url_route", {}).get("kwargs", {}).get("pk")

        if pk:
            try:
                self.bot = Bot.objects.get(pk=pk)
            except Bot.DoesNotExist:
                self.close()
                return

        # accept the websocket connection
        self.accept()

    def disconnect(self, close_code):
        """
        disconnect from the websocket so remove from groups
        """
        self.close()

    def receive_json(self, content, **kwargs):
        message_type = content.get("message_type")

        if message_type == "get_markets":
            exchange_account_pk = content.get("exchange_account_pk")

            if not exchange_account_pk:
                return

            try:
                exchange_account = Exchange.objects.get(pk=exchange_account_pk)
            except Exchange.DoesNotExist:
                print(
                    "No exchange Account found with pk {}".format(exchange_account_pk)
                )
                return

            try:
                exchange = getattr(ccxt, exchange_account.exchange.lower())()
            except Exception as e:
                print("Bad stuff: {}".format(e))
                return

            exchange.load_markets()

            # first, clear the existing markets
            self.send_json({"message_type": "clear_markets"})

            # then send the available markets
            for market in exchange.symbols:
                self.send_json({"message_type": "new_market", "text": market})

            # finally we send the selected market if there is one
            if self.bot:
                if self.bot.market:
                    self.send_json(
                        {"message_type": "selected_market", "text": self.bot.market}
                    )
