import base64
import codecs
import hashlib
import hmac
import json
import os
from urllib import parse
from datetime import datetime
from vigil import vigil_alert

import logging
import requests
import time


class SouthXchange(object):

    def __init__(self, api_key, api_secret, base_url):
        self.name = 'SouthXchange'
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def get_headers(self, post_params):
        headers = {
            'Content-Type': 'application/json',
            'Hash': hmac.new(
                self.api_secret.encode(),
                msg=json.dumps(post_params).encode('utf-8'),
                digestmod=hashlib.sha512
            ).hexdigest()
        }
        return headers

    def make_request(self, url, post_params, tries=0):
        post_params['nonce'] = time.time() * 1000
        post_params['key'] = self.api_key
        response = requests.post(
            url=self.base_url + url,
            headers=self.get_headers(post_params),
            data=json.dumps(post_params),
        )

        # some responses indicate a temporary failue so we just try again
        retry = False

        if response.status_code == 429:
            retry = True

        if response.status_code == 400 and 'Invalid API key or nonce' in response.text:
            retry = True

        if retry:
            print('Retry needed: {} - {}'.format(response.status_code, response.text))
            tries += 1

            if tries >= 5:
                vigil_alert(
                    alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                    data={
                        'bot_name': os.environ['BOT_NAME'],
                        'exchange': 'SouthXchange',
                        'action': 'Make a Request to {}'.format(url),
                        'error': '5 retries attempted and failed. Giving up'
                    }
                )
                return False

            time.sleep(10)
            return self.make_request(url, post_params, tries)

        if response.status_code == requests.codes.no_content:
            # we got no content response.
            # cancel order returns this on success
            return True

        if response.status_code != requests.codes.ok:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'SouthXchange',
                    'action': 'Make a Request to {}'.format(url),
                    'error': 'Got a bad response code: {} {}'.format(response.status_code, response.text)
                }
            )
            return False

        try:
            return response.json()
        except ValueError:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'SouthXchange',
                    'action': 'Make a Request to {}'.format(url),
                    'error': 'no json returned by api: {}'.format(response.text)
                }
            )
            return None

    def get_open_orders(self, base, quote):
        open_orders = self.make_request('listOrders', {})

        if open_orders is None or open_orders is False:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'SouthXchange',
                    'action': 'Get Open Orders',
                    'error': 'There are no open orders!'
                }
            )
            return None

        orders = {'ask': [], 'bid': []}

        for order in open_orders:
            if order.get('ListingCurrency') != quote:
                continue

            if order.get('ReferenceCurrency') != base:
                continue

            orders['ask' if order.get('Type') == 'sell' else 'bid'].append(
                {
                    'id': order.get('Code'),
                    'amount': order.get('Amount'),
                    'price': order.get('LimitPrice')
                }
            )

        return orders

    def get_balances(self):
        return self.make_request('listBalances', {})

    def get_balance(self, currency):
        balances = self.get_balances()

        if not balances:
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'exchange': 'SouthXchange',
                    'action': 'Get Balance',
                    'error': 'no balances found'
                }
            )
            balances = []

        for balance in balances:
            if balance.get('Currency').upper() == currency.upper():
                return float(balance.get('Available'))

        vigil_alert(
            alert_channel_id=os.environ['VIGIL_WRAPPER_ERROR_CHANNEL_ID'],
            data={
                'bot_name': os.environ['BOT_NAME'],
                'exchange': 'SouthXchange',
                'action': 'Get Balance',
                'error': 'no balance found for {}'.format(currency)
            }
        )
        return None

    def place_order(self, base, quote, order_type, price, amount):
        print(
            'Placing {} Order: {:.4f} {} @ {:.4f} {}'.format(
                order_type,
                amount,
                quote,
                price,
                base
            )
        )
        order_id = self.make_request(
            'placeOrder',
            {
                'listingCurrency': quote,
                'referenceCurrency': base,
                'type': order_type,
                'amount': amount,
                'limitPrice': price
            }
        )

        return order_id

    def cancel_order(self, order_id):
        cancel = self.make_request(
            'cancelOrder',
            {
                'orderCode': order_id
            }
        )

        if cancel is False:
            return False

        return True

    def get_trades(self, pair):
        trades = []

        exchange_trades = self.make_request(
            'listTransactions',
            {
                'PageSize': 50,
                'SortField': 'Date',
                'Descending': True
            }
        )

        if not exchange_trades:
            return trades

        for trade in exchange_trades.get('Result', []):
            if trade.get('Type') != 'trade':
                continue

            if trade.get('CurrencyCode') != pair['base'].upper():
                continue

            if trade.get('OtherCurrency') != pair['quote'].upper():
                continue

            date = datetime.strptime(
                trade.get('Date').split('.')[0],
                '%Y-%m-%dT%H:%M:%S'
            )

            trades.append(
                {
                    'trade_type': 'sell' if float(trade.get('Amount', 0)) > float(0.0) else 'buy',
                    'trade_id': trade.get('TradeId'),
                    'trade_time': date,
                    'price': float(trade.get('Price')),
                    'amount': float(trade.get('OtherAmount')),
                    'total': float(trade.get('OtherAmount') * trade.get('Price')),
                    'age': 1
                }
            )

        return sorted(trades, key=lambda x: x['trade_time'], reverse=True)

    def get_min_trade_size(self, base, quote):
        return 0.001

    def get_last_price(self, pair):
        ##  https://www.southxchange.com/api/price/{listingCurrencyCode}/{referenceCurrencyCode}
        response = requests.get('{}/price/{}/{}'.format(self.base_url, pair['quote'].upper(), pair['base'].upper()))

        if response.status_code != requests.codes.ok:
            return None

        try:
            price_data = response.json()
        except ValueError:
            return None

        return float(price_data.get('Last', 0))

    def cancel_all_orders(self, pair):
        orders = self.get_open_orders(pair.get('base'), pair.get('quote'))

        for side in orders:
            for order in orders[side]:
                self.cancel_order(order['id'])
