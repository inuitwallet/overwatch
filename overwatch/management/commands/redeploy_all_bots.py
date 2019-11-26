from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management import BaseCommand

from overwatch.models import Bot


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--exchange',
            help='Exchange to restrict bots to',
            dest='exchange',
            default=None
        )

    def handle(self, *args, **options):
        if options['exchange']:
            bots = Bot.objects.filter(exchange__iexact=options['exchange'])
        else:
            bots = Bot.objects.all()

        for bot in bots:
            async_to_sync(get_channel_layer().send)(
                'bot-deploy',
                {
                    "type": "deploy",
                    "bot_pk": bot.pk
                },
            )

