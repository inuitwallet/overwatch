from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import models
from django.utils import timezone

from overwatch.models import Bot


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

    def save(self, **kwargs):
        super().save(kwargs)

        async_to_sync(get_channel_layer().group_send)(
            'bot_{}'.format(self.bot.pk),
            {
                'type': 'get.heart.beats'
            }
        )

        async_to_sync(get_channel_layer().send)(
            'cloudwatch-logs',
            {
                "type": "get.cloudwatch.logs",
                "bot_pk": self.bot.pk,
                "sleep": 30
            },
        )


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

    def save(self, **kwargs):
        super().save(kwargs)

        async_to_sync(get_channel_layer().group_send)(
            'bot_{}'.format(self.bot.pk),
            {
                'type': 'get.errors',
            }
        )


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
    price_usd = models.FloatField(
        blank=True,
        null=True
    )
    amount = models.FloatField()
    updated = models.BooleanField(default=False)

    def __str__(self):
        return '{} {:.4f} {}@{:.4f} {}'.format(self.order_type, self.amount, self.quote, self.price, self.base)

    class Meta:
        ordering = ['-time']

    def save(self, **kwargs):
        super().save(kwargs)

        async_to_sync(get_channel_layer().group_send)(
            'bot_{}'.format(self.bot.pk),
            {
                'type': 'get.placed.orders',
            }
        )

        if not self.updated:
            async_to_sync(get_channel_layer().send)(
                'bot-order',
                {
                    "type": "calculate.usd.values",
                    "bot_order": self.pk,
                },
            )


class BotPriceManager(models.Manager):
    def get_closest_to(self, target):
        closest_greater_qs = self.filter(
            time__gt=target
        ).order_by(
            'date_time'
        )

        closest_less_qs = self.filter(
            time__lt=target
        ).order_by(
            '-date_time'
        )

        try:
            try:
                closest_greater = closest_greater_qs[0]
            except IndexError:
                return closest_less_qs[0]

            try:
                closest_less = closest_less_qs[0]
            except IndexError:
                return closest_greater_qs[0]
        except IndexError:
            raise self.model.DoesNotExist(
                "There is no closest value because there are no values."
            )

        if closest_greater.time - target > target - closest_less.time:
            return closest_less
        else:
            return closest_greater


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
        null=True,
        blank=True
    )
    updated = models.BooleanField(default=False)

    objects = BotPriceManager()

    def __str__(self):
        return '{}@{}'.format(self.bot, self.time)

    class Meta:
        ordering = ['-time']

    def save(self, **kwargs):
        super().save(kwargs)

        if not self.updated:
            async_to_sync(get_channel_layer().send)(
                'bot-price',
                {
                    "type": "calculate.usd.values",
                    "bot_price": self.pk,
                },
            )


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
    updated = models.BooleanField(default=False)

    def __str__(self):
        return '{}@{}'.format(self.bot, self.time)

    class Meta:
        ordering = ['-time']

    def save(self, **kwargs):
        super().save(kwargs)

        if not self.updated:
            async_to_sync(get_channel_layer().send)(
                'bot-balance',
                {
                    "type": "calculate.usd.values",
                    "bot_balance": self.pk,
                },
            )


class BotTrade(models.Model):
    bot = models.ForeignKey(
        Bot,
        on_delete=models.CASCADE
    )
    time = models.DateTimeField(
        default=timezone.now  # there is some historical data so need to be able to set this field
    )
    trade_id = models.CharField(
        max_length=255
    )
    trade_type = models.CharField(
        max_length=255,
    )
    bot_trade = models.BooleanField(default=True)
    price = models.FloatField()
    amount = models.FloatField()
    total = models.FloatField()
    age = models.DurationField(null=True, blank=True)
    target_price_usd = models.FloatField(null=True, blank=True)
    trade_price_usd = models.FloatField(null=True, blank=True)
    difference_usd = models.FloatField(null=True, blank=True)
    profit_usd = models.FloatField(null=True, blank=True)
    updated = models.BooleanField(default=False)

    def __str__(self):
        if self.profit_usd:
            return '{} {}={:.2f} USD'.format(self.trade_id, self.trade_type, self.profit_usd)
        else:
            return '{} {} {}@{}'.format(self.trade_id, self.trade_type, self.amount, self.price)

    class Meta:
        ordering = ['-time']
        unique_together = ('bot', 'trade_id')

    def save(self, **kwargs):
        super().save(kwargs)

        async_to_sync(get_channel_layer().group_send)(
            'bot_{}'.format(self.bot.pk),
            {
                'type': 'get.trades',
            }
        )

        if not self.updated:
            async_to_sync(get_channel_layer().send)(
                'bot-trade',
                {
                    "type": "calculate.usd.values",
                    'bot_trade': self.pk
                },
            )
