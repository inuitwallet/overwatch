from django.conf import settings
from django.core.management import BaseCommand

from overwatch.models import Bot


class Command(BaseCommand):
    def handle(self, *args, **options):
        for bot in Bot.objects.all():
            bot.aws_access_key = settings.AWS_ACCESS_KEY_ID
            bot.aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
            bot.save()
