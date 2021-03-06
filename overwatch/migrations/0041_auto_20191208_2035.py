# Generated by Django 2.1.5 on 2019-12-08 20:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import encrypted_model_fields.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("overwatch", "0040_bot_market"),
    ]

    operations = [
        migrations.CreateModel(
            name="AWS",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("identifier", models.CharField(max_length=255, unique=True)),
                ("region", models.CharField(default="eu-west-1", max_length=255)),
                (
                    "access_key",
                    encrypted_model_fields.fields.EncryptedCharField(
                        blank=True, help_text="database encrypted", null=True
                    ),
                ),
                (
                    "secret_key",
                    encrypted_model_fields.fields.EncryptedCharField(
                        blank=True,
                        help_text="database encrypted and hidden from display",
                        null=True,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Exchange",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("identifier", models.CharField(max_length=255, unique=True)),
                (
                    "exchange",
                    models.CharField(
                        choices=[
                            ("_1btcxe", "_1Btcxe"),
                            ("acx", "Acx"),
                            ("adara", "Adara"),
                            ("allcoin", "Allcoin"),
                            ("anxpro", "Anxpro"),
                            ("bcex", "Bcex"),
                            ("bequant", "Bequant"),
                            ("bibox", "Bibox"),
                            ("bigone", "Bigone"),
                            ("binance", "Binance"),
                            ("binanceje", "Binanceje"),
                            ("binanceus", "Binanceus"),
                            ("bit2c", "Bit2C"),
                            ("bitbank", "Bitbank"),
                            ("bitbay", "Bitbay"),
                            ("bitfinex", "Bitfinex"),
                            ("bitfinex2", "Bitfinex2"),
                            ("bitflyer", "Bitflyer"),
                            ("bitforex", "Bitforex"),
                            ("bithumb", "Bithumb"),
                            ("bitkk", "Bitkk"),
                            ("bitlish", "Bitlish"),
                            ("bitmart", "Bitmart"),
                            ("bitmax", "Bitmax"),
                            ("bitmex", "Bitmex"),
                            ("bitso", "Bitso"),
                            ("bitstamp", "Bitstamp"),
                            ("bitstamp1", "Bitstamp1"),
                            ("bittrex", "Bittrex"),
                            ("bitz", "Bitz"),
                            ("bl3p", "Bl3P"),
                            ("bleutrade", "Bleutrade"),
                            ("braziliex", "Braziliex"),
                            ("btcalpha", "Btcalpha"),
                            ("btcbox", "Btcbox"),
                            ("btcchina", "Btcchina"),
                            ("btcmarkets", "Btcmarkets"),
                            ("btctradeim", "Btctradeim"),
                            ("btctradeua", "Btctradeua"),
                            ("btcturk", "Btcturk"),
                            ("buda", "Buda"),
                            ("bw", "Bw"),
                            ("bytetrade", "Bytetrade"),
                            ("cex", "Cex"),
                            ("chilebit", "Chilebit"),
                            ("cobinhood", "Cobinhood"),
                            ("coinbase", "Coinbase"),
                            ("coinbaseprime", "Coinbaseprime"),
                            ("coinbasepro", "Coinbasepro"),
                            ("coincheck", "Coincheck"),
                            ("coinegg", "Coinegg"),
                            ("coinex", "Coinex"),
                            ("coinexchange", "Coinexchange"),
                            ("coinfalcon", "Coinfalcon"),
                            ("coinfloor", "Coinfloor"),
                            ("coingi", "Coingi"),
                            ("coinmarketcap", "Coinmarketcap"),
                            ("coinmate", "Coinmate"),
                            ("coinone", "Coinone"),
                            ("coinspot", "Coinspot"),
                            ("cointiger", "Cointiger"),
                            ("coolcoin", "Coolcoin"),
                            ("coss", "Coss"),
                            ("crex24", "Crex24"),
                            ("deribit", "Deribit"),
                            ("digifinex", "Digifinex"),
                            ("dsx", "Dsx"),
                            ("exmo", "Exmo"),
                            ("exx", "Exx"),
                            ("fcoin", "Fcoin"),
                            ("fcoinjp", "Fcoinjp"),
                            ("flowbtc", "Flowbtc"),
                            ("foxbit", "Foxbit"),
                            ("ftx", "Ftx"),
                            ("fybse", "Fybse"),
                            ("gateio", "Gateio"),
                            ("gemini", "Gemini"),
                            ("hitbtc", "Hitbtc"),
                            ("hitbtc2", "Hitbtc2"),
                            ("huobipro", "Huobipro"),
                            ("huobiru", "Huobiru"),
                            ("ice3x", "Ice3X"),
                            ("idex", "Idex"),
                            ("independentreserve", "Independentreserve"),
                            ("indodax", "Indodax"),
                            ("itbit", "Itbit"),
                            ("kkex", "Kkex"),
                            ("kraken", "Kraken"),
                            ("kucoin", "Kucoin"),
                            ("kuna", "Kuna"),
                            ("lakebtc", "Lakebtc"),
                            ("latoken", "Latoken"),
                            ("lbank", "Lbank"),
                            ("liquid", "Liquid"),
                            ("livecoin", "Livecoin"),
                            ("luno", "Luno"),
                            ("lykke", "Lykke"),
                            ("mandala", "Mandala"),
                            ("mercado", "Mercado"),
                            ("mixcoins", "Mixcoins"),
                            ("negociecoins", "Negociecoins"),
                            ("oceanex", "Oceanex"),
                            ("okcoincny", "Okcoincny"),
                            ("okcoinusd", "Okcoinusd"),
                            ("okex", "Okex"),
                            ("okex3", "Okex3"),
                            ("paymium", "Paymium"),
                            ("poloniex", "Poloniex"),
                            ("rightbtc", "Rightbtc"),
                            ("southxchange", "Southxchange"),
                            ("stronghold", "Stronghold"),
                            ("surbitcoin", "Surbitcoin"),
                            ("theocean", "Theocean"),
                            ("therock", "Therock"),
                            ("tidebit", "Tidebit"),
                            ("tidex", "Tidex"),
                            ("upbit", "Upbit"),
                            ("vaultoro", "Vaultoro"),
                            ("vbtc", "Vbtc"),
                            ("virwox", "Virwox"),
                            ("whitebit", "Whitebit"),
                            ("xbtce", "Xbtce"),
                            ("yobit", "Yobit"),
                            ("zaif", "Zaif"),
                            ("zb", "Zb"),
                        ],
                        help_text="The exchange name. This matches ",
                        max_length=255,
                    ),
                ),
                (
                    "key",
                    encrypted_model_fields.fields.EncryptedCharField(
                        blank=True,
                        help_text="database encrypted and hidden from display",
                        null=True,
                    ),
                ),
                (
                    "secret",
                    encrypted_model_fields.fields.EncryptedCharField(
                        blank=True,
                        help_text="database encrypted and hidden from display",
                        null=True,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RemoveField(model_name="bot", name="aws_access_key",),
        migrations.RemoveField(model_name="bot", name="aws_region",),
        migrations.RemoveField(model_name="bot", name="aws_secret_key",),
        migrations.RemoveField(model_name="bot", name="base_url",),
        migrations.RemoveField(model_name="bot", name="exchange_api_key",),
        migrations.RemoveField(model_name="bot", name="exchange_api_secret",),
        migrations.AlterField(
            model_name="bot",
            name="exchange",
            field=models.CharField(
                choices=[
                    ("_1btcxe", "_1Btcxe"),
                    ("acx", "Acx"),
                    ("adara", "Adara"),
                    ("allcoin", "Allcoin"),
                    ("anxpro", "Anxpro"),
                    ("bcex", "Bcex"),
                    ("bequant", "Bequant"),
                    ("bibox", "Bibox"),
                    ("bigone", "Bigone"),
                    ("binance", "Binance"),
                    ("binanceje", "Binanceje"),
                    ("binanceus", "Binanceus"),
                    ("bit2c", "Bit2C"),
                    ("bitbank", "Bitbank"),
                    ("bitbay", "Bitbay"),
                    ("bitfinex", "Bitfinex"),
                    ("bitfinex2", "Bitfinex2"),
                    ("bitflyer", "Bitflyer"),
                    ("bitforex", "Bitforex"),
                    ("bithumb", "Bithumb"),
                    ("bitkk", "Bitkk"),
                    ("bitlish", "Bitlish"),
                    ("bitmart", "Bitmart"),
                    ("bitmax", "Bitmax"),
                    ("bitmex", "Bitmex"),
                    ("bitso", "Bitso"),
                    ("bitstamp", "Bitstamp"),
                    ("bitstamp1", "Bitstamp1"),
                    ("bittrex", "Bittrex"),
                    ("bitz", "Bitz"),
                    ("bl3p", "Bl3P"),
                    ("bleutrade", "Bleutrade"),
                    ("braziliex", "Braziliex"),
                    ("btcalpha", "Btcalpha"),
                    ("btcbox", "Btcbox"),
                    ("btcchina", "Btcchina"),
                    ("btcmarkets", "Btcmarkets"),
                    ("btctradeim", "Btctradeim"),
                    ("btctradeua", "Btctradeua"),
                    ("btcturk", "Btcturk"),
                    ("buda", "Buda"),
                    ("bw", "Bw"),
                    ("bytetrade", "Bytetrade"),
                    ("cex", "Cex"),
                    ("chilebit", "Chilebit"),
                    ("cobinhood", "Cobinhood"),
                    ("coinbase", "Coinbase"),
                    ("coinbaseprime", "Coinbaseprime"),
                    ("coinbasepro", "Coinbasepro"),
                    ("coincheck", "Coincheck"),
                    ("coinegg", "Coinegg"),
                    ("coinex", "Coinex"),
                    ("coinexchange", "Coinexchange"),
                    ("coinfalcon", "Coinfalcon"),
                    ("coinfloor", "Coinfloor"),
                    ("coingi", "Coingi"),
                    ("coinmarketcap", "Coinmarketcap"),
                    ("coinmate", "Coinmate"),
                    ("coinone", "Coinone"),
                    ("coinspot", "Coinspot"),
                    ("cointiger", "Cointiger"),
                    ("coolcoin", "Coolcoin"),
                    ("coss", "Coss"),
                    ("crex24", "Crex24"),
                    ("deribit", "Deribit"),
                    ("digifinex", "Digifinex"),
                    ("dsx", "Dsx"),
                    ("exmo", "Exmo"),
                    ("exx", "Exx"),
                    ("fcoin", "Fcoin"),
                    ("fcoinjp", "Fcoinjp"),
                    ("flowbtc", "Flowbtc"),
                    ("foxbit", "Foxbit"),
                    ("ftx", "Ftx"),
                    ("fybse", "Fybse"),
                    ("gateio", "Gateio"),
                    ("gemini", "Gemini"),
                    ("hitbtc", "Hitbtc"),
                    ("hitbtc2", "Hitbtc2"),
                    ("huobipro", "Huobipro"),
                    ("huobiru", "Huobiru"),
                    ("ice3x", "Ice3X"),
                    ("idex", "Idex"),
                    ("independentreserve", "Independentreserve"),
                    ("indodax", "Indodax"),
                    ("itbit", "Itbit"),
                    ("kkex", "Kkex"),
                    ("kraken", "Kraken"),
                    ("kucoin", "Kucoin"),
                    ("kuna", "Kuna"),
                    ("lakebtc", "Lakebtc"),
                    ("latoken", "Latoken"),
                    ("lbank", "Lbank"),
                    ("liquid", "Liquid"),
                    ("livecoin", "Livecoin"),
                    ("luno", "Luno"),
                    ("lykke", "Lykke"),
                    ("mandala", "Mandala"),
                    ("mercado", "Mercado"),
                    ("mixcoins", "Mixcoins"),
                    ("negociecoins", "Negociecoins"),
                    ("oceanex", "Oceanex"),
                    ("okcoincny", "Okcoincny"),
                    ("okcoinusd", "Okcoinusd"),
                    ("okex", "Okex"),
                    ("okex3", "Okex3"),
                    ("paymium", "Paymium"),
                    ("poloniex", "Poloniex"),
                    ("rightbtc", "Rightbtc"),
                    ("southxchange", "Southxchange"),
                    ("stronghold", "Stronghold"),
                    ("surbitcoin", "Surbitcoin"),
                    ("theocean", "Theocean"),
                    ("therock", "Therock"),
                    ("tidebit", "Tidebit"),
                    ("tidex", "Tidex"),
                    ("upbit", "Upbit"),
                    ("vaultoro", "Vaultoro"),
                    ("vbtc", "Vbtc"),
                    ("virwox", "Virwox"),
                    ("whitebit", "Whitebit"),
                    ("xbtce", "Xbtce"),
                    ("yobit", "Yobit"),
                    ("zaif", "Zaif"),
                    ("zb", "Zb"),
                ],
                help_text="The exchange name. This matches ",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="bot",
            name="aws_account",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="overwatch.AWS",
            ),
        ),
        migrations.AddField(
            model_name="bot",
            name="exchange_account",
            field=models.ForeignKey(
                help_text="The exchange account to use",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="overwatch.Exchange",
            ),
        ),
    ]
