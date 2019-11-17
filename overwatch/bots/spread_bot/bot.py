import datetime
import json
import math
import os
import time
import random

from price_manager import PriceManager
from vigil import vigil_alert
from overwatch import Overwatch
import exchange_wrappers


EXCHANGE = os.environ['EXCHANGE']
wrapper = exchange_wrappers.get_wrapper(EXCHANGE)

overwatch = Overwatch(
    api_secret=os.environ['OVERWATCH_API_SECRET'],
    name=os.environ['BOT_NAME'],
    exchange=EXCHANGE
)

SLEEP_SHORT = int(os.environ['SLEEP_SHORT'])
SLEEP_MEDIUM = int(os.environ['SLEEP_MEDIUM'])
SLEEP_LONG = int(os.environ['SLEEP_LONG'])


def reset_order(order_id, pair, order_type, price, reverse, min_order_amount):
    """
    Cancel the order given by order_id
    Place an new order at price
    """
    print('Resetting order {}'.format(order_id))
    # cancel the order
    success = wrapper.cancel_order(order_id)

    # check we've cancelled the order
    if not success:
        print('Unable to cancel order {}'.format(order_id))
        return

    time.sleep(SLEEP_SHORT)

    jitter = random.triangular(0, pair.get('tolerance')) * price

    if reverse:
        jittered_price = (
            (price + jitter) if order_type == 'buy' else (price - jitter)
        )
    else:
        jittered_price = (
            (price + jitter) if order_type == 'sell' else (price - jitter)
        )

    amount = pair.get('order_amount') / price if reverse else pair.get('order_amount')


    # place the new order
    place = wrapper.place_order(
        base=pair.get('base'),
        quote=pair.get('quote'),
        order_type=order_type,
        price=jittered_price,
        amount=pair.get('order_amount') / price if reverse else pair.get('order_amount')  # noqa
    )

    if place:
        overwatch.record_placed_order(
            pair.get('base'),
            pair.get('quote'),
            order_type,
            jittered_price,
            pair.get('order_amount') / price if reverse else pair.get('order_amount')  # noqa
        )

    # TODO: if order placing fails. alert to vigil

    print('Order Placed: {}'.format(place))


def get_order_total(base, quote):
    """
    Get orders from exchange wrapper.
    Return the total amount on each side
    """
    orders = wrapper.get_open_orders(base, quote)

    if orders is None:
        return {'ask': None, 'bid': None}

    total = {'ask': 0, 'bid': 0}

    for order in orders['ask']:
        if total['ask'] is None:
            total['ask'] = order.get('amount')
            continue
        total['ask'] += order.get('amount')

    for order in orders['bid']:
        if total['bid'] is None:
            total['bid'] = order.get('amount')
            continue
        total['bid'] += order.get('amount')

    return total


def check_existing_orders(orders, pair, order_type, price, reverse, min_order_amount):
    """
    Check that existing order prices lie within the pair tolerance
    """
    print('')
    print('###########')
    print('#  Checking Existing {} Orders'.format(order_type.title()))
    print('')

    for order in orders:
        print(
            'Checking {} {} order {}'.format(
                pair.get('track'),
                order_type.title(),
                order
            )
        )

        order_tolerance = (
            max(order.get('price'), price) - min(order.get('price'), price)
        ) / price

        print('Got order tolerance of {} against {}'.format(
            order_tolerance,
            price
        ))

        # if the order price is outside of the allowed tolerance
        if order_tolerance > pair.get('tolerance'):
            reset_order(
                order.get('id'),
                pair,
                order_type.lower(),
                price,
                reverse,
                min_order_amount
            )
            time.sleep(SLEEP_MEDIUM)


def report_balances(pair, price, reverse):
    """
    Calculate the balances available and on order and report them to Overwatch
    """
    print('')
    print('###########')
    print('#  Reporting Balances')
    print('')

    totals_on_order = get_order_total(pair.get('base'), pair.get('quote'))

    if totals_on_order is None:
        print('failed to get totals on order when reporting balances')
        return

    bid_balance = wrapper.get_balance(pair.get('base'))

    if bid_balance is None:
        print('Failed to get bid_balance for {}'.format(pair.get('base')))
        bid_balance = 0

    bid_balance = float(bid_balance)

    ask_balance = wrapper.get_balance(pair.get('quote'))

    if ask_balance is None:
        print('Failed to get ask_balance for {}'.format(pair.get('quote')))
        ask_balance = 0

    ask_balance = float(ask_balance)

    # we should convert other currency to Nu currency for display
    if not reverse:
        # base currency is non-Nu
        bid_balance /= float(price)

    if reverse:
        # quote currency is non-Nu
        ask_balance *= float(price)
        # totals on order will be in quote currency (non-Nu in a reversed pair)
        for side in totals_on_order:
            totals_on_order[side] *= float(price)

    overwatch.record_balances(
        unit=pair.get('quote'),
        bid_available=bid_balance,
        ask_available=ask_balance,
        bid_on_order=totals_on_order['bid'],
        ask_on_order=totals_on_order['ask']
    )

