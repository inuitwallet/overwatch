from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer

from overwatch.models import BotPlacedOrder
from overwatch.utils.price_aggregator import get_price_data


class BotOrderConsumer(SyncConsumer):
    @staticmethod
    def calculate_usd_values(message):
        """
        This method is called when a bot_order is saved.
        It fetches the price closest to the time recorded for the bot_order and updates the bot_order instance
        """
        try:
            bot_order = BotPlacedOrder.objects.get(
                pk=message.get('bot_order')
            )
        except BotPlacedOrder.DoesNotExist:
            return

        if bot_order.updated:
            return

        print('Getting usd values for BotPlacedOrder: {} {}'.format(bot_order.pk, bot_order))

        # which currency to use?
        # we use quote if the bot is standard or base if it is reversed
        currency = bot_order.bot.quote if bot_order.bot.reversed else bot_order.bot.base

        # get the spot price at the time closest to the BotOrder
        price_data = get_price_data(currency, bot_order.time)

        if price_data is None:
            return

        price_30_ma = price_data.get('moving_averages', {}).get('30_minute')
        print(price_30_ma, currency)

        if price_30_ma is None:
            return

        if bot_order.price:
            if bot_order.bot.reversed:
                bot_order.price_usd = bot_order.price / price_30_ma
            else:
                bot_order.price_usd = bot_order.price * price_30_ma

        bot_order.updated = True
        bot_order.save()

        print('updated bot_order')




