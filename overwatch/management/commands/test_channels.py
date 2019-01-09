from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.management import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print('testing channels')
        layer = get_channel_layer()
        print(layer)
        async_to_sync(layer.send)(
            'bot-price',
            {
                "type": "calculate.usd.values",
                "id": 123456789,
            },
        )
