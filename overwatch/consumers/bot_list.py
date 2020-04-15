import itertools
from functools import reduce

import pygal
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.template import Template, Context
from django.template.loader import render_to_string
from pygal.style import CleanStyle

from overwatch.models import Bot, Exchange


class BotListConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()
        async_to_sync(self.channel_layer.group_add)('bot_list', self.channel_name)
        self.user = self.scope["user"]

        self.update_days(1)
        #self.send_profits_chart()

        self.get_bots_data()

    def disconnect(self, code):
        self.close()

    def get_bots_data(self):
        for bot in Bot.objects.filter(active=True, owner=self.user):
            self.send_bot_data({'bot': bot.pk})

    def send_bot_data(self, event):
        try:
            bot = Bot.objects.get(pk=event['bot'])
        except Bot.DoesNotExist:
            return

        self.send_json(
            {
                'message_type': 'data_update',
                'bot': bot.pk,
                'activity': Template(
                    '{{ heartbeat | timesince }}'
                ).render(
                    Context({'heartbeat': bot.latest_heartbeat})
                ),
                'price': bot.rendered_price(usd=False),
                'price_usd': bot.rendered_price(usd=True),
                'market_price': bot.rendered_market_price(usd=True),
                'ask_balance': bot.rendered_ask_balance(on_order=True),
                'bid_balance': bot.rendered_bid_balance(on_order=True),
                'profit': bot.rendered_profit()
            }
        )

    def send_profits_chart(self):
        """
        Calculate daily profits over 30 days for all exchange accounts. Push as rendered chart
        """
        profits = {}

        for day in range(30):
            profits[day] = 0

        for exchange_account in Exchange.objects.filter(owner=self.user):
            for day in range(30):
                profits[day] += exchange_account.days_profit(day)

        chart = pygal.Line(
            x_title='Days Ago',
            y_title='Profit/Loss (USD)',
            show_legend=False,
            value_formatter=lambda x: '${:.8f}'.format(x),
            style=CleanStyle(
                font_family='googlefont:Raleway',
            ),
        )
        chart.x_labels = list(profits.keys())
        chart.add("Profits/Losses", list(profits.values()))

        self.send_json(
            {
                'message_type': 'profits_chart',
                'chart': '<embed type="image/svg+xml" src="{}" />'.format(
                    chart.render_data_uri()
                )
            }
        )

    def update_days(self, days):
        exchange_accounts = Exchange.objects.filter(owner=self.user)
        total_profit = reduce(lambda a, b: a + b, [e.total_profit(days) for e in exchange_accounts])

        balances = {}

        for exchange_account in exchange_accounts:
            if exchange_account.exchange not in balances:
                balances[exchange_account.exchange] = {}

            for bot in exchange_account.bot_set.all():
                if bot.base not in balances[exchange_account.exchange]:
                    balances[exchange_account.exchange][bot.base] = {'on_order': 0, 'available': 0}

                if bot.quote not in balances[exchange_account.exchange]:
                    balances[exchange_account.exchange][bot.quote] = {'on_order': 0, 'available': 0}

                latest_balance = bot.botbalance_set.first()

                balances[exchange_account.exchange][bot.base]['on_order'] += latest_balance.ask_on_order
                balances[exchange_account.exchange][bot.quote]['on_order'] += latest_balance.bid_on_order

                balances[exchange_account.exchange][bot.base]['available'] = latest_balance.ask_available
                balances[exchange_account.exchange][bot.quote]['available'] = latest_balance.bid_available

        self.send_json(
            {
                'message_type': 'update_dashboard',
                'days': days,
                'total_profit': render_to_string(
                    'overwatch/fragments/bot_list/total_profit.html',
                    {'profit': total_profit or 0}
                ),
                'contributing_bots': [
                    render_to_string('overwatch/fragments/bot_list/contributing_bot.html', {'bot': bot, 'days': days})
                    for bot in
                    sorted(list(Bot.objects.filter(owner=self.user)), key=lambda x: x.profit(days), reverse=True)
                    if bot.profit(days) != 0.0
                ],
                'balances': render_to_string('overwatch/fragments/bot_list/funds.html', {'balances': balances})
            }
        )

    def receive_json(self, content, **kwargs):
        message_type = content.get('message_type')

        if message_type == 'days_update':
            self.update_days(int(content.get('days')))
