import datetime
import math
import os
import sys
import time
import random
import ccxt
import logging

from price_manager import PriceManager
from vigil import vigil_alert
from overwatch import Overwatch


class Bot(object):
    def __init__(self, name, exchange):
        # get a decent logger#
        self.logger = self.setup_logging()

        # set the bot name and exchange
        self.name = name
        self.exchange = exchange

        # instantiate the Overwatch connection
        self.overwatch = None
        self.get_overwatch_wrapper()

        # get the bot config from Overwatch
        self.config = self.overwatch.get_config()

        if not self.config:
            self.logger.error('Failed to get Overwatch config')
            sys.exit(1)

        self.symbol = self.config.get('market')

        # instantiate the ccxt wrapper for this bots exchange
        self.wrapper = None
        self.market = None
        self.get_exchange_wrapper()

        # set the sleep values
        self.sleep_short = int(os.environ.get('SLEEP_SHORT', 2))
        self.sleep_medium = int(os.environ.get('SLEEP_MEDIUM', 3))
        self.sleep_long = int(os.environ.get('SLEEP_LONG', 5))

        self.logger.info('Working on {}@{}'.format(self.symbol, self.exchange))
        self.logger.info('{}'.format(datetime.datetime.now()))

        # get the prices
        self.price = 0
        self.buy_price = 0
        self.sell_price = 0
        self.quote_price = None
        self.base_price = None
        self.peg_price = None
        self.get_prices()

        # calculate the limits in base currency
        self.order_amount = 0
        self.total_bid = 0
        self.total_ask = 0
        self.get_limits()

    @staticmethod
    def setup_logging():
        logger = logging.getLogger()
        for h in logger.handlers:
            logger.removeHandler(h)

        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))

        logger.addHandler(h)
        logger.setLevel(logging.INFO)

        return logger

    def get_exchange_wrapper(self):
        """
        Instantiate the CCXT exchange wrapper
        """
        wrapper_class = getattr(ccxt, self.exchange.lower())
        self.wrapper = wrapper_class(
            {
                'apiKey': os.environ['API_KEY'],
                'secret': os.environ['API_SECRET'],
                'nonce': ccxt.Exchange.milliseconds
            }
        )
        self.market = next(m for m in self.wrapper.fetch_markets() if m.get('symbol') == self.symbol)

    def get_overwatch_wrapper(self):
        """
        Instantiate the Overwatch Wrapper
        """
        self.overwatch = Overwatch(
            api_secret=os.environ['OVERWATCH_API_SECRET'],
            name=self.name,
            exchange=self.exchange
        )

    def get_prices(self):
        """
        Get the current sell and buy prices
        :return: 
        """
        self.logger.info('###########')
        self.logger.info('Getting Price')
        market_price = self.wrapper.fetch_ticker(self.symbol).get('last')
        known_config = False

        if self.config.get('use_market_price'):
            # just opperate using the market price
            self.logger.info('Using Market Price')
            price = float(market_price)
            known_config = True
        else:
            # otherwise there are 4 PEG options.
            # 1. The peg currency is the quote currency: Price = 1/(Quote Price/Base Price)
            # 2. The peg currency is the base currency: Price = Base Price / Quote Price
            # 3. The peg currency is neither and the quote is being pegged to it: Price = Base Price / Peg Price
            # 4. The peg currency is neither and the base is being pegged to it: Price = Peg Price / Quote Price
            pm = PriceManager()
            self.quote_price = pm.get_price(self.market.get('quote'), self.config.get('quote_price_url'))
            self.base_price = pm.get_price(self.market.get('base'), self.config.get('base_price_url'))
            self.peg_price = pm.get_price(self.config.get('peg_currency').upper(), self.config.get('peg_price_url'))

            price = None

            if self.config.get('peg_currency', 'peg').upper() == self.market.get('quote', 'quote').upper():
                known_config = True
                # this is option 1

                if self.quote_price is not None and self.base_price is not None:
                    price = 1/(self.quote_price/self.base_price)

            if self.config.get('peg_currency', 'peg').upper() == self.market.get('base', 'base').upper():
                known_config = True
                # this is option 2

                if self.quote_price is not None and self.base_price is not None:
                    price = self.base_price / self.quote_price

            if (
                    self.config.get('peg_currency', '').upper() != self.market.get('base', '').upper()
                    and self.config.get('peg_currency', '').upper() != self.market.get('quote', '').upper()
            ):
                if self.config.get('peg_side', '').lower() == 'quote':
                    known_config = True
                    # this is option 3

                    if self.base_price is not None and self.peg_price is not None:
                        price = self.base_price / self.peg_price

                if self.config.get('peg_side', '').lower() == 'base':
                    known_config = True
                    # this is option 4

                    if self.quote_price is not None and self.peg_price is not None:
                        price = self.peg_price / self.quote_price

        if not known_config:
            self.logger.warning('Not a known Bot Config!')
            self.cancel_all_orders()
            self.report_balances()
            return

        if price is None:
            self.logger.warning('No Price Available!')
            self.cancel_all_orders()
            self.report_balances()
            return

        self.price = price
        self.buy_price = float(price) - (float(self.config.get('fee') + self.config.get('bid_spread')) * float(price))
        self.sell_price = float(price) + (float(self.config.get('fee') + self.config.get('ask_spread')) * float(price))

        self.logger.info('Buy Price set to {:.8f}'.format(self.buy_price))
        self.logger.info('Sell Price set to {:.8f}'.format(self.sell_price))

        # send prices to Overwatch
        self.overwatch.record_price(
            price=price,
            bid_price=self.buy_price,
            ask_price=self.sell_price,
            market_price=market_price
        )

    def get_limits(self):
        """
        Order amount, Total Ask and total Bid come to the Bot in USD. We need them in 'Quote' currency
        """
        print('getting limits')
        if self.quote_price is not None:
            self.order_amount = self.config.get('order_amount', 0) / self.quote_price
            self.total_ask = self.config.get('total_ask', 0) / self.quote_price
            self.total_bid = self.config.get('total_bid', 0) / self.quote_price
            print('order amount: {}'.format(self.order_amount))
            print('total ask: {}'.format(self.total_ask))
            print('total bid: {}'.format(self.total_bid))
        
    def get_open_orders(self):
        """
        get the currently open orders
        """
        return self.wrapper.fetch_open_orders(self.symbol)

    def get_base(self) -> str:
        """
        return the base currency based on if the bot is reversed or not
        """
        return self.market.get('base')

    def get_quote(self) -> str:
        """
        return the quote currency based on if the bot is reversed or not
        """
        return self.market.get('quote')

    def get_jittered_price(self, price, order_type):
        """
        Use the tolerance to calculate a random price +/- the given price
        """
        jitter = random.triangular(0, self.config.get('tolerance')) * price
        return (price + jitter) if order_type == 'sell' else (price - jitter)

    def check_amount(self, amount):
        amount_min = self.market.get('limits', {}).get('amount', {}).get('min')
        amount_max = self.market.get('limits', {}).get('amount', {}).get('max')
        
        if amount_min:
            if amount < amount_min:
                self.logger.warning('Minimum order amount not reached: {} < {}'.format(amount, amount_min))
                return False
            
        if amount_max:
            if amount > amount_max:
                self.logger.warning('Maximum order amount breached: {} > {}'.format(amount, amount_max))
                return False
            
        return True

    def check_price(self, price):
        price_min = self.market.get('limits', {}).get('price', {}).get('min')
        price_max = self.market.get('limits', {}).get('price', {}).get('max')

        if price_min:
            if price < price_min:
                self.logger.warning('Minimum order price not reached: {} < {}'.format(price, price_min))
                return False

        if price_max:
            if price > price_max:
                self.logger.warning('Maximum order price breached: {} > {}'.format(price, price_max))
                return False

        return True
    
    def check_cost(self, amount, price):
        cost = amount * price
        
        cost_min = self.market.get('limits', {}).get('cost', {}).get('min')
        cost_max = self.market.get('limits', {}).get('cost', {}).get('max')

        if cost_min:
            if cost < cost_min:
                self.logger.warning('Minimum order cost not reached: {} < {}'.format(cost, cost_min))
                return False

        if cost_max:
            if cost > cost_max:
                self.logger.warning('Maximum order cost breached: {} > {}'.format(cost, cost_max))
                return False

        return True

    def place_order(self, order_type, price, amount):
        """
        place an order based on the order_type
        """
        if not self.check_amount(amount):
            return
        
        if not self.check_price(price):
            return

        if not self.check_cost(amount, price):
            return

        place = None

        if order_type == 'buy':
            try:
                # place = self.wrapper.create_limit_buy_order(self.symbol, amount, price)
                self.logger.info('Placing Buy order of {} @ {}'.format(amount, price))
            except Exception as e:
                self.logger.error('Placing limit buy order failed: {}'.format(e))
                return
        else:
            try:
                # place = self.wrapper.create_limit_sell_order(self.symbol, amount, price)
                self.logger.info('Placing Sell order of {} @ {}'.format(amount, price))
            except Exception as e:
                self.logger.error('Placing limit sell order failed: {}'.format(e))
                return

        if place:
            # TODO - order_amount, buy_limit and sell_limit are in USD now. need to convert to base
            self.overwatch.record_placed_order(
                self.config.get('base'),
                self.config.get('quote'),
                order_type,
                price,
                self.order_amount
            )

        # TODO: if order placing fails. alert to vigil
        self.logger.info('Order Placed: {}'.format(place.get('id')))

    def reset_order(self, order_id, order_type, price):
        """
        Cancel the order given by order_id
        Place an new order at price
        """
        self.logger.info('Resetting order {}'.format(order_id))

        # cancel the order
        success = self.wrapper.cancel_order(order_id)

        # check we've cancelled the order
        if not success:
            self.logger.error('Unable to cancel order {}'.format(order_id))
            return

        time.sleep(self.sleep_short)

        jittered_price = self.get_jittered_price(price, order_type)
        amount = self.order_amount

        self.place_order(order_type, jittered_price, amount)

    def get_order_total(self):
        """
        Get orders from exchange wrapper.
        Return the total amount on each side
        """
        total = {'sell': 0, 'buy': 0}

        for order in self.get_open_orders():
            if order.get('side') == 'buy':
                total['buy'] += order.get('amount')
            else:
                total['sell'] += order.get('amount')

        return total

    def get_available_balance(self, currency):
        """
        Return the available balance for the given currency
        """
        balances = self.wrapper.fetch_balance()

        for cur in balances:
            if cur == currency.upper():
                return balances.get(cur).get('free', 0.0)

        return 0.0

    def check_existing_orders(self):
        orders = self.get_open_orders()
        self.check_existing_side_orders(orders, 'buy', self.buy_price)
        self.check_existing_side_orders(orders, 'sell', self.sell_price)

    def check_existing_side_orders(self, orders, order_type, price):
        """
        Check that existing order prices lie within the pair tolerance
        """
        self.logger.info('Checking Existing {} Orders'.format(order_type.title()))

        for order in orders:
            if order.get('side') != order_type:
                continue

            self.logger.info(
                'Checking {} {} order {}'.format(
                    self.config.get('track'),
                    order_type.title(),
                    order.get('id')
                )
            )

            order_tolerance = (max(order.get('price'), price) - min(order.get('price'), price)) / price

            self.logger.info(
                'Got an order tolerance of {} against {}'.format(
                    order_tolerance,
                    self.config.get('tolerance')
                )
            )

            # if the order price is outside of the allowed tolerance
            if order_tolerance > self.config.get('tolerance'):
                self.reset_order(
                    order.get('id'),
                    order_type.lower(),
                    price
                )
                time.sleep(self.sleep_medium)

    def report_balances(self):
        """
        Calculate the balances available and on order and report them to Overwatch
        """
        self.logger.info('Reporting Balances')

        totals_on_order = self.get_order_total()

        buy_balance = self.get_available_balance(self.get_quote())
        sell_balance = self.get_available_balance(self.get_base())

        self.overwatch.record_balances(
            unit=self.get_base(),
            bid_available=buy_balance,
            ask_available=sell_balance,
            bid_on_order=totals_on_order['buy'],
            ask_on_order=totals_on_order['sell']
        )

    def check_total_is_reached(self):
        self.check_side_total_is_reached('buy', self.total_bid, self.buy_price)
        self.check_side_total_is_reached('sell', self.total_ask, self.sell_price)

    def check_side_total_is_reached(self, side, side_total, price):
        """
        Check that the combined amount on order is equal to or more than the target
        If the combined amount comes up short,
        place a number of orders to reach the target.
        (We don't worry too much if the target isn't reached completely,
        the bot should place the missing order in 60 seconds time.
        We also don't worry if the target is slightly over)
        """
        self.logger.info('Checking {} Wall Height'.format(side.title()))

        total = self.get_order_total()[side]

        target = side_total
        step = self.order_amount

        self.logger.info(
            '{}: Total = {}, Target = {}, step = {}'.format(
                side.title(),
                total,
                target,
                step
            )
        )

        if total < target:
            # calculate the difference between current total and the target
            difference = target - total
            # get the balance Available
            check_currency = self.config.get('base') if side == 'buy' else self.config.get('quote')
            balance = self.get_available_balance(check_currency)

            self.logger.info('Got available balance of {}'.format(balance))

            # we can only place orders up to the value of 'balance'
            if balance < difference:
                # then warn
                self.logger.warning('Not enough funds available to reach target')
                self.logger.warning(
                    'Need {} to reach target of {} '
                    'but only {:.4f} available'.format(
                        difference,
                        target,
                        balance
                    )
                )
                vigil_alert(
                    alert_channel_id=os.environ['VIGIL_FUNDS_ALERT_CHANNEL_ID'],
                    data={
                        'bot_name': self.name,
                        'currency': self.config.get('base') if side == 'buy' else self.config.get('quote'),
                        'exchange': self.exchange.title(),
                        'target_amount': target,
                        'amount_on_order': total,
                        'amount_available': balance
                    }
                )
                # set difference to == balance
                difference = balance

            # calculate the number of orders we need to make the total
            # use balance instead of step amount if not enough is available
            if balance < step:
                self.logger.warning('Not enough funds to place a full order. Attempting to place available balance')
                # setting step to balance exactly can cause api errors
                step = balance * 0.9

            number_of_orders = 0

            if step > 0:
                number_of_orders = math.ceil(difference/step)

            # place the orders needed
            if number_of_orders > 0:
                self.logger.info('Placing {} orders to reach {} target {} from {}'.format(
                    number_of_orders,
                    side,
                    target,
                    total
                ))
                for x in range(number_of_orders):
                    jittered_price = self.get_jittered_price(price, side)
                    self.place_order(side, jittered_price, step)
                    time.sleep(self.sleep_short)

    def check_order_prices(self):
        orders = self.get_open_orders()
        self.check_order_side_prices(orders, 'buy', self.buy_price)
        self.check_order_side_prices(orders, 'sell', self.sell_price)

    def check_order_side_prices(self, orders, side, price):
        """
        For each order, check that the price it is placed at is correct.
        Cancel the order if it isn't
        """
        self.logger.info('Checking Existing {} Order Prices Against {} price {:.8f}'.format(
            side.title(),
            'sell' if side == 'buy' else 'buy',
            price
        ))

        for order in orders:
            if order.get('side') != side:
                continue

            if side == 'buy':
                cancel = (float(order['price']) > price)
            else:
                cancel = (float(order['price']) < price)

            if cancel:
                self.logger.info(
                    'Cancelling {} {} Order {} @ {}'.format(
                        self.config.get('track'),
                        side.title(),
                        order['id'],
                        order['price']
                    )
                )
                self.wrapper.cancel_order(order.get('id'))

    def check_orders_over_target(self):
        orders = self.get_open_orders()
        self.check_orders_over_target_side(orders, 'buy', self.total_bid, self.buy_price)
        self.check_orders_over_target_side(orders, 'sell', self.total_ask, self.sell_price)

    def check_orders_over_target_side(self, orders, side, side_total, price):
        """
        Cancel any orders that take the side total to greater than the target
        """
        self.logger.info('Checking For {} Orders Over Target'.format(side.title()))

        total = self.get_order_total()[side]

        target = side_total + self.order_amount

        self.logger.info('{}: Total = {}, Target = {}'.format(side.title(), total, target))

        if total > target:
            # total on side is too high so remove bottom orders
            difference = total - target
            num = math.floor(difference / self.order_amount)
            self.logger.info('Got Diff of {}. Removing {} orders'.format(difference, num))

            remove_orders = sorted(
                [o for o in orders if o.get('side') == side],
                key=lambda x: x['price'],
                reverse=(side == 'sell')
            )

            self.logger.info('Remove {} Orders'.format(len(remove_orders[:num])))

            for order in remove_orders[:num]:
                self.logger.info(
                    'Cancelling {} {} Order {}'.format(
                        self.config.get('track'),
                        side.title(),
                        order.get('id')
                    )
                )
                self.wrapper.cancel_order(order.get('id'))

    def cancel_all_orders(self):
        """
        In an emergency, cancel all the orders
        """
        for order in self.wrapper.fetch_open_orders(self.symbol):
            self.wrapper.cancel_order(order.get('id'))
            time.sleep(self.sleep_short)

    def get_trades(self):
        """
        Get any new trades and report them to Overwatch
        """
        if not self.wrapper.has['fetchMyTrades']:
            self.logger.warning('fetchMyTrades is not implemented on this exchange')
            return

        self.logger.info('Getting Trades')

        last_trade_id = self.overwatch.get_last_trade_id()

        for trade in self.wrapper.fetch_my_trades(self.symbol):
            if trade.get('id') == last_trade_id:
                break

            self.overwatch.record_trade(
                trade.get('datetime'),
                trade.get('id'),
                trade.get('side'),
                trade.get('price'),
                trade.get('amount'),
                trade.get('cost'),
                0
            )

    def run(self):
        start_time = time.time()

        if self.config.get('stop'):
            # we should cancel all the orders
            self.logger.warning('STOP SIGNAL RECEIVED')
            self.cancel_all_orders()
            return

        # cancel orders with prices which overlap the calculated price
        self.check_order_prices()
        time.sleep(self.sleep_short)

        # cancel orders placed over side target
        self.check_orders_over_target()
        time.sleep(self.sleep_short)

        # check that existing orders are placed within the price tolerance
        self.check_existing_orders()
        time.sleep(self.sleep_short)

        # check that side targets are reached
        self.check_total_is_reached()
        time.sleep(self.sleep_short)

        # report balances to Overwatch
        self.report_balances()
        time.sleep(self.sleep_long)

        # report new trades to Overwatch
        self.get_trades()

        self.logger.info('COMPLETE IN {} Seconds'.format(time.time() - start_time))


def main(event, context):
    Bot(
        os.environ.get('BOT_NAME'),
        os.environ.get('EXCHANGE'),
    ).run()

    return 'Complete'


if __name__ == '__main__':
    main(None, None)
