import requests
from django.core.management import BaseCommand

from overwatch.models.bot import BotPrice


class Command(BaseCommand):
    usd_prices = {}

    @staticmethod
    def apply_price(bot_price, usd_price, reverse):
        if reverse:
            return (1 / bot_price) * float(usd_price)
        else:
            return bot_price * float(usd_price)

    def make_price_request(self, currency):
        # we've not see this unit yet so get the usd price
        r = requests.get('https://price-aggregator.crypto-daio.co.uk/price/{}'.format(currency))

        if r.status_code == requests.codes.not_found:
            # we got a 404 so no data for this unit
            # set to None to prevent future wasted requests
            self.usd_prices[currency] = None
            return False

        if r.status_code != requests.codes.ok:
            # other fail code probably means a temporary issue with the price aggregator
            return False

        try:
            response = r.json()
        except ValueError:
            # no valid json returned, some temporary error again perhaps?
            return False

        # we got a response so set the value!
        self.usd_prices[currency] = response.get('moving_averages', {}).get('30_minute')
        return True

    def handle(self, *args, **options):
        # get all BotPrices that don't have a price_usd
        bot_prices = BotPrice.objects.filter(price_peg__isnull=True)

        print('getting PEG values for {} bot prices'.format(bot_prices.count()))

        for bot_price in bot_prices:
            track = bot_price.bot.track.upper()
            peg = bot_price.bot.peg.upper()
            reverse = bot_price.bot.quote.upper() == track

            if track not in self.usd_prices:
                if not self.make_price_request(track):
                    continue

            if self.usd_prices[track] is None:
                # catch the not found unit from above without the need for a second request
                continue

            # If the peg currency is USD, we're golden as the price is already in USD
            if peg == 'USD':
                if bot_price.price:
                    bot_price.price_peg = self.apply_price(bot_price.price, self.usd_prices[track], reverse)

                if bot_price.bid_price:
                    bot_price.bid_price_peg = self.apply_price(bot_price.bid_price, self.usd_prices[track], reverse)

                if bot_price.ask_price:
                    bot_price.ask_price_peg = self.apply_price(bot_price.ask_price, self.usd_prices[track], reverse)

            else:
                # we do the same as above but multiply in the USD price of the peg currency
                if peg not in self.usd_prices:
                    if not self.make_price_request(peg):
                        continue

                if self.usd_prices[peg] is None:
                    # catch the not found unit from above without the need for a second request
                    continue

                if reverse:
                    peg_price = self.usd_prices[track] / self.usd_prices[peg]
                else:
                    peg_price = self.usd_prices[track] * self.usd_prices[peg]

                if bot_price.price:
                    bot_price.price_peg = self.apply_price(bot_price.price, peg_price, reverse)

                if bot_price.bid_price:
                    bot_price.bid_price_peg = self.apply_price(bot_price.bid_price, peg_price, reverse)

                if bot_price.ask_price:
                    bot_price.ask_price_peg = self.apply_price(bot_price.ask_price, peg_price, reverse)

            bot_price.save()
