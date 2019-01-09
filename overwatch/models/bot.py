import hashlib
import hmac
import uuid

from django.db import models
from django.template import Template, Context


class Bot(models.Model):
    name = models.CharField(
        max_length=255,
        help_text='Name to identify this bot. Usually the name of the pair it operates on'
    )
    exchange = models.CharField(
        max_length=255,
        help_text='The exchange the bot operates on. '
                  'Together with the name this forms a unique identifier for this bot'
    )
    base = models.CharField(
        max_length=255,
        help_text='The base currency of the pair to operate on'
    )
    quote = models.CharField(
        max_length=255,
        help_text='The quote currency of the pair to operate on'
    )
    track = models.CharField(
        max_length=255,
        help_text='The currency to track. This determines if the pair is reversed or not'
    )
    peg = models.CharField(
        max_length=255,
        help_text='The currency to peg to. The value of this currency will be used to calculate prices'
    )
    tolerance = models.FloatField(
        help_text='How far from the price an order can be before it is cancelled and replaced at the correct price.'
                  'Show as a Percentage'
    )
    fee = models.FloatField(
        help_text='The fee to apply to each side. Shown as a percentage'
    )
    bid_spread = models.FloatField(
        help_text='The spread to add to the fee on the Buy side'
    )
    ask_spread = models.FloatField(
        help_text='The spread to add to the fee on the Sell side'
    )
    order_amount = models.FloatField(
        help_text='The amount each order should be'
    )
    total_bid = models.FloatField(
        help_text='The total amount of funds allowed on the Buy side'
    )
    total_ask = models.FloatField(
        help_text='The total amount of funds allowed on the Sell side'
    )
    api_secret = models.UUIDField(
        default=uuid.uuid4
    )
    last_nonce = models.BigIntegerField(
        default=0
    )
    logs_group = models.CharField(
        max_length=255,
        help_text='AWS Cloudwatch logs group name',
        blank=True,
        null=True
    )
    aws_access_key = models.CharField(
        max_length=255,
        help_text='',
        blank=True,
        null=True
    )
    aws_secret_key = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    aws_region = models.CharField(
        max_length=255,
        default='eu-west-1'
    )
    peg_decimal_places = models.IntegerField(default=6)
    base_decimal_places = models.IntegerField(default=6)
    quote_decimal_places = models.IntegerField(default=6)

    def __str__(self):
        return self.name

    def serialize(self):
        return {
            'name': self.name,
            'exchange': self.exchange,
            'base': self.base,
            'quote': self.quote,
            'track': self.track,
            'peg': self.peg,
            'tolerance': self.tolerance / 100,
            'fee': self.fee / 100,
            'bid_spread': self.bid_spread / 100,
            'ask_spread': self.ask_spread / 100,
            'order_amount': self.order_amount,
            'total_bid': self.total_bid,
            'total_ask': self.total_ask
        }

    def auth(self, supplied_hash, name, exchange, nonce):
        # check that the supplied nonce is an integer
        # and is greater than the last supplied nonce to prevent reuse
        try:
            nonce = int(nonce)
        except ValueError:
            return False, 'n parameter needs to be a positive integer'

        if nonce <= self.last_nonce:
            return False, 'n parameter needs to be a positive integer and greater than the previous nonce'

        # calculate the hash from our own data
        calculated_hash = hmac.new(
            self.api_secret.bytes,
            '{}{}{}'.format(
                name.lower(),
                exchange.lower(),
                nonce
            ).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # update the last nonce value
        self.last_nonce = nonce
        self.save()

        if calculated_hash != supplied_hash:
            return False, 'supplied hash does not match calculated hash'

        return True, 'authenticated'

    @property
    def latest_heartbeat(self):
        latest_heartbeat = self.botheartbeat_set.first()

        if latest_heartbeat:
            return latest_heartbeat.time

        return ''

    @property
    def last_error(self):
        latest_error = self.boterror_set.first()

        if latest_error:
            return latest_error.time

        return ''

    @property
    def last_price(self):
        return self.botprice_set.exclude(price_usd__isnull=True).first()

    @property
    def last_balance(self):
        return self.botbalance_set.first()

    @property
    def reversed(self):
        return self.quote == self.peg

    @property
    def spread(self):
        return max(
            self.last_price.bid_price,
            self.last_price.ask_price
        ) - min(
            self.last_price.bid_price,
            self.last_price.ask_price
        )

    def rendered_price(self, usd=True):
        if usd:
            dp = str(4)
            template = '{{ last_price.price_usd|floatformat:' + dp + ' }} {{ currency }}'
        else:
            dp = str(self.base_decimal_places)
            template = '{{ last_price.price|floatformat:' + dp + ' }} {{ currency }}'

        return Template(
            template
        ).render(
            Context(
                {
                    'last_price': self.last_price,
                    'currency': 'USD' if usd else self.base
                }
            )
        )

    def rendered_bid_price(self, usd=True):
        if usd:
            dp = str(4)
            template = '{{ last_price.bid_price_usd|floatformat:' + dp + ' }} {{ currency }}'
        else:
            dp = str(self.base_decimal_places)
            template = '{{ last_price.bid_price|floatformat:' + dp + ' }} {{ currency }}'

        return Template(
            template
        ).render(
            Context(
                {
                    'last_price': self.last_price,
                    'currency': 'USD' if usd else self.base
                }
            )
        )

    def rendered_ask_price(self, usd=True):
        if usd:
            dp = str(6)
            template = '{{ last_price.ask_price_usd|floatformat:' + dp + ' }} {{ currency }}'
        else:
            dp = str(self.base_decimal_places)
            template = '{{ last_price.ask_price|floatformat:' + dp + ' }} {{ currency }}'

        return Template(
            template
        ).render(
            Context(
                {
                    'last_price': self.last_price,
                    'currency': 'USD' if usd else self.base
                }
            )
        )

    def rendered_bid_balance(self, on_order=True, usd=True):
        if usd:
            dp = str(6)
            currency = 'USD'
        else:
            dp = str(self.quote_decimal_places) if self.reversed else str(self.base_decimal_places)
            currency = self.base if self.reversed else self.quote

        if on_order:
            if usd:
                template = '{{ last_balance.bid_on_order_usd|floatformat:' + dp + ' }} {{ currency }}'
            else:
                template = '{{ last_balance.bid_on_order|floatformat:' + dp + ' }} {{ currency }}'
        else:
            if usd:
                template = '{{ last_balance.bid_available_usd|floatformat:' + dp + ' }} {{ currency }}'
            else:
                template = '{{ last_balance.bid_available|floatformat:' + dp + ' }} {{ currency }}'

        return Template(
            template
        ).render(
            Context(
                {
                    'last_balance': self.last_balance,
                    'currency': currency
                }
            )
        )

    def rendered_ask_balance(self, on_order=True, usd=True):
        if usd:
            dp = str(6)
            currency = 'USD'
        else:
            dp = str(self.base_decimal_places) if self.reversed else str(self.quote_decimal_places)
            currency = self.base if self.reversed else self.quote

        if on_order:
            if usd:
                template = '{{ last_balance.ask_on_order_usd|floatformat:' + dp + ' }} {{ currency }}'
            else:
                template = '{{ last_balance.ask_on_order|floatformat:' + dp + ' }} {{ currency }}'
        else:
            if usd:
                template = '{{ last_balance.ask_available_usd|floatformat:' + dp + ' }} {{ currency }}'
            else:
                template = '{{ last_balance.ask_available|floatformat:' + dp + ' }} {{ currency }}'

        return Template(
            template
        ).render(
            Context(
                {
                    'last_balance': self.last_balance,
                    'currency': currency
                }
            )
        )
