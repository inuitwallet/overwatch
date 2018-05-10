import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, DeleteView, UpdateView

from oversight.models import Bot, BotHeartBeat


class ListBotView(LoginRequiredMixin, ListView):
    model = Bot


class DetailBotView(LoginRequiredMixin, DetailView):
    model = Bot


class UpdateBotView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Bot
    fields = ['name', 'exchange', 'base', 'quote', 'track', 'peg',
              'tolerance', 'fee', 'order_amount', 'total_bid', 'total_ask']
    success_message = '%(name)s has been updated'

    def get_success_url(self):
        return reverse_lazy('bot_detail', kwargs={'pk': self.object.pk})


class CreateBotView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Bot
    fields = ['name', 'exchange', 'base', 'quote', 'track', 'peg',
              'tolerance', 'fee', 'order_amount', 'total_bid', 'total_ask']
    success_message = '%(name)s has been created'
    success_url = reverse_lazy('index')


class DeleteBotView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Bot
    success_message = '%(name)s has been deleted'
    success_url = reverse_lazy('index')


class BotConfigView(View):
    @staticmethod
    def get(request):
        for key in ['name', 'exchange', 'n', 'h']:
            if key not in request.GET:
                return JsonResponse({'success': False, 'error': 'no {} present in GET data'.format(key)})

        name = request.GET.get('name')
        exchange = request.GET.get('exchange')
        nonce = request.GET.get('n')
        supplied_hash = request.GET.get('h')

        try:
            bot = Bot.objects.get(name__iexact=name, exchange__iexact=exchange)
        except Bot.DoesNotExist:
            return HttpResponseNotFound(
                json.dumps(
                    {'success': False, 'error': '\'{}@{}\' does not exist as a bot'.format(name, exchange)}
                ),
                content_type='application/json'
            )

        has_auth, reason = bot.auth(supplied_hash, name, exchange, nonce)
        if not has_auth:
            return HttpResponseForbidden(
                json.dumps({'success': False, 'error': reason}),
                content_type='application/json'
            )

        # hitting this endpoint can act as a 'heartbeat' monitor for the bots
        # create a heartbeat object
        BotHeartBeat.objects.create(bot=bot)

        return JsonResponse(bot.serialize())
