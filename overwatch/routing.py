from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
from django.conf.urls import url

from .consumers import *


application = ProtocolTypeRouter({
    # http->django views is added by default
    'websocket': AuthMiddlewareStack(
        URLRouter([
            url(r'^logs/(?P<pk>[^/]+)/$', CloudWatchConsumer),
            url(r'^bot/(?P<pk>[^/]+)/$', BotConsumer)
        ])
    ),
    'channel': ChannelNameRouter({
        'bot-price': BotPriceConsumer,
        'bot-balance': BotBalanceConsumer,
        'bot-order': BotOrderConsumer,
        'bot-trade': BotTradeConsumer,
    }),
})
