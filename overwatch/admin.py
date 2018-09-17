from django.contrib import admin

# Register your models here.
from overwatch.models import ApiProfile, Bot, BotHeartBeat, BotError
from overwatch.models.bot import BotPlacedOrder, BotPrice


@admin.register(ApiProfile)
class ApiProfileAdmin(admin.ModelAdmin):
    list_display = ['api_user', 'api_secret', 'last_nonce']


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ['name', 'exchange', 'api_secret']


@admin.register(BotHeartBeat)
class BotHeartBeatAdmin(admin.ModelAdmin):
    list_display = ['bot', 'time']


@admin.register(BotError)
class BotErrorAdmin(admin.ModelAdmin):
    list_display = ['bot', 'time', 'title']
    raw_id_fields = ['bot']


@admin.register(BotPlacedOrder)
class BotPlacedOrderAdmin(admin.ModelAdmin):
    list_display = ['bot', 'time', 'base', 'quote', 'order_type', 'price', 'amount']
    raw_id_fields = ['bot']


@admin.register(BotPrice)
class BotPriceAdmin(admin.ModelAdmin):
    list_display = ['bot', 'time', 'price', 'unit', 'side']
    raw_id_fields = ['bot']
