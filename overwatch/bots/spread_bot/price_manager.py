import requests


class PriceManager(object):
    def __init__(self, track_url, peg_url):
        self.rates = {'USD': 1}
        self.track_url = track_url
        self.peg_url = peg_url

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
            print('no price: {}'.format(data))
            self.rates[currency] = None
            return

        try:
            self.rates[currency] = float(avg_price)
        except ValueError:
            self.rates[currency] = None
        return

    def get_price(self, track, peg, reverse):
        '''
        get the value of the track currency from the streamer (prices returned in USD)
        divide by the value of the peg currency
        '''
        # ensure the currencies have rates this time
        self.get_aggregator_price(track.upper(), self.track_url)
        self.get_aggregator_price(peg.upper(), self.peg_url)

        # ensure not None
        if self.rates[track.upper()] is None:
            print('Could not get aggregated price for track currency {}'.format(track))
            return None

        if self.rates[peg.upper()] is None:
            print('Could not get aggregated price for peg currency {}'.format(peg))
            return None

        # return the caluclated price
        if reverse:
            return self.rates[track.upper()] / self.rates[peg.upper()]

        return (1 / self.rates[track.upper()] * self.rates[peg.upper()])
