from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer

from overwatch.models import BotBalance
from overwatch.utils.price_aggregator import get_price_data


class BotBalanceConsumer(SyncConsumer):
    def calculate_usd_values(self, message):
        """
        This method is called when a bot_balance is saved.
        It fetches the price closest to the time recorded for the bot_balance and updates the bot_balance instance
        """
        try:
            bot_balance = BotBalance.objects.get(pk=message.get('bot_balance'))
        except BotBalance.DoesNotExist:
            return

        if bot_balance.updated:
            return

        print('Getting usd values for BotBalance: {} {}'.format(bot_balance.pk, bot_balance))

        # which currency to use?
        # we use quote if the bot is standard or base if it is reversed
        currency = bot_balance.bot.base if bot_balance.bot.reversed else bot_balance.bot.quote

        # get the spot price at the time closest to the botbalance
        price_data = get_price_data(currency, bot_balance.time)

        if price_data is None:
            return

        price_30_ma = price_data.get('moving_averages', {}).get('30_minute')

        if price_30_ma is None:
            return

        if bot_balance.bid_available:
            bot_balance.bid_available_usd = bot_balance.bid_available * price_30_ma

        if bot_balance.bid_on_order:
            bot_balance.bid_on_order_usd = bot_balance.bid_on_order * price_30_ma

        if bot_balance.ask_available:
            bot_balance.ask_available_usd = bot_balance.ask_available * price_30_ma

        if bot_balance.ask_on_order:
            bot_balance.ask_on_order_usd = bot_balance.ask_on_order * price_30_ma

        bot_balance.updated = True

        bot_balance.save()

        print('updated bot_balance')

        # we should scan any other prices that happen to be missing usd prices
        # for bad_bot_balance in BotBalance.objects.filter(updated=False):
        #     async_to_sync(self.channel_layer.send)(
        #         'bot-balance',
        #         {
        #             "type": "calculate.usd.values",
        #             "bot_balance": bad_bot_balance.pk,
        #         },
        #     )


