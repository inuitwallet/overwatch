from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer

from overwatch.models import BotPlacedOrder, BotPrice
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

        # we should use the bot price closest to the order being placed to calculate the USD value
        try:
            closest_bot_price = BotPrice.objects.get_closest_to(bot_order.bot, bot_order.time)
        except BotPrice.DoesNotExist:
            print('no closest BotPrice for calculation')
            return

        bot_price_usd = closest_bot_price.price_usd
        print(bot_price_usd)

        if bot_price_usd is None:
            return

        if bot_order.price:
            bot_order.price_usd = bot_order.price * bot_price_usd

        bot_order.updated = True
        bot_order.save()

        print('updated bot_order')




