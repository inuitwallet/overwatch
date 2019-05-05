from django.core.management import BaseCommand

from overwatch.models import BotBalance, BotPlacedOrder, BotPrice, BotTrade


class Command(BaseCommand):
    """
    If there are missing usd calculations we can update them all by passing objects to the consumers
    """
    def handle(self, *args, **options):
        # bot_balance
        for balance in BotBalance.objects.filter(updated=False):
            balance.save()

        # bot_price
        for price in BotPrice.objects.filter(updated=False):
            price.save()

        # bot_order
        for order in BotPlacedOrder.objects.filter(updated=False):
            order.save()

        # bot_trade
        for trade in BotTrade.objects.filter(updated=False):
            trade.save()
