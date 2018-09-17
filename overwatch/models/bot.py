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
        help_text='The base currency of the pair'
    )
    quote = models.CharField(
        max_length=255,
        help_text='The quote currency of the pair'
    )
    track = models.CharField(
        max_length=255,
        help_text='The currency to track. This determines if the pair is reversed or not'
    )
    peg = models.CharField(
        max_length=255,
        help_text='The currency to peg to'
    )
    tolerance = models.FloatField(
        help_text=''
    )
    fee = models.FloatField()
    order_amount = models.FloatField()
    total_bid = models.FloatField()
    total_ask = models.FloatField()
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
    price = models.FloatField()
    unit = models.CharField(
        max_length=255,
    )
    side = models.CharField(
        max_length=255,
    )

    class Meta:
        ordering = ['-time']
