import ccxt
from django.contrib.auth.models import User
from django.db import models
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