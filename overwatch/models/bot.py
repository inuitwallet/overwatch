import hashlib
import hmac
import uuid

from django.db import models


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
            'tolerance': self.tolerance,
            'fee': self.fee,
            'bid_spread': self.bid_spread,
            'ask_spread': self.ask_spread,
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


class BotHeartBeat(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE
    )
    time = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return '{}'.format(self.time)

    class Meta:
        ordering = ['-time']


class BotError(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE
    )
    time = models.DateTimeField(
        auto_now_add=True
    )
    title = models.CharField(
        max_length=255
    )
    message = models.TextField()

    def __str__(self):
        return '{} - {}'.format(self.time, self.title)

    class Meta:
        ordering = ['-time']


class BotPlacedOrder(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE
    )
    time = models.DateTimeField(
        auto_now_add=True
    )
    base = models.CharField(
        max_length=255,
    )
    quote = models.CharField(
        max_length=255,
    )
    order_type = models.CharField(
        max_length=255,
    )
    price = models.FloatField()
    amount = models.FloatField()

    class Meta:
        ordering = ['-time']


class BotPrice(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE
    )
    time = models.DateTimeField(
        auto_now_add=True
    )
    price = models.FloatField(null=True, blank=True)
    price_usd = models.FloatField(null=True, blank=True)
    bid_price = models.FloatField(null=True, blank=True)
    bid_price_usd = models.FloatField(null=True, blank=True)
    ask_price = models.FloatField(null=True, blank=True)
    ask_price_usd = models.FloatField(null=True, blank=True)
    unit = models.CharField(
        max_length=255,
    )

    class Meta:
        ordering = ['-time']


class BotBalance(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE
    )
    time = models.DateTimeField(
        auto_now_add=True
    )
    bid_available = models.FloatField()
    ask_available = models.FloatField()
    bid_on_order = models.FloatField()
    ask_on_order = models.FloatField()
    bid_available_usd = models.FloatField(null=True, blank=True)
    ask_available_usd = models.FloatField(null=True, blank=True)
    bid_on_order_usd = models.FloatField(null=True, blank=True)
    ask_on_order_usd = models.FloatField(null=True, blank=True)
    unit = models.CharField(
        max_length=255,
    )

    class Meta:
        ordering = ['-time']
