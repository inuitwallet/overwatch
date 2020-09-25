import logging

from django.core.management import BaseCommand

from overwatch.models import BotBalance, BotPlacedOrder, BotPrice, BotTrade, Bot


class Command(BaseCommand):
    """
    If there are missing usd calculations we can update them all by passing objects to the consumers
    """

    log = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            "-l",
            "--limit",
            help="limit the number of blocks to process. useful in combination with -s",
            dest="limit",
            default=None,
        )
        parser.add_argument(
            "-b", "--bot", help="pk of bot to limit to", dest="bot", default=None
        )

    def handle(self, *args, **options):
        bot = None

        if options["bot"]:
            try:
                bot = Bot.objects.get(pk=options["bot"])
                self.log.info("Using bot {}".format(bot))
            except Bot.DoesNotExist:
                bot = None

        limit = options["limit"]

        # bot_balance
        balances = BotBalance.objects.filter(updated=False).order_by("-time")

        if bot:
            balances.filter(bot=bot)

        if limit:
            balances = balances[: int(limit)]

        self.log.info("Processing {} BotBalances".format(balances.count()))

        for balance in balances:
            self.log.info(balance)
            balance.save()

        # bot_price
        prices = BotPrice.objects.filter(updated=False).order_by("-time")

        if bot:
            prices.filter(bot=bot)

        if limit:
            prices = prices[: int(limit)]

        self.log.info("Processing {} BotPrices".format(prices.count()))

        for price in prices:
            self.log.info(price)
            price.save()

        # bot_order
        orders = BotPlacedOrder.objects.filter(updated=False).order_by("-time")

        if bot:
            orders.filter(bot=bot)

        if limit:
            orders = orders[: int(limit)]

        self.log.info("Processing {} BotPlacedOrders".format(orders.count()))

        for order in orders:
            self.log.info(order)
            order.save()

        # bot_trade
        trades = BotTrade.objects.filter(updated=False).order_by("-time")

        if bot:
            trades.filter(bot=bot)

        if limit:
            trades = trades[: int(limit)]

        self.log.info("Processing {} BotTrades".format(trades.count()))

        for trade in trades:
            self.log.info(trade)
            trade.save()
