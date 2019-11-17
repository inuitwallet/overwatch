import requests
import os
from vigil import vigil_alert
from datetime import datetime

class Altilly(object):
    """
    Altilly say that USNBT is the base currency but orders are priced in BTC.
    They just have them the wrong way round
    """
    def __init__(self, api_key, api_secret, base_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def make_request(self, method, url, params):
        if method == 'post':
            response = requests.post(
                url='{}{}'.format(self.base_url, url),
                data=params,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=(self.api_key, self.api_secret)
            )
        if method == 'get':
            response = requests.get(
                url='{}{}'.format(self.base_url, url),
                data=params,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=(self.api_key, self.api_secret)
            )
        if method == 'delete':
            response = requests.delete(
                url='{}{}'.format(self.base_url, url),
                data=params,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=(self.api_key, self.api_secret)
            )
        if method == 'put':
            response = requests.put(
                url='{}{}'.format(self.base_url, url),
                data=params,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                auth=(self.api_key, self.api_secret)
            )

        if response.status_code != requests.codes.ok:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'Altilly',
                    'action': 'Make a Request to {}'.format(url),
                    'error': 'Got a bad response code: {} {}'.format(response.status_code, response.text)
                }
            )
            print('Got a bad response code: {} {}'.format(response.status_code, response.text))
            return {}

        try:
            json_response = response.json()
        except ValueError:
            return {}

        return json_response

    def cancel_order(self, order_id):
        return self.make_request('delete', '/order/{}'.format(order_id), {})

    def place_order(self, base, quote, order_type, price, amount):
        print('Placing Order: {} {}@{}'.format(order_type, amount, price))
        result = self.make_request(
            'post',
            '/order',
            {
                'symbol': '{}{}'.format(quote.upper(), base.upper()),
                'side': order_type,
                'quantity': amount,
                'price': price
            }
        )

        return result.get('uuid', False)

    def get_open_orders(self, base, quote):
        open_orders = self.make_request('get', '/order', {'symbol': '{}{}'.format(quote.upper(), base.upper())})

        if open_orders is None:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'Altilly',
                    'action': 'Get Open Orders for {}-{}'.format(quote.upper(), base.upper()),
                    'error': 'There are no open orders!'
                }
            )
            return None

        orders = {'ask': [], 'bid': []}

        for order in open_orders:
            if order.get('symbol') != '{}{}'.format(quote.upper(), base.upper()):
                continue

            order_type = 'bid'

            if order.get('side') == 'sell':
                order_type = 'ask'

            orders[order_type].append(
                {
                    'id': order.get('uuid'),
                    'amount': float(order.get('quantity')),
                    'price': float(order.get('price'))
                }
            )

        return orders

    def get_balances(self):
        return self.make_request('get', '/trading/balance', {})

    def get_balance(self, currency):
        balances = self.get_balances()
        currency_balance = None

        for balance in balances:
            if balance.get('currency').lower() == currency.lower():
                currency_balance = balance.get('available')

        return currency_balance

    def get_trades(self, pair):
        trades = []

        exchange_trades = self.make_request(
            'get',
            '/history/trades',
            {'symbol': '{}{}'.format(pair['quote'].upper(), pair['base'].upper())}
        )

        for trade in exchange_trades:
            if trade.get('symbol') != '{}{}'.format(pair['quote'].upper(), pair['base'].upper()):
                continue

            trade_time = datetime.strptime(
                trade.get('timestamp').split('.')[0],
                '%Y-%m-%dT%H:%M:%S'
            )

            trades.append(
                {
                    'trade_type': trade.get('side'),
                    'trade_id': trade.get('uuid'),
                    'trade_time': trade_time,
                    'price': float(trade.get('price')),
                    'amount': float(trade.get('quantity')),
                    'total': float(trade.get('price')) * float(trade.get('quantity')),
                    'age': 1
                }
            )

        return sorted(trades, key=lambda x: x['trade_time'], reverse=True)


    def get_min_trade_size(self, base, quote):
        return 0.0001

    def get_last_price(self, pair):
        r = requests.get(
            url='https://api.altilly.com/api/public/ticker'
        )

        if r.status_code != requests.codes.ok:
            return 0

        try:
            response = r.json()
        except ValueError:
            return None

        for market in response:
            if market.get('symbol') == '{}{}'.format(pair['quote'].upper(), pair['base'].upper()):
                return float(market.get('last', 0.0))

        return None

    def cancel_all_orders(self, pair):
        orders = self.get_open_orders(pair.get('quote'), pair.get('base'))

        for side in orders:
            for order in orders[side]:
                self.cancel_order(order['id'])
