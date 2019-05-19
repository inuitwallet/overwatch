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

        # get the spot price at the time closest to the BotOrder. 
        # This will be the quote currency if the bot is reversed
        print('getting spot price for {}'.format(bot_trade.bot.quote if bot_trade.bot.reversed else bot_trade.bot.base))
        got_price_data = get_price_data(
            bot_trade.bot.quote_price_url if bot_trade.bot.reversed else bot_trade.bot.base_price_url,
            bot_trade.bot.quote if bot_trade.bot.reversed else bot_trade.bot.base, 
            bot_trade.time
        )

        if got_price_data is None:
            return

        got_price_usd = got_price_data.get('moving_averages', {}).get('30_minute')

        if got_price_usd is None:
            return

        # get the bot_price value closest to the trade. 
        # This will be denominated in base currency if the bot is reversed
        try:
            closest_bot_price = BotPrice.objects.get_closest_to(bot_trade.bot, bot_trade.time)
        except BotPrice.DoesNotExist:
            print('no closest BotPrice for calculation')
            return

        bot_price_usd = closest_bot_price.price_usd

        if bot_price_usd is None:
            return

        if bot_trade.price:
            if bot_trade.bot.reversed:
                trade_price_usd = got_price_usd / bot_trade.price
            else:
                trade_price_usd = bot_trade.price * got_price_usd

            bot_trade.trade_price_usd = trade_price_usd
            bot_trade.target_price_usd = bot_price_usd

            if bot_trade.trade_type == 'buy':
                if bot_trade.bot.reversed:
                    trade_difference = trade_price_usd - bot_price_usd
                else:
                    trade_difference = bot_price_usd - trade_price_usd
            else:
                if bot_trade.bot.reversed:
                    trade_difference = bot_price_usd - trade_price_usd
                else:
                    trade_difference = trade_price_usd - bot_price_usd

            bot_trade.difference_usd = trade_difference

            if bot_trade.bot.reversed:
                bot_trade.profit_usd = trade_difference * bot_trade.total
            else:
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