def check_total_is_reached(pair, side, side_total, price, reverse, min_order_amount):
    """
    Check that the combined amount on order is equal to or more than the target
    If the combined amount comes up short,
    place a number of orders to reach the target.
    (We don't worry too much if the target isn't reached completely,
    the bot should place the missing order in 60 seconds time.
    We also don't worry if the target is slightly over)
    """
    print('')
    print('###########')
    print('#  Checking {} Wall Height'.format(side.title()))
    print('')

    total = get_order_total(pair.get('base'), pair.get('quote'))[side]

    if total is None:
        print('failed to get {} total'.format(side))
        return

    target = (side_total / price) if reverse else side_total
    step = (
        (pair.get('order_amount') / price)
        if reverse else
        pair.get('order_amount')
    )

    # TODO - Calculate Total and Target in terms of the currency they refer to

    print(
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
        balance = wrapper.get_balance(
            pair.get('base') if side == 'bid' else pair.get('quote')
        )

        if balance is None:
            print(
                'Failed to get balance for {}'.format(
                    pair.get('base') if side == 'bid' else pair.get('quote')
                )
            )
            return

        balance = float(balance)

        # calculate non Nu balance as Nu value using price
        if side == 'bid' and not reverse:
            balance /= float(price)

        if side == 'ask' and reverse:
            balance *= float(price)

        print('Got available balance of {}'.format(balance))

        # send alerts if balance is insufficient
        if balance < difference:
            print('!!! Not enough funds available to reach target !!!')
            print(
                '!!! Need {} to reach target of {} '
                'but only {:.4f} available !!!'.format(
                    difference,
                    target,
                    balance
                )
            )
            vigil_alert(
                alert_channel_id=os.environ['VIGIL_FUNDS_ALERT_CHANNEL_ID'],
                data={
                    'bot_name': os.environ['BOT_NAME'],
                    'currency': pair.get('base') if side == 'bid' else pair.get('quote'),
                    'exchange': EXCHANGE.title(),
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
            print('!!! Not enough funds to place an order !!!')
            step = balance * 0.9

        number_of_orders = 0

        if step < min_order_amount:
            print('!!! Minimum Order Amount not Reached !!!')
            print('{} < {}'.format(step, min_order_amount))
            return

        if step > 0:
            number_of_orders = math.ceil(difference/step)

        # place the orders needed
        if number_of_orders > 0:
            print('Placing {} orders to reach {} target {} from {}'.format(
                number_of_orders,
                side,
                target,
                total
            ))
            for x in range(number_of_orders):

                # Add some jitter to the order
                jitter = random.triangular(0, pair.get('tolerance')) * float(price)

                if reverse:
                    jittered_price = (
                        (price + jitter) if side == 'bid' else (price - jitter)
                    )
                else:
                    jittered_price = (
                        (price + jitter) if side == 'ask' else (price - jitter)
                    )

                place = wrapper.place_order(
                    base=pair.get('base'),
                    quote=pair.get('quote'),
                    order_type='buy' if side == 'bid' else 'sell',
                    price=jittered_price,
                    amount=step
                )

                if place:
                    overwatch.record_placed_order(
                        pair.get('base'),
                        pair.get('quote'),
                        'buy' if side == 'bid' else 'sell',
                        jittered_price,
                        pair.get('order_amount') / price if reverse else pair.get('order_amount')  # noqa
                    )

                print('Order Placed: {}'.format(place))
                time.sleep(SLEEP_SHORT)


def check_order_prices(pair, orders, price, side):
    print('')
    print('###########')
    print('#  Checking Existing {} Order Prices Against {} price {:.8f}'.format(
        side.title(),
        'Ask' if side == 'bid' else 'Bid',
        price
    ))
    print('')

    for order in orders:
        if side == 'bid':
            cancel = order['price'] > price
        else:
            cancel = order['price'] < price

        if cancel:
            print(
                'Cancelling {} {} Order {}'.format(
                    pair['track'],
                    side.title(),
                    order
                )
            )
            wrapper.cancel_order(order.get('id'))


def check_orders_over_target(pair, side, side_total, price, orders, reverse):
    print('')
    print('###########')
    print('#  Checking For {} Orders Over Target'.format(side.title()))
    print('')

    total = get_order_total(pair.get('base'), pair.get('quote'))[side]

    if total is None:
        print('failed to get {} total'.format(side))
        return

    target = (
        (side_total + pair.get('order_amount')) / price
        if reverse else
        side_total + pair.get('order_amount')
    )
    order_amount = (
        pair.get('order_amount') / price
        if reverse else
        pair.get('order_amount')
    )

    print('{}: Total = {}, Target = {}'.format(side.title(), total, target))

    if total > target:
        # total on side is too high so remove bottom orders
        difference = total - target
        num = math.floor(difference / order_amount )
        print('Got Diff of {}. Removing {} orders'.format(difference, num))

        remove_orders = sorted(
            orders,
            key=lambda x: x['price'],
            reverse=(side == 'ask')
        )

        print('Remove Orders {}'.format(remove_orders[:num]))

        for order in remove_orders[:num]:
            print(
                'Cancelling {} {} Order {}'.format(
                    pair['track'],
                    side.title(),
                    order
                )
            )
            wrapper.cancel_order(order.get('id'))


def main(event, context):
    start_time = time.time()
    pair = overwatch.get_config()

    if pair.get('stop'):
        print('STOP SIGNAL RECEIVED')
        wrapper.cancel_all_orders(pair)
        return

    print('###########')
    print('#  Working on {}_{}'.format(pair.get('base'), pair.get('quote')))
    print('# {}'.format(datetime.datetime.now()))
    print('###########')
    # later maths relies on whether the pair is reversed or not
    reverse = (pair.get('quote') == pair.get('track'))
    print('Reversed Pair = {}'.format(reverse))
    # Get price
    print('###########')
    print('#  Getting Prices')

    market_price = wrapper.get_last_price(pair)

    if pair.get('market_price'):
        print('Using Market Price')
        price = market_price
    else:
        pm = PriceManager(pair.get('track_url'), pair.get('peg_url'))
        price = pm.get_price(pair.get('track'), pair.get('peg'), reverse)

    if price is None:
        print('No Price Available!')
        wrapper.cancel_all_orders(pair)
        report_balances(pair, price, reverse)
        return

    bid_price = float(price) - (float(pair.get('fee') + pair.get('bid_spread')) * float(price))
    ask_price = float(price) + (float(pair.get('fee') + pair.get('ask_spread')) * float(price))

    print('Bid Price set to {:.8f}'.format(bid_price))
    print('Ask Price set to {:.8f}'.format(ask_price))

    # send prices to Overwatch
    overwatch.record_price(
        price=price,
        bid_price=bid_price,
        ask_price=ask_price,
        market_price=market_price
    )

    time.sleep(SLEEP_SHORT)

    # cancel orders with overlapping prices
    orders = wrapper.get_open_orders(pair.get('base'), pair.get('quote'))

    if orders is None:
        print('failed to get open orders before checking prices')
        wrapper.cancel_all_orders(pair)
        report_balances(pair, price, reverse)
        return

    check_order_prices(pair, orders['bid'], ask_price, 'bid')
    check_order_prices(pair, orders['ask'], bid_price, 'ask')

    time.sleep(SLEEP_SHORT)

    # cancel orders placed over side target
    orders = wrapper.get_open_orders(pair.get('base'), pair.get('quote'))

    if orders is None:
        print('failed to get open orders before checking breached target')
        wrapper.cancel_all_orders(pair)
        report_balances(pair, price, reverse)
        return

    check_orders_over_target(pair, 'bid', pair.get('total_bid'), bid_price, orders['bid'], reverse)  # noqa
    check_orders_over_target(pair, 'ask', pair.get('total_ask'), ask_price, orders['ask'], reverse)  # noqa

    time.sleep(SLEEP_SHORT)

    # check that existing orders are placed within the pair price tolerance
    orders = wrapper.get_open_orders(pair.get('base'), pair.get('quote'))

    if orders is None:
        print('failed to get open orders before checking existing orders')
        wrapper.cancel_all_orders(pair)
        report_balances(pair, price, reverse)
        return

    # get the minimum order amount
    min_order_amount = wrapper.get_min_trade_size(pair.get('base'), pair.get('quote'))

    check_existing_orders(orders['bid'], pair, 'buy', bid_price, reverse, min_order_amount)
    check_existing_orders(orders['ask'], pair, 'sell', ask_price, reverse, min_order_amount)

    time.sleep(SLEEP_SHORT)

    # check that side targets are reached
    check_total_is_reached(pair, 'bid', pair.get('total_bid'), bid_price, reverse, min_order_amount)  # noqa
    check_total_is_reached(pair, 'ask', pair.get('total_ask'), ask_price, reverse, min_order_amount)  # noqa

    print('')

    # report balances to Overwatch
    report_balances(pair, price, reverse)

    time.sleep(SLEEP_LONG)

    print('###########')
    print('#  Getting Trades')

    last_trade_id = overwatch.get_last_trade_id()

    for trade in wrapper.get_trades(pair):
        if trade.get('trade_id') == last_trade_id:
            break

        overwatch.record_trade(
            trade.get('trade_time'),
            trade.get('trade_id'),
            trade.get('trade_type'),
            trade.get('price'),
            trade.get('amount'),
            trade.get('total'),
            trade.get('age')
        )

    print('')
    print('###########')
    print(' COMPLETE IN {} Seconds'.format(time.time() - start_time))
    print('{}'.format(datetime.datetime.now()))
    print('###########')

    return 'All Done'
