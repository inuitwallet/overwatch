import ccxt
from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from overwatch.models import Bot


@receiver(pre_save, sender=Bot)
def check_currencies(sender, instance, **kwargs):
    # we should make sure this pair exists at the exchange

    exchange = getattr(ccxt, instance.exchange)()

    for market in exchange.fetch_markets():
        if market['base'].upper() == instance.base.upper and market['quote'].upper() == instance.quote.upper():
            return

        if market['base'].upper() == instance.quote.upper and market['quote'].upper() == instance.base.upper():
            # raise ValidationError(
            #     'There is a {} pair. You possibly have base and quote reversed'.format(market['symbol'])
            # )
            return

    return

    raise ValidationError('No {} market matching {}/{} found'.format(instance.exchange, instance.base, instance.quote))
