import requests
from django.core.management import BaseCommand

from overwatch.models.bot import BotPrice


class Command(BaseCommand):
    usd_prices = {}

    def handle(self, *args, **options):
        # get all BotPrices that don't have a price_usd
        bot_prices = BotPrice.objects.filter(price_usd__isnull=True).exclude(unit__iexact='usd')
        print('getting USD values for {} bot prices'.format(bot_prices.count()))
        for bot_price in bot_prices:
            if bot_price.unit not in self.usd_prices:
                # we've not see this unit yet so get the usd price
                r = requests.get('https://price-aggregator.crypto-daio.co.uk/price/{}'.format(bot_price.unit))

                if r.status_code == requests.codes.not_found:
                    # we got a 404 so no data for this unit
                    # set to None to prevent future wasted requests
                    self.usd_prices[bot_price.unit] = None
                    continue

                if r.status_code != requests.codes.ok:
                    # other fail code probably means a temporary issue with the price aggregator
                    continue

                try:
                    response = r.json()
                except ValueError:
                    # no valid json returned, some temporary error again perhaps?
                    continue

                # we got a response so set the value!
                self.usd_prices[bot_price.unit] = response.get('moving_averages', {}).get('30_minute')

            if self.usd_prices[bot_price.unit] is None:
                # catch the not sound unit from above without the need for a second request
                continue

            if bot_price.price:
                bot_price.price_usd = bot_price.price * float(self.usd_prices[bot_price.unit])

            if bot_price.bid_price:
                bot_price.bid_price_usd = bot_price.bid_price * float(self.usd_prices[bot_price.unit])

            if bot_price.ask_price:
                bot_price.ask_price_usd = bot_price.ask_price * float(self.usd_prices[bot_price.unit])

            bot_price.save()
