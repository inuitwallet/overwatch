import logging

from django.core.management import BaseCommand

from overwatch.models import BotBalance, BotPlacedOrder, BotPrice, BotTrade


class Command(BaseCommand):
    """
    If there are missing usd calculations we can update them all by passing objects to the consumers
    """
    log = logging.getLogger(__name__)

    def handle(self, *args, **options):
        # bot_balance
        self.log.info('Processing BotBalances')

        for balance in BotBalance.objects.filter(updated=False):
            self.log.info(balance)
            balance.save()

        # bot_price
        self.log.info('Processing BotPrices')

        for price in BotPrice.objects.filter(updated=False):
            self.log.info(price)
            price.save()

        # bot_order
        self.log.info('Processing BotPlacedOrders')

        for order in BotPlacedOrder.objects.filter(updated=False):
            self.log.info(order)
            order.save()

        # bot_trade
        self.log.info('Processing BotTrades')

        for trade in BotTrade.objects.filter(updated=False):
            self.log.info(trade)
            trade.save()
