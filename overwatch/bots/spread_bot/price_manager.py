import requests


class PriceManager(object):
    def __init__(self):
        self.rates = {'USD': 1}

    def get_aggregator_price(self, currency, url):
        if currency.upper() in self.rates:
            return

        r = requests.get(
            url='{}/{}'.format(
                url,
                currency
            )
        )

        if r.status_code != requests.codes.ok:
            self.rates[currency] = None
            return

        try:
            data = r.json()
        except ValueError:
            self.rates[currency] = None
            return

        moving_averages = data.get('moving_averages', {})
        avg_price = moving_averages.get('30_minute')

        if not avg_price:
            avg_price = data.get('aggregated_usd_price')

        if not avg_price:
            avg_price = data.get('usd_price')

        if not avg_price:
            self.rates[currency] = None
            return

        try:
            self.rates[currency] = float(avg_price)
        except ValueError:
            self.rates[currency] = None
        return

    def get_price(self, currency, url):
        self.get_aggregator_price(currency, url)
        return self.rates.get(currency.upper())
