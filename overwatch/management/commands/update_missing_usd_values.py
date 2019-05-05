import logging

from django.core.management import BaseCommand

from overwatch.models import BotBalance, BotPlacedOrder, BotPrice, BotTrade


class Command(BaseCommand):
    """
    If there are missing usd calculations we can update them all by passing objects to the consumers
    """
    log = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '-l',
            '--limit',
            help='limit the number of blocks to process. useful in combination with -s',
            dest='limit',
            default=None
        )

    def handle(self, *args, **options):
        # bot_balance
        balances = BotBalance.objects.filter(updated=False).order_by('-time')[:int(options['limit'])]
        self.log.info('Processing {} BotBalances'.format(balances.count()))

        for balance in balances:
            self.log.info(balance)
            balance.save()

        # bot_price
        prices = BotPrice.objects.filter(updated=False).order_by('-time')[:int(options['limit'])]
        self.log.info('Processing {} BotPrices'.format(prices.count()))

        for price in prices:
            self.log.info(price)
            price.save()

        # bot_order
        orders = BotPlacedOrder.objects.filter(updated=False).order_by('-time')[:int(options['limit'])]
        self.log.info('Processing {} BotPlacedOrders'.format(orders.count()))

        for order in orders:
            self.log.info(order)
            order.save()

        # bot_trade
        trades = BotTrade.objects.filter(updated=False).order_by('-time')[:int(options['limit'])]
        self.log.info('Processing {} BotTrades'.format(trades.count()))

        for trade in trades:
            self.log.info(trade)
            trade.save()
