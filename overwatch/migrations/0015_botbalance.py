# Generated by Django 2.1 on 2018-09-29 11:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('overwatch', '0014_auto_20180920_1459'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotBalance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField(auto_now_add=True)),
                ('bid_available', models.FloatField()),
                ('ask_available', models.FloatField()),
                ('bid_on_order', models.FloatField()),
                ('ask_on_order', models.FloatField()),
                ('bid_available_usd', models.FloatField(blank=True, null=True)),
                ('ask_available_usd', models.FloatField(blank=True, null=True)),
                ('bid_on_order_usd', models.FloatField(blank=True, null=True)),
                ('ask_on_order_usd', models.FloatField(blank=True, null=True)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='overwatch.Bot')),
            ],
            options={
                'ordering': ['-time'],
            },
        ),
    ]
