import datetime

import psycopg2
import requests
from django.conf import settings
from django.core.management import BaseCommand
from django.utils.timezone import make_aware

from overwatch.models import BotTrade, Bot


class Command(BaseCommand):
    @staticmethod
    def get_price(cur, dt):
        r = requests.get('https://price-aggregator.crypto-daio.co.uk/price/{}/{}'.format(cur, dt))

        if r.status_code != requests.codes.ok:
            print('Bad response from aggregator: {} {}'.format(r.status_code, r.reason))
            return None

        try:
            response = r.json()
        except ValueError:
            print('No Json: {}'.format(r.text))
            return None

        agg_price = response.get('moving_averages', {}).get('30_minute')

        if agg_price is None:
            print('No agg_price?: {}'.format(response))
            return None

        return agg_price

    def handle(self, *args, **options):
        conn = psycopg2.connect(
            dbname='completed_trades',
            user='liquidity_operations',
            password=settings.BITTREX_TRADES_PASSWORD,
            host=settings.BITTREX_TRADES_HOST,
            port=5432
        )

        curr = conn.cursor()

        prices = {'btc': {}, 'usnbt': {}}

        curr.execute(
            "select * from completed_trades order by datetime desc;"
        )
        rows = curr.fetchall()

        for row in rows:
            try:
                BotTrade.objects.get(trade_id=row[4])
                print('Trade already exists')
            except BotTrade.DoesNotExist:
                print(row)
                dt = row[0].strftime('%Y-%m-%dT%H:%M:%S')

                btc_price = prices['btc'].get(dt, self.get_price('btc', dt))

                if btc_price is None:
                    continue

                prices['btc'][dt] = btc_price

                usnbt_price = prices['usnbt'].get(dt, self.get_price('usnbt', dt))

                if usnbt_price is None:
                    continue

                prices['usnbt'][dt] = usnbt_price

                print('price = {}'.format(row[6]))
                print('btc price = {}'.format(btc_price))

                trade_price_usd = row[6] * btc_price

                print('trade_price = {}'.format(trade_price_usd))

                if row[5] == 'buy':
                    trade_diff_usd = usnbt_price - trade_price_usd
                else:
                    trade_diff_usd = trade_price_usd - usnbt_price
                # let's make a new trade
                name = '{}-{}'.format(row[2], row[3])
                bot = Bot.objects.get(name__iexact=name, exchange__iexact=row[1])

                trade = BotTrade.objects.create(
                    bot=bot,
                    time=make_aware(row[0]),
                    trade_id=row[4],
                    trade_type=row[5],
                    price=row[6],
                    amount=row[7],
                    total=row[8],
                    age=datetime.timedelta(seconds=row[9]),
                    target_price_usd=usnbt_price,
                    trade_price_usd=trade_price_usd,
                    difference_usd=trade_diff_usd,
                    profit_usd=trade_diff_usd * row[7]
                )

                print(trade)
