import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta

import requests
from django.core.management import BaseCommand
from django.utils.timezone import make_aware

from overwatch.models import Bot, Exchange, BotTrade


class Command(BaseCommand):
    def make_request(self, account, url, post_params, tries=0):
        post_params["nonce"] = time.time() * 1000
        post_params["key"] = account.key
        response = requests.post(
            url="https://www.southxchange.com/api/{}".format(url),
            headers={
                "Content-Type": "application/json",
                "Hash": hmac.new(
                    account.secret.encode(),
                    msg=json.dumps(post_params).encode("utf-8"),
                    digestmod=hashlib.sha512,
                ).hexdigest(),
            },
            data=json.dumps(post_params),
        )

        # some responses indicate a temporary failue so we just try again
        retry = False

        if response.status_code == 429:
            retry = True

        if response.status_code == 400 and "Invalid API key or nonce" in response.text:
            retry = True

        if retry:
            print("Retry needed: {} - {}".format(response.status_code, response.text))
            tries += 1

            if tries >= 5:
                return False

            time.sleep(10)
            return self.make_request(account, url, post_params, tries)

        if response.status_code == requests.codes.no_content:
            # we got no content response.
            # cancel order returns this on success
            return True

        if response.status_code != requests.codes.ok:
            return False

        try:
            return response.json()
        except ValueError:
            return None

    def get_trades(self, account, market):
        trades = []

        exchange_trades = self.make_request(
            account,
            "listTransactions",
            {"PageSize": 50, "SortField": "Date", "Descending": True},
        )

        if not exchange_trades:
            return trades

        for trade in exchange_trades.get("Result", []):
            if trade.get("Type") != "trade":
                continue

            if trade.get("CurrencyCode") != market.split("/")[1].upper():
                continue

            if trade.get("OtherCurrency") != market.split("/")[0].upper():
                continue

            date = datetime.strptime(
                trade.get("Date").split(".")[0], "%Y-%m-%dT%H:%M:%S"
            )

            trades.append(
                {
                    "trade_type": "sell"
                    if float(trade.get("Amount", 0)) > float(0.0)
                    else "buy",
                    "trade_id": trade.get("TradeId"),
                    "trade_time": date,
                    "price": float(trade.get("Price")),
                    "amount": float(trade.get("OtherAmount")),
                    "total": float(trade.get("OtherAmount") * trade.get("Price")),
                    "age": 1,
                }
            )

        return sorted(trades, key=lambda x: x["trade_time"], reverse=True)

    def handle(self, *args, **options):
        account = Exchange.objects.get(exchange__iexact="southxchange")

        for bot in Bot.objects.filter(exchange_account=account):
            trades = self.get_trades(account, bot.market)
            for trade in trades:
                try:
                    trade = BotTrade.objects.get(
                        bot=bot, trade_id=trade.get("trade_id")
                    )
                    print("Found existing trade {}".format(trade))
                except BotTrade.DoesNotExist:
                    trade = BotTrade.objects.create(
                        bot=bot,
                        time=make_aware(trade.get("trade_time")),
                        trade_id=trade.get("trade_id"),
                        trade_type=trade.get("trade_type"),
                        price=trade.get("price"),
                        amount=trade.get("amount"),
                        total=trade.get("total"),
                        age=timedelta(seconds=int(trade.get("age"))),
                    )
                    print("Created trade {}".format(trade))
