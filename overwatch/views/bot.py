from math import ceil

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.template import Template, Context
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, DeleteView, UpdateView

from overwatch.models import Bot, BotError, BotPlacedOrder, BotTrade


class ListBotView(LoginRequiredMixin, ListView):
    model = Bot


class DetailBotView(LoginRequiredMixin, DetailView):
    model = Bot


class UpdateBotView(SuccessMessageMixin, LoginRequiredMixin, UpdateView):
    model = Bot
    fields = ['name', 'exchange', 'base', 'quote', 'track', 'peg',
              'tolerance', 'fee', 'bid_spread', 'ask_spread', 'order_amount', 'total_bid', 'total_ask',
              'logs_group', 'aws_access_key', 'aws_secret_key', 'base_price_url', 'quote_price_url', 'market_price']
    success_message = '%(name)s@%(exchange)s has been updated'

    def get_success_url(self):
        return reverse_lazy('bot_detail', kwargs={'pk': self.object.pk})


class CreateBotView(SuccessMessageMixin, LoginRequiredMixin, CreateView):
    model = Bot
    fields = ['name', 'exchange', 'base', 'quote', 'track', 'peg',
              'tolerance', 'fee', 'bid_spread', 'ask_spread', 'order_amount', 'total_bid', 'total_ask',
              'logs_group', 'aws_access_key', 'aws_secret_key', 'base_price_url', 'quote_price_url', 'market_price']
    success_message = '%(name)s@%(exchange)s has been created'
    success_url = reverse_lazy('index')


class DeleteBotView(SuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Bot
    success_message = '%(name)s has been deleted'
    success_url = reverse_lazy('index')


def generic_data_tables_view(request, object, bot_pk):
    # get the basic parameters
    draw = int(request.GET.get('draw', 0))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 0))

    # handle a search term
    search = request.GET.get('search[value]', '')
    query_set = object.objects.filter(bot__pk=bot_pk)
    results_total = query_set.count()

    if search:
        # start with a blank Q object and add a query for every non-relational field attached to the model
        q_objects = Q()

        for field in object._meta.fields:
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
        ceil(index / length)
    )

    return {
        'draw': draw,
        'recordsTotal': results_total,
        'recordsFiltered': query_set.count(),
        'data': page
    }


class BotErrorsDataTablesView(LoginRequiredMixin, View):
    def get(self, request, pk):
        data = generic_data_tables_view(request, BotError, pk)
        return JsonResponse(
            {
                'draw': data['draw'],
                'recordsTotal': data['recordsTotal'],
                'recordsFiltered': data['recordsFiltered'],
                'data': [
                    [
                        Template(
                            '{{ error.time }}'
                        ).render(
                            Context({'error': error})
                        ),
                        error.title,
                        error.message
                    ] for error in data['data']
                ]
            }
        )


class BotPlacedOrdersDataTablesView(LoginRequiredMixin, View):
    def get(self, request, pk):
        data = generic_data_tables_view(request, BotPlacedOrder, pk)
        return JsonResponse(
            {
                'draw': data['draw'],
                'recordsTotal': data['recordsTotal'],
                'recordsFiltered': data['recordsFiltered'],
                'data': [
                    [
                        Template(
                            '{{ placed_order.time }}'
                        ).render(
                            Context({'placed_order': placed_order})
                        ),
                        placed_order.order_type,
                        round(placed_order.price, 8),
                        round(placed_order.price_usd, 8) if placed_order.price_usd else 'Calculating',
                        placed_order.amount
                    ] for placed_order in data['data']
                ]
            }
        )


class BotTradesDataTablesView(LoginRequiredMixin, View):
    def get(self, request, pk):
        data = generic_data_tables_view(request, BotTrade, pk)
        return JsonResponse(
            {
                'draw': data['draw'],
                'recordsTotal': data['recordsTotal'],
                'recordsFiltered': data['recordsFiltered'],
                'data': [
                    [
                        Template(
                            '{{ trade.time }}'
                        ).render(
                            Context({'trade': trade})
                        ),
                        trade.trade_id,
                        trade.trade_type.title(),
                        round(trade.target_price_usd, 8) if trade.target_price_usd else 'Calculating',
                        round(trade.trade_price_usd, 8) if trade.trade_price_usd else 'Calculating',
                        trade.amount,
                        round(trade.profit_usd, 2) if trade.profit_usd else 'Calculating'
                    ] for trade in data['data']
                ]
            }
        )
