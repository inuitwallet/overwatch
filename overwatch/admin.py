from django.contrib import admin

# Register your models here.
from overwatch.models import (
    ApiProfile,
    Bot,
    BotHeartBeat,
    BotError,
    BotPlacedOrder,
    BotPrice,
    BotBalance,
    BotTrade,
    Exchange,
    AWS,
)


@admin.register(ApiProfile)
class ApiProfileAdmin(admin.ModelAdmin):
    list_display = ["api_user", "api_secret", "last_nonce"]
    list_filter = ["api_user"]


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ["name", "exchange_account", "api_secret", "logs_group"]
    list_filter = ["name", "exchange_account"]


@admin.register(BotHeartBeat)
class BotHeartBeatAdmin(admin.ModelAdmin):
    list_display = ["bot", "time"]
    list_filter = ["bot"]


@admin.register(BotError)
class BotErrorAdmin(admin.ModelAdmin):
    list_display = ["bot", "time", "title"]
    raw_id_fields = ["bot"]
    list_filter = ["bot"]


@admin.register(BotPlacedOrder)
class BotPlacedOrderAdmin(admin.ModelAdmin):
    list_display = [
        "bot",
        "time",
        "base",
        "quote",
        "order_type",
        "price",
        "price_usd",
        "amount",
    ]
    raw_id_fields = ["bot"]
    list_filter = ["bot", "base", "quote", "order_type"]


@admin.register(BotPrice)
class BotPriceAdmin(admin.ModelAdmin):
    list_display = ["bot", "time", "price", "price_usd", "market_price_usd", "unit"]
    raw_id_fields = ["bot"]
    list_filter = ["bot"]


@admin.register(BotBalance)
class BotBalanceAdmin(admin.ModelAdmin):
    list_display = [
        "bot",
        "time",
        "bid_available",
        "ask_available",
        "bid_on_order",
        "ask_on_order",
    ]
    raw_id_fields = ["bot"]
    list_filter = ["bot"]


@admin.register(BotTrade)
class BotTradeAdmin(admin.ModelAdmin):
    list_display = [
        "bot",
        "time",
        "trade_type",
        "trade_id",
        "price",
        "amount",
        "total",
        "target_price_usd",
        "trade_price_usd",
        "profit_usd",
        "updated",
    ]
    list_editable = ["updated"]
    raw_id_fields = ["bot"]
    list_filter = ["bot", "trade_type"]


@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    pass


@admin.register(AWS)
class AWSAdmin(admin.ModelAdmin):
    pass
