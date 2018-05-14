from django.contrib import admin

# Register your models here.
from oversight.models import Bot, BotHeartBeat, BotError


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ['name', 'exchange', 'api_secret']


@admin.register(BotHeartBeat)
class BotHeartBeatAdmin(admin.ModelAdmin):
    list_display = ['bot', 'time']


@admin.register(BotError)
class BotErrorAdmin(admin.ModelAdmin):
    list_display = ['bot', 'time', 'title']
