# Generated by Django 2.1.5 on 2019-01-18 00:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("overwatch", "0027_bot_aws_region"),
    ]

    operations = [
        migrations.AddField(
            model_name="bottrade",
            name="bot_trade",
            field=models.BooleanField(default=True),
        ),
    ]
