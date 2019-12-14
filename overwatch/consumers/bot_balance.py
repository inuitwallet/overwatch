import logging

from channels.consumer import SyncConsumer

from overwatch.models import BotBalance, BotPrice
from overwatch.utils.price_aggregator import get_price_data

logger = logging.getLogger(__name__)


class BotBalanceConsumer(SyncConsumer):
    @staticmethod
    def calculate_usd_values(message):
        """
        This method is called when a bot_balance is saved.
        It fetches the price closest to the time recorded for the bot_balance and updates the bot_balance instance
        """
        logger.info('Trying to get usd values for BotBalance {}'.format(message.get('bot_balance')))

        try:
            bot_balance = BotBalance.objects.get(pk=message.get('bot_balance'))
        except BotBalance.DoesNotExist:
            logger.error('No BotBalance object found')
            return

        if bot_balance.updated:
            logger.warning('BotBalance already updated')
            return

        logger.info('Getting usd values for BotBalance: {} {}'.format(bot_balance.pk, bot_balance))

        # get the spot price at the time closest to the botbalance
        quote_price_data = get_price_data(
            bot_balance.bot.quote_price_url,
            bot_balance.bot.quote,
            bot_balance.time
        )

        if quote_price_data is None:
            logger.error('No Quote Price Data')
            return

        quote_price_30_ma = quote_price_data.get('moving_averages', {}).get('30_minute')

        if quote_price_30_ma is None:
            logger.error('No 30 min MA found')
            return

        base_price_data = get_price_data(
            bot_balance.bot.base_price_url,
            bot_balance.bot.base,
            bot_balance.time
        )

        if base_price_data is None:
            logger.error('No Quote Price Data')
            return

        base_price_30_ma = base_price_data.get('moving_averages', {}).get('30_minute')

        if base_price_30_ma is None:
            logger.error('No 30 min MA found')
            return

        if bot_balance.bid_available is not None:
            bot_balance.bid_available_usd = bot_balance.bid_available * quote_price_30_ma

        if bot_balance.bid_available is not None:
            nearest_price = BotPrice.objects.get_closest_to(bot_balance.bot, bot_balance.time)

            if nearest_price:
                bot_balance.bid_available_as_base = bot_balance.bid_available / nearest_price.price

        if bot_balance.bid_on_order is not None:
            # bid_balance_on_order will be denominated in the 'base' currency
            bot_balance.bid_on_order_usd = bot_balance.bid_on_order * base_price_30_ma

        if bot_balance.ask_available is not None:
            bot_balance.ask_available_usd = bot_balance.ask_available * base_price_30_ma

        if bot_balance.ask_on_order is not None:
            bot_balance.ask_on_order_usd = bot_balance.ask_on_order * base_price_30_ma

        bot_balance.updated = True

        bot_balance.save()

        logger.info('updated bot_balance')
