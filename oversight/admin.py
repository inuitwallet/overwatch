from django.contrib import admin

# Register your models here.
from oversight.models import Bot


@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ['name', 'exchange', 'api_secret']
