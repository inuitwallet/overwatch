import logging

from channels.consumer import SyncConsumer

from overwatch.models import BotTrade, BotPrice
from overwatch.utils.price_aggregator import get_price_data

logger = logging.getLogger(__name__)


class BotTradeConsumer(SyncConsumer):
    @staticmethod
    def calculate_usd_values(message):
        """
        This method is called when a bot_trade is saved.
        It fetches the price closest to the time recorded for the bot_trade and updates the bot_trade instance
        """
        logger.info('Trying to get USD values fof BotTrade {}'.format(message.get('bot_trade')))

        try:
            bot_trade = BotTrade.objects.get(pk=message.get('bot_trade'))
        except BotTrade.DoesNotExist:
            logger.error('No BotTrade found')
            return

        if bot_trade.updated:
            logger.warning('BotTrade already updated')
            return

        logger.info('Getting usd values for BotTrade: {}) {}'.format(bot_trade.pk, bot_trade))

        # get the spot price at the time closest to the BotOrder. 
        got_price_data = get_price_data(
            bot_trade.bot.quote_price_url,
            bot_trade.bot.quote,
            bot_trade.time
        )

        if got_price_data is None:
            logger.error('No price data')
            return

        got_price_usd = got_price_data.get('moving_averages', {}).get('30_minute')

        if got_price_usd is None:
            logger.error('No 30 min MA found')
            return

        # get the bot_price value closest to the trade. 
        try:
            closest_bot_price = BotPrice.objects.get_closest_to(bot_trade.bot, bot_trade.time)
        except BotPrice.DoesNotExist:
            logger.error('No closest BotPrice for calculation')
            return

        bot_price_usd = closest_bot_price.price_usd

        if bot_price_usd is None:
            logger.error('Closest BotPrice has no USD value')
            return

        if bot_trade.price:
            trade_price_usd = bot_trade.price * got_price_usd

            bot_trade.trade_price_usd = trade_price_usd
            bot_trade.target_price_usd = bot_price_usd

            if bot_trade.trade_type == 'buy':
                trade_difference = bot_price_usd - trade_price_usd
            else:
                trade_difference = trade_price_usd - bot_price_usd

            bot_trade.difference_usd = trade_difference

            bot_trade.profit_usd = trade_difference * bot_trade.amount

            bot_trade.updated = True
            bot_trade.save()

            logger.info('updated bot_trade')
