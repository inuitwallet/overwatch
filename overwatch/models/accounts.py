import datetime

import ccxt
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum
from django.utils.timezone import now
from encrypted_model_fields.fields import EncryptedCharField


class Exchange(models.Model):
    identifier = models.CharField(
        max_length=255,
        unique=True
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    exchange = models.CharField(
        max_length=255,
        help_text='The exchange name. This matches ',
        choices=[(exchange, exchange.title()) for exchange in ccxt.exchanges]
    )
    key = EncryptedCharField(
        max_length=255,
        help_text='database encrypted and hidden from display',
        blank=True,
        null=True
    )
    secret = EncryptedCharField(
        max_length=255,
        help_text='database encrypted and hidden from display',
        blank=True,
        null=True
    )

    def __str__(self):
        return '{} @ {}'.format(self.identifier, self.exchange.title())

    def total_profit(self, days=1):
        total_profit = 0

        for bot in self.bot_set.all():
            profit = bot.bottrade_set.filter(
                time__gte=now() - datetime.timedelta(days=days),
                profit_usd__isnull=False,
                bot_trade=True
            ).aggregate(
                profit=Sum('profit_usd')
            )['profit'] or 0

            total_profit += profit

        return total_profit

    def most_profitable_bot(self, days=1):
        most_profitable_bot = None
        max_profit = 0

        for bot in self.bot_set.all():
            profit = bot.bottrade_set.filter(
                time__gte=now() - datetime.timedelta(days=days),
                profit_usd__isnull=False,
                bot_trade=True
            ).aggregate(
                profit=Sum('profit_usd')
            )['profit'] or 0

            if profit > max_profit:
                max_profit = profit
                most_profitable_bot = bot

        return most_profitable_bot, max_profit


class AWS(models.Model):
    identifier = models.CharField(
        max_length=255,
        unique=True
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    region = models.CharField(
        max_length=255,
        default='eu-west-1'
    )
    access_key = EncryptedCharField(
        max_length=255,
        help_text='database encrypted',
        blank=True,
        null=True
    )
    secret_key = EncryptedCharField(
        max_length=255,
        help_text='database encrypted and hidden from display',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.identifier