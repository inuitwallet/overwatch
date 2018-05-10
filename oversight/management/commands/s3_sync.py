import json

import boto3
from botocore.config import Config
from django.core.management import BaseCommand

from oversight.models import Bot


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '-p',
            '--pull',
            help='Sync changes from s3 to Oversight',
            action='store_true',
            default=False
        )

    def handle(self, *args, **options):
        config = Config(connect_timeout=120, read_timeout=120)
        client = boto3.client('s3', config=config)
        for object in client.list_objects_v2(Bucket='nu-lambda-data').get('Contents'):
            if 'liquidity_provision_pairs' in object.get('Key'):
                exchange = object.get('Key').replace('_liquidity_provision_pairs.json', '').title()
                file = client.get_object(Bucket='nu-lambda-data', Key=object.get('Key'))
                contents = json.loads(file.get('Body').read())
                for bot in contents:
                    Bot.objects.update_or_create(
                        name=bot.get('name'),
                        exchange=exchange,
                        defaults={
                            'base': bot.get('base'),
                            'quote': bot.get('quote'),
                            'track': bot.get('track'),
                            'peg': bot.get('peg'),
                            'tolerance': bot.get('tolerance'),
                            'fee': bot.get('fee'),
                            'order_amount': bot.get('order_amount'),
                            'total_bid': bot.get('total_bid'),
                            'total_ask': bot.get('total_ask')
                        }
                    )

