from datetime import datetime

import requests


def get_price_data(price_url, currency, dt=None):
    """
    Contact the price-aggregator service and fetch a price for the given currency
    If time_stamp is None, the latest price is retrieved.
    Otherwise the price closest to the tie stamp is retrieved.
    """
    if currency.lower() == 'usd':
        return {
            "aggregated_usd_price": 1,
            "currency": "USD",
            "currency_name": "US-Dollar",
            "moving_averages": {
                "12_hour": 1,
                "1_hour": 1,
                "24_hour": 1,
                "30_minute": 1,
                "6_hour": 1
            }
        }

    if currency.lower() == 'cnnbt':
        currency = 'cny'

    url = '{}/{}'.format(price_url, currency)

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


def get_price_movement(price_url, currency):
    """
    get the price movements for the given currency fromthe price aggregator service
    """
    if currency.lower() == 'usd':
        return None

    if currency.lower() == 'cnnbt':
        currency = 'cny'

    r = requests.get(url='{}/{}'.format(price_url, currency), timeout=30)
    r.raise_for_status()

    try:
        return r.json()
    except ValueError:
        print('No Json Returned: {}'.format(r.text))
        return None
