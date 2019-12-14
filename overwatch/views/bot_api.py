import datetime
import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse, HttpResponseNotFound, HttpResponseForbidden
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from overwatch.models import BotHeartBeat, Bot, BotPlacedOrder, BotPrice, BotBalance, BotTrade

"""
These classes represent API views that use direct bot authentication. 
They affect a single bot at a time meaning that data sent to them is tied to that single bot
"""


def handle_bot_api_auth(request_data, additional_keys=None):
    """
    Handle API Authentication for direct bot methods
    """
    keys = ['name', 'exchange', 'n', 'h']

    if additional_keys is not None:
        keys += additional_keys

    for key in keys:
        if key not in request_data:
            return False, JsonResponse({'success': False, 'error': 'no {} present in data'.format(key)})

    name = request_data.get('name')
    exchange = request_data.get('exchange')
    nonce = request_data.get('n')
    supplied_hash = request_data.get('h')

    try:
        bot = Bot.objects.get(name__iexact=name, exchange_account__exchange__iexact=exchange)
    except Bot.DoesNotExist:
        return False, HttpResponseNotFound(
            json.dumps(
                {'success': False, 'error': '\'{}@{}\' does not exist as a bot'.format(name, exchange)}
            ),
            content_type='application/json'
        )

    has_auth, reason = bot.auth(supplied_hash, name, exchange, nonce)

    if not has_auth:
        return False, HttpResponseForbidden(
            json.dumps({'success': False, 'error': reason}),
            content_type='application/json'
        )

    return True, bot


class BotApiConfigView(View):
    """
    Endpoint to allow a bot to request it's  config as a json object.
    Hitting this endpoint also registers a Bot Heartbeat
    """
    @staticmethod
    def get(request):
        success, bot = handle_bot_api_auth(request.GET)

        if not success:
            return bot

        # hitting this endpoint can act as a 'heartbeat' monitor for the bots
        # create a heartbeat object
        BotHeartBeat.objects.create(bot=bot)

        return JsonResponse(bot.serialize())


class BotApiPlacedOrderView(View):
    """
    Endpoint to allow bots to register a placed order
    """
    @staticmethod
    def post(request):
        success, bot = handle_bot_api_auth(request.POST, ['base', 'quote', 'order_type', 'price', 'amount'])

        if not success:
            # if the function returns False, then bot is set to a Response instance
            return bot

        BotPlacedOrder.objects.create(
            bot=bot,
            base=request.POST.get('base'),
            quote=request.POST.get('quote'),
            order_type=request.POST.get('order_type'),
            price=request.POST.get('price'),
            amount=request.POST.get('amount')
        )

        return JsonResponse({'success': True})

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class BotApiPricesView(View):
    """
    Endpoint to allow bots to register their operational prices
    """
    @staticmethod
    def post(request):
        success, bot = handle_bot_api_auth(request.POST, ['price', 'bid_price', 'ask_price', 'market_price'])

        if not success:
            # if the function returns False, then bot is set to a Response instance
            return bot

        BotPrice.objects.create(
            bot=bot,
            price=request.POST.get('price'),
            ask_price=request.POST.get('ask_price'),
            bid_price=request.POST.get('bid_price'),
            market_price=request.POST.get('market_price')
        )

        async_to_sync(get_channel_layer().group_send)(
            'bot_{}'.format(bot.pk),
            {
                'type': 'get.price.info',
            }
        )

        return JsonResponse({'success': True})

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class BotApiBalancesView(View):
    """
    Endpoint to allow bots to register their available balances
    """
    @staticmethod
    def post(request):
        success, bot = handle_bot_api_auth(
            request.POST, ['bid_available', 'ask_available', 'bid_on_order', 'ask_on_order', 'unit']
        )

        if not success:
            # if the function returns False, then bot is set to a Response instance
            return bot

        # Bittrex still lists USNBT as NBT
        unit = request.POST.get('unit')

        if unit.upper() == 'NBT':
            unit = 'USNBT'

        BotBalance.objects.create(
            bot=bot,
            bid_available=request.POST.get('bid_available'),
            ask_available=request.POST.get('ask_available'),
            bid_on_order=request.POST.get('bid_on_order'),
            ask_on_order=request.POST.get('ask_on_order'),
            unit=unit
        )

        return JsonResponse({'success': True})

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class BotApiTradeView(View):
    """
    Endpoint to allow for reporting of trades.
    """

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def post(request):
        success, bot = handle_bot_api_auth(
            request.POST, ['trade_time', 'trade_id', 'trade_type', 'price', 'amount', 'total', 'age']
        )

        if not success:
            # if the function returns False, then bot is set to a Response instance
            return bot

        try:
            BotTrade.objects.get(bot=bot, trade_id=request.POST.get('trade_id'))
            print('Got existing order with id {}'.format(request.POST.get('trade_id')))
        except BotTrade.DoesNotExist:
            trade = BotTrade.objects.create(
                bot=bot,
                time=request.POST.get('trade_time'),
                trade_id=request.POST.get('trade_id'),
                trade_type=request.POST.get('trade_type'),
                price=request.POST.get('price'),
                amount=request.POST.get('amount'),
                total=request.POST.get('total'),
                age=datetime.timedelta(seconds=int(request.POST.get('age'))),
            )
            print('Created trade {}'.format(trade))

        return JsonResponse({'success': True})

    @staticmethod
    def get(request):
        """
        return the latest trade id so the bot doesn't have to report all trades at once
        """
        success, bot = handle_bot_api_auth(request.GET)

        if not success:
            # if the function returns False, then bot is set to a Response instance
            return bot

        last_trade = BotTrade.objects.filter(bot=bot).order_by('time').last()

        if last_trade:
            return JsonResponse({'success': True, 'trade_id': last_trade.trade_id})

        return JsonResponse({'success': True, 'trade_id': None})
