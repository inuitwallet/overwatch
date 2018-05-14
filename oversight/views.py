import json
from math import ceil

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, Http404, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.template import Template, Context
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, CreateView, DeleteView, UpdateView

from oversight.models import Bot, BotHeartBeat, BotError


class ListBotView(LoginRequiredMixin, ListView):
    model = Bot


class DetailBotView(LoginRequiredMixin, DetailView):
    model = Bot

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_heartbeats = self.object.botheartbeat_set.all()
        paginator = Paginator(all_heartbeats, 30)
        context['heart_beats'] = paginator.get_page(1)
        print(context)
        return context


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


class BotErrorsView(View):
    @staticmethod
    def post(request):
        for key in ['name', 'exchange', 'n', 'h', 'title', 'message']:
            if key not in request.POST:
                return JsonResponse({'success': False, 'error': 'no {} present in POST data'.format(key)})

        name = request.POST.get('name')
        exchange = request.POST.get('exchange')
        nonce = request.POST.get('n')
        supplied_hash = request.POST.get('h')
        title = request.POST.get('title')
        message = request.POST.get('message')

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

        # hitting this endpoint creates the error
        BotError.objects.create(
            bot=bot,
            title=title,
            message=message
        )

        return JsonResponse({'success': True})

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class BotErrorsDataTablesView(LoginRequiredMixin, View):
    def get(self, request, pk):
        # get the basic parameters
        draw = int(request.GET.get('draw', 0))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 0))

        # handle a search term
        search = request.GET.get('search[value]', '')
        query_set = BotError.objects.filter(bot__pk=pk)
        results_total = query_set.count()

        if search:
            # start with a blank Q object and add a query for every non-relational field attached to the model
            q_objects = Q()

            for field in BotError._meta.fields:
                if field.is_relation:
                    continue
                kwargs = {'{}__icontains'.format(field.name): search}
                q_objects |= Q(**kwargs)

            query_set = query_set.filter(q_objects)

        # handle the ordering
        order_column_index = request.GET.get('order[0][column]')
        order_by = request.GET.get('columns[{}][name]'.format(order_column_index))
        order_direction = request.GET.get('order[0][dir]')

        if order_direction == 'desc':
            order_by = '-{}'.format(order_by)

        if order_by:
            query_set = query_set.order_by(order_by)

        # now we have our completed queryset. we can paginate it
        index = start + 1  # start is 0 based, pages are 1 based
        page = Paginator(
            query_set,
            length
        ).get_page(
            ceil(index/length)
        )

        return JsonResponse(
            {
                'draw': draw,
                'recordsTotal': results_total,
                'recordsFiltered': query_set.count(),
                'data': [
                    [
                        Template(
                            '{{ error.time }}'
                        ).render(
                            Context({'error': error})
                        ),
                        error.title,
                        error.message
                    ] for error in page
                ]
            }
        )
