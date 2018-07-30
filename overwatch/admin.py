from django.contrib import admin

# Register your models here.
from overwatch.models import ApiProfile, Bot, BotHeartBeat, BotError


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
