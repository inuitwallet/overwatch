from datetime import datetime

import requests


def get_price_data(currency, dt=None):
    """
    Contact the price-aggregator service and fetch a price for the given currency
    If time_stamp is None, the latest price is retrieved.
    Otherwise the price closest to the tie stamp is retrieved.
    """
    if currency.lower() == 'usd':
        return 1

    url = 'https://price-aggregator.crypto-daio.co.uk/price/{}'.format(currency)

    if dt is not None:
        # price service expects timestamp in format yyyy-mm-ddTHH:MM:SS
        url += '/{}'.format(datetime.strftime(dt, '%Y-%m-%dT%H:%M:%S'))

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    try:
        return r.json()
    except ValueError:
        print('No Json Returned: {}'.format(r.text))
        return None
