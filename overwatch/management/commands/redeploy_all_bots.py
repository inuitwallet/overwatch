from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management import BaseCommand

from overwatch.models import Bot


class Command(BaseCommand):
    def handle(self, *args, **options):
        for bot in Bot.objects.all():
            async_to_sync(get_channel_layer().send)(
                'bot-deploy',
                {
                    "type": "deploy",
                    "bot_pk": bot.pk
                },
            )

