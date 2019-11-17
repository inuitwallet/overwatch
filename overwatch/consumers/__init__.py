from .cloud_watch import CloudWatchLogsConsumer
from .bot import BotConsumer
from .bot_deploy import BotDeployConsumer
from .bot_list import BotListConsumer
from .bot_price import BotPriceConsumer
from .bot_balance import BotBalanceConsumer
from .bot_order import BotOrderConsumer
from .bot_trade import BotTradeConsumer

__all__ = [
    'CloudWatchLogsConsumer',
    'BotConsumer',
    'BotDeployConsumer',
    'BotListConsumer',
    'BotPriceConsumer',
    'BotBalanceConsumer',
    'BotOrderConsumer',
    'BotTradeConsumer'
]
