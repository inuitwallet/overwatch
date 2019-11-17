import codecs
import time
import hashlib
import hmac
from datetime import datetime
from urllib import parse
import logging
import requests
import os
from decimal import Decimal
from vigil import vigil_alert


class Bittrex(object):
    def __init__(self, api_key, api_secret, base_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def make_request(self, url, params):
        url = '{}/{}?apikey={}&nonce={}&{}'.format(
            self.base_url,
            url,
            self.api_key,
            int(time.time() * 1000),
            parse.urlencode(params)
        )
        response = requests.get(
            url=url,
            headers={
                'apisign': hmac.new(
                    self.api_secret.encode(),
                    msg=url.encode(),
                    digestmod=hashlib.sha512
                ).hexdigest()
            }
        )

        if response.status_code == 429:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'Bittrex',
                    'action': 'Make a Request to {}'.format(url),
                    'error': 'Got 429 response code (too many requests). Trying again in 30 seconds'
                }
            )
            time.sleep(30)
            return self.make_request(url, post_params)

        if response.status_code != requests.codes.ok:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'Bittrex',
                    'action': 'Make a Request to {}'.format(url),
                    'error': 'Got a bad response code: {} {}'.format(response.status_code, response.text)
                }
            )
            return {}

        try:
            json_response = response.json()
        except ValueError:
            return {}

        if 'success' not in json_response:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'Bittrex',
                    'action': 'Make a Request to {}'.format(url),
                    'error': 'unexpected json response: {}'.format(json_response)
                }
            )
            return {}

        if not json_response['success']:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'Bittrex',
                    'action': 'Make a Request to {}'.format(url),
                    'error': 'api call failed: {}'.format(json_response['message'])
                }
            )
            return {}

        return json_response

    def cancel_order(self, order_id):
        cancelled = False
        attempts = 0

        while not cancelled:
            cancelled = self.make_request(
                'market/cancel',
                {'uuid': order_id}
            ).get(
                'success',
                False
            )
            attempts += 1

            if attempts >= 5:
                vigil_alert(
                    alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                    data={
                        'bot_name': os.environ['BOT_NAME'],
                        'exchange': 'Bittrex',
                        'action': 'Cancel Order {}'.format(order_id),
                        'error': '5 attempts to cancel have failed'
                    }
                )
                break

        return cancelled

    def place_order(self, base, quote, order_type, price, amount):
        if order_type == 'buy':
            endpoint = 'market/buylimit'
        else:
            endpoint = 'market/selllimit'

        print(
            'placing {} order. {:.4f}@{:.8f}'.format(order_type, amount, price)
        )

        result = self.make_request(
            endpoint,
            {
                'market': '{}-{}'.format(base.upper(), quote.upper()),
                'quantity': '{:.8f}'.format(amount),
                'rate': '{:.8f}'.format(price)
            }
        ).get(
            'result',
            {}
        )

        order_uuid = result.get('uuid', False)

        if order_uuid:
            return order_uuid

        return False

    def get_open_orders(self, base, quote):
        open_orders = self.make_request(
            'market/getopenorders',
            {
                'market': '{}-{}'.format(base.upper(), quote.upper())
            }
        ).get(
            'result'
        )

        if open_orders is None:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'Bittrex',
                    'action': 'Get Open Orders for {}-{}'.format(base.upper(), quote.upper()),
                    'error': 'There are no open orders!'
                }
            )
            return None

        orders = {'ask': [], 'bid': []}

        for order in open_orders:
            if order.get('Exchange') != '{}-{}'.format(base.upper(), quote.upper()):  # noqa
                continue

            order_type = 'bid'

            if order.get('OrderType') == 'LIMIT_SELL':
                order_type = 'ask'

            orders[order_type].append(
                {
                    'id': order.get('OrderUuid'),
                    'amount': order.get('QuantityRemaining'),
                    'price': order.get('Limit')
                }
            )

        return orders

    def get_balances(self):
        return self.make_request(
            'account/getbalances',
            {}
        ).get(
            'result',
            []
        )

    def get_balance(self, currency):
        balances = self.get_balances()
        currency_balance = None

        for balance in balances:
            if balance.get('Currency') == currency:
                currency_balance = balance.get('Available')

        return currency_balance

    def get_trades(self, pair):
        trades = []

        exchange_trades =  self.make_request(
            'account/getorderhistory',
            {'limit': 0}
        ).get(
            'result',
            []
        )

        for trade in exchange_trades:
            if trade.get('Exchange') != '{}-{}'.format(pair['base'].upper(), pair['quote'].upper()):
                continue

            opened = datetime.strptime(
                trade.get('TimeStamp').split('.')[0],
                '%Y-%m-%dT%H:%M:%S'
            )
            closed = datetime.strptime(
                trade.get('Closed').split('.')[0],
                '%Y-%m-%dT%H:%M:%S'
            )
            trades.append(
                {
                    'trade_type': 'sell' if trade.get('OrderType') == 'LIMIT_SELL' else 'buy',
                    'trade_id': trade.get('OrderUuid'),
                    'trade_time': closed,
                    'price': trade.get('PricePerUnit'),
                    'amount': trade.get('Quantity') - trade.get('QuantityRemaining'),
                    'total': trade.get('Price'),
                    'age': (closed - opened).seconds
                }
            )

        return sorted(trades, key=lambda x: x['trade_time'], reverse=True)

    def get_min_trade_size(self, base, quote):
        r = requests.get('https://api.bittrex.com/api/v1.1/public/getmarkets')

        if r.status_code != requests.codes.ok:
            return 0

        try:
            response = r.json()
        except ValueError:
            return 0

        for market in response.get('result', []):
            if (
                market['BaseCurrency'] == base.upper()
                and market['MarketCurrency'] == quote.upper()
            ):
                return market['MinTradeSize']

    def get_last_price(self, pair):
        r = requests.get('https://bittrex.com/api/v1.1/public/getmarketsummaries')

        if r.status_code != requests.codes.ok:
            return 0

        try:
            response = r.json()
        except ValueError:
            return None

        for market in response.get('result', []):
            base_coin = market.get('MarketName', '-').split('-')[0]
            market_coin = market.get('MarketName', '-').split('-')[1]

            if (
                base_coin == pair['base'].upper()
                and market_coin == pair['quote'].upper()
            ):
                return float((market.get('Bid', 0) + market.get('Ask', 0)) / 2)

    def cancel_all_orders(self, pair):
        orders = self.get_open_orders(pair.get('base'), pair.get('quote'))

        for side in orders:
            for order in orders[side]:
                self.cancel_order(order['id'])
