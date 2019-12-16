from channels.consumer import SyncConsumer
import logging
from overwatch.models import BotPlacedOrder, BotPrice

logger = logging.getLogger(__name__)


class BotOrderConsumer(SyncConsumer):
    @staticmethod
    def calculate_usd_values(message):
        """
        This method is called when a bot_order is saved.
        It fetches the price closest to the time recorded for the bot_order and updates the bot_order instance
        """
        logger.info('Trying to get usd values for BotPlacedOrder {}'.format(message.get('bot_order')))

        try:
            bot_order = BotPlacedOrder.objects.get(pk=message.get('bot_order'))
        except BotPlacedOrder.DoesNotExist:
            logger.error('BotPlaceOrder not found')
            return

        if bot_order.updated:
            logger.warning('BotPlacedOrder already updated')
            return

        # we should use the bot price closest to the order being placed to calculate the USD value
        try:
            closest_bot_price = BotPrice.objects.get_closest_to(bot_order.bot, bot_order.time)
        except BotPrice.DoesNotExist:
            logger.error('No closest BotPrice for calculation')
            return

        bot_quote_price = closest_bot_price.quote_price

        if bot_quote_price is None:
            logger.error('No USD Price for closest price')
            return

        if bot_order.price:
            bot_order.price_usd = bot_order.price * bot_quote_price

        bot_order.updated = True
        bot_order.save()

        logger.info('updated bot_order')
