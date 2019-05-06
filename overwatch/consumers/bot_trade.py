from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer

from overwatch.models import BotTrade, BotPrice
from overwatch.utils.price_aggregator import get_price_data


class BotTradeConsumer(SyncConsumer):
    def calculate_usd_values(self, message):
        """
        This method is called when a bot_trade is saved.
        It fetches the price closest to the time recorded for the bot_trade and updates the bot_trade instance
        """
        try:
            bot_trade = BotTrade.objects.get(pk=message.get('bot_trade'))
        except BotTrade.DoesNotExist:
            return

        if bot_trade.updated:
            return

        print('Getting usd values for BotTrade: {}) {}'.format(bot_trade.pk, bot_trade))

        # get the spot prices at the time closest to the BotOrder
        base_price_data = get_price_data(bot_trade.bot.base_price_url, bot_trade.bot.base, bot_trade.time)

        if base_price_data is None:
            return

        base_price_30_ma = base_price_data.get('moving_averages', {}).get('30_minute')

        if base_price_30_ma is None:
            return

        # the quote price should be the bot_price closest to the trade time
        try:
            closest_bot_price = BotPrice.objects.get_closest_to(bot_trade.bot, bot_trade.time)
        except BotPrice.DoesNotExist:
            print('no closest BotPrice for calculation')
            return

        quote_price_30_ma = closest_bot_price.ask_price_usd

        if quote_price_30_ma is None:
            return

        if bot_trade.price:
            trade_price_usd = bot_trade.price * base_price_30_ma

            bot_trade.trade_price_usd = trade_price_usd
            bot_trade.target_price_usd = quote_price_30_ma

            if bot_trade.trade_type == 'buy':
                trade_difference = quote_price_30_ma - trade_price_usd
            else:
                trade_difference = trade_price_usd - quote_price_30_ma

            bot_trade.difference_usd = trade_difference
            bot_trade.profit_usd = trade_difference * bot_trade.amount

            bot_trade.updated = True
            bot_trade.save()

            print('updated bot_trade')

        # we should scan any other prices that happen to be missing usd prices
        # for bad_bot_trade in BotTrade.objects.filter(updated=False):
        #     async_to_sync(self.channel_layer.send)(
        #         'bot-trade',
        #         {
        #             "type": "calculate.usd.values",
        #             "bot_trade": bad_bot_trade.pk,
        #         },
        #     )


