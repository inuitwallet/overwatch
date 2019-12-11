import logging

from channels.consumer import SyncConsumer

from overwatch.models import BotPrice
from overwatch.utils.price_aggregator import get_price_data

logger = logging.getLogger(__name__)


class BotPriceConsumer(SyncConsumer):
    @staticmethod
    def calculate_usd_values(message):
        """
        This method is called when a bot_price is saved.
        It fetches the price closest to the time recorded for the bot_price and updates the bot_price instance
        """
        logger.info('Trying to get usd values for BotPrice {}'.format(message.get('bot_price')))

        try:
            bot_price = BotPrice.objects.get(pk=message.get('bot_price'))
        except BotPrice.DoesNotExist:
            logger.error('No BotPrice found')
            return

        if bot_price.updated:
            logger.warning('BotPrice already updated')
            return

        logger.info('Getting usd values for BotPrice: {} {}'.format(bot_price.pk, bot_price))

        # get the spot price at the time closest to the botprice
        price_data = get_price_data(bot_price.bot.quote_price_url, bot_price.bot.quote, bot_price.time)

        if price_data is None:
            logger.error('No price data found')
            return

        price_30_ma = price_data.get('moving_averages', {}).get('30_minute')

        if price_30_ma is None:
            logger.error('No 30 min MA found')
            return

        if bot_price.price:
            bot_price.price_usd = bot_price.price * price_30_ma

        if bot_price.bid_price:
            bot_price.bid_price_usd = bot_price.bid_price * price_30_ma

        if bot_price.ask_price:
            bot_price.ask_price_usd = bot_price.ask_price * price_30_ma

        if bot_price.market_price:
            bot_price.market_price_usd = bot_price.market_price * price_30_ma

        bot_price.unit = bot_price.bot.quote
        bot_price.updated = True

        bot_price.save()

        logger.info('updated bot_price')
