import json
from uuid import UUID

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseNotFound, HttpResponseForbidden
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from overwatch.models import BotError, ApiProfile, Bot

"""
These classes represent API views that use direct bot authentication. 
They affect a single bot at a time meaning that data sent to them is tied to that single bot
"""


def handle_bot_user_api_auth(request, additional_keys=None):
    """
    Handle API Authentication for methods which authenticate through a user account instead of a direct bot
    """
    keys = ['name', 'exchange', 'api_user', 'n', 'h']

    if additional_keys is not None:
        keys += additional_keys

    for key in keys:
        if key not in request.POST:
            return False, JsonResponse({'success': False, 'error': 'no {} present in POST data'.format(key)})

    nonce = request.POST.get('n')
    supplied_hash = request.POST.get('h')
    api_user = request.POST.get('api_user')

    try:
        api_profile = ApiProfile.objects.get(api_user=UUID(api_user))
    except User.DoesNotExist:
        return False,  HttpResponseNotFound(
            json.dumps(
                {'success': False, 'error': '\'{}\' does not exist as an api user'.format(api_user)}
            ),
            content_type='application/json'
        )

    has_auth, reason = api_profile.auth(supplied_hash, nonce)

    if not has_auth:
        return False, HttpResponseForbidden(
            json.dumps({'success': False, 'error': reason}),
            content_type='application/json'
        )

    name = request.POST.get('name')
    exchange = request.POST.get('exchange')

    try:
        bot = Bot.objects.get(name__iexact=name, exchange_account__exchange__iexact=exchange)
    except Bot.DoesNotExist:
        return False, HttpResponseNotFound(
            json.dumps(
                {'success': False, 'error': '\'{}@{}\' does not exist as a bot'.format(name, exchange)}
            ),
            content_type='application/json'
        )

    return True, bot


class BotUserApiErrorsView(View):
    @staticmethod
    def post(request):
        success, bot = handle_bot_user_api_auth(request, ['title', 'message'])

        if not success:
            # if the function returns False, then bot is set to a Response instance
            return bot

        # hitting this endpoint creates the error
        BotError.objects.create(
            bot=bot,
            title=request.POST.get('title'),
            message=request.POST.get('message')
        )

        return JsonResponse({'success': True})

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)