# Generated by Django 2.1.5 on 2019-11-10 19:39

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('overwatch', '0032_auto_20190528_2218'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bot',
            name='active',
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AlterField(
            model_name='bot',
            name='market_price',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='botbalance',
            name='time',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='botbalance',
            name='updated',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='botplacedorder',
            name='price_usd',
            field=models.FloatField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='botplacedorder',
            name='time',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='botplacedorder',
            name='updated',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='botprice',
            name='time',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='botprice',
            name='updated',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name='bottrade',
            name='bot_trade',
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AlterField(
            model_name='bottrade',
            name='profit_usd',
            field=models.FloatField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='bottrade',
            name='time',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='bottrade',
            name='trade_type',
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='bottrade',
            name='updated',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]