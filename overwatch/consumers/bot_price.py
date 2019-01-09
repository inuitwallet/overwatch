from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer

from overwatch.models import BotPrice
from overwatch.utils.price_aggregator import get_price_data


class BotPriceConsumer(SyncConsumer):
    def calculate_usd_values(self, message):
        """
        This method is called when a bot_price is saved.
        It fetches the price closest to the time recorded for the bot_price and updates the bot_price instance
        """
        try:
            bot_price = BotPrice.objects.get(pk=message.get('bot_price'))
        except BotPrice.DoesNotExist:
            return

        if bot_price.updated:
            return

        print('Getting usd values for BotPrice: {} {}'.format(bot_price.pk, bot_price))

        # which currency to use?
        # we use quote if the bot is standard or base if it is reversed
        currency = bot_price.bot.base if bot_price.bot.reversed else bot_price.bot.quote

        # get the spot price at the time closest to the botprice
        price_data = get_price_data(currency, bot_price.time)

        if price_data is None:
            return

        price_30_ma = price_data.get('moving_averages', {}).get('30_minute')

        if price_30_ma is None:
            return

        if bot_price.price:
            bot_price.price_usd = bot_price.price * price_30_ma

        if bot_price.bid_price:
            bot_price.bid_price_usd = bot_price.bid_price * price_30_ma

        if bot_price.ask_price:
            bot_price.ask_price_usd = bot_price.ask_price * price_30_ma

        bot_price.unit = currency
        bot_price.updated = True

        bot_price.save()

        print('updated bot_price')

        # we should scan any other prices that happen to be missing usd prices
        # for bad_bot_price in BotPrice.objects.filter(updated=False):
        #     async_to_sync(self.channel_layer.send)(
        #         'bot-price',
        #         {
        #             "type": "calculate.usd.values",
        #             "bot_price": bad_bot_price.pk,
        #         },
        #     )


