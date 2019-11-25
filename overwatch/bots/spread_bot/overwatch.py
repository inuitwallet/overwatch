import hashlib
import hmac
import logging
import sys
import time
import uuid

import requests


class Overwatch(object):
    def __init__(self, api_secret, name, exchange):
        self.api_secret = api_secret
        self.name = name
        self.exchange = exchange
        self.logger = self.setup_logging()

    @staticmethod
    def setup_logging():
        logger = logging.getLogger()
        for h in logger.handlers:
            logger.removeHandler(h)

        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

        logger.addHandler(h)
        logger.setLevel(logging.INFO)

        return logger

    def generate_hash(self):
        nonce = int(time.time() * 1000)
        # calculate the hash from supplied data
        return nonce, hmac.new(
            uuid.UUID(self.api_secret).bytes,
            '{}{}{}'.format(
                self.name.lower(),
                self.exchange.lower(),
                nonce
            ).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def handle_response(self, r):
        if r.status_code != requests.codes.ok:
            self.logger.error('overwatch gave a bad response code: {}'.format(r.status_code))
            return False

        try:
            response = r.json()
        except ValueError:
            self.logger.error('overwatch did not return valid JSON: {}'.format(r.text))
            return False

        if not response.get('success', True):
            self.logger.error('overwatch reported a failure: {}'.format(response))
            return False

        return response

    def get_config(self):
        nonce, generated_hash = self.generate_hash()
        config = self.handle_response(
            requests.get(
                url='https://overwatch.crypto-daio.co.uk/bot/config',
                params={
                    'name': self.name,
                    'exchange': self.exchange,
                    'n': nonce,
                    'h': generated_hash
                }
            )
        )

        if not config:
            self.logger.error('unable to get config for {}@{}'.format(self.name, self.exchange))
            return False

        return config

    def record_placed_order(self, base, quote, order_type, price, amount):
        nonce, generated_hash = self.generate_hash()
        self.handle_response(
            requests.post(
                url='https://overwatch.crypto-daio.co.uk/bot/placed_order',
                data={
                    'name': self.name,
                    'exchange': self.exchange,
                    'n': nonce,
                    'h': generated_hash,
                    'base': base,
                    'quote': quote,
                    'order_type': order_type,
                    'price': price,
                    'amount': amount
                }
            )
        )

    def record_price(self, price, bid_price, ask_price, market_price):
        nonce, generated_hash = self.generate_hash()
        self.handle_response(
            requests.post(
                url='https://overwatch.crypto-daio.co.uk/bot/prices',
                data={
                    'name': self.name,
                    'exchange': self.exchange,
                    'n': nonce,
                    'h': generated_hash,
                    'price': price,
                    'bid_price': bid_price,
                    'ask_price': ask_price,
                    'market_price': market_price
                }
            )
        )

    def record_balances(self, bid_available, ask_available, bid_on_order, ask_on_order, unit):
        nonce, generated_hash = self.generate_hash()
        self.handle_response(
            requests.post(
                url='https://overwatch.crypto-daio.co.uk/bot/balances',
                data={
                    'name': self.name,
                    'exchange': self.exchange,
                    'n': nonce,
                    'h': generated_hash,
                    'unit': unit,
                    'bid_available': bid_available,
                    'ask_available': ask_available,
                    'bid_on_order': bid_on_order,
                    'ask_on_order': ask_on_order,
                }
            )
        )

    def get_last_trade_id(self):
        nonce, generated_hash = self.generate_hash()
        response = self.handle_response(
            requests.get(
                url='https://overwatch.crypto-daio.co.uk/bot/trades',
                params={
                    'name': self.name,
                    'exchange': self.exchange,
                    'n': nonce,
                    'h': generated_hash,
                }
            )
        )
        return response['trade_id']

    def record_trade(self, time, id, type, price, amount, total, age):
        nonce, generated_hash = self.generate_hash()
        self.handle_response(
            requests.post(
                url='https://overwatch.crypto-daio.co.uk/bot/trades',
                data={
                    'name': self.name,
                    'exchange': self.exchange,
                    'n': nonce,
                    'h': generated_hash,
                    'trade_time': time,
                    'trade_id': id,
                    'trade_type': type,
                    'price': price,
                    'amount': amount,
                    'total': total,
                    'age': age,
                }
            )
        )
