import logging
from datetime import timedelta

from django.core.management import BaseCommand
from django.utils.timezone import now

from overwatch.models import BotTrade, Bot


class Command(BaseCommand):
    log = logging.getLogger(__name__)

    def add_arguments(self, parser):
        parser.add_argument(
            '-t',
            '--tim',
            help='The time to calculate the profit over',
            dest='time',
            default=None
        )
        parser.add_argument(
            '-b',
            '--bot',
            help='pk of bot to limit to',
            dest='bot',
            default=None
        )

    def handle(self, *args, **options):
        bot = None

        if options['bot']:
            try:
                bot = Bot.objects.get(pk=options['bot'])
                self.log.info('Using bot {}'.format(bot))
            except Bot.DoesNotExist:
                bot = None

        total_profit = 0

        trades = BotTrade.objects.all()

        if options['time']:
            trades = trades.filter(time__gte=now() - timedelta(days=int(options['time'])))

        earliest_trade = now()

        for t in trades:
            total_profit += t.profit_usd

            if t.time < earliest_trade:
                earliest_trade = t.time

        self.log.info('Profit since {} = ${}'.format(earliest_trade, total_profit))


