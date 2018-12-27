import requests
from django.core.management import BaseCommand

from overwatch.models.bot import BotTrade


class Command(BaseCommand):
    def get_price(self, cur):
        r = requests.get('https://price-aggregator.crypto-daio.co.uk/price/{}'.format(cur))

        if r.status_code != requests.codes.ok:
            print('Bad response from aggregator: {} {}'.format(r.status_code, r.reason))
            return None

        try:
            response = r.json()
        except ValueError:
            print('No Json: {}'.format(r.text))
            return None

        agg_price = response.get('moving_averages', {}).get('30_minute')

        if agg_price is None:
            print('No agg_price?: {}'.format(response))
            return None

        return agg_price

    def handle(self, *args, **options):
        trades = BotTrade.objects.filter(profit_usd__isnull=True)

        print('Updating trade prices for {} trades'.format(trades.count()))

        prices = {}

        for trade in trades:
            base_price = prices.get(trade.bot.base, self.get_price(trade.bot.base))
            quote_price = prices.get(trade.bot.quote, self.get_price(trade.bot.quote))

            if base_price is None:
                continue

            prices[trade.bot.base] = base_price

            if quote_price is None:
                continue

            prices[trade.bot.quote] = quote_price

            trade_price_usd = trade.price * base_price

            if trade.trade_type == 'buy':
                trade_diff_usd = quote_price - trade_price_usd
            else:
                trade_diff_usd = trade_price_usd - quote_price

            trade.target_price_usd = quote_price,
            trade.trade_price_usd = trade_price_usd,
            trade.difference_usd = trade_diff_usd,
            trade.profit_usd = trade_diff_usd * trade.amount

            trade.save()
            print('Updated {}'.format(trade))




