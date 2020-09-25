from django.db import models


class DeploymentSettings(models.Model):
    bot = models.OneToOneField("Bot", on_delete=models.CASCADE)
    aws_access_key = models.CharField(
        max_length=255,
        help_text="AWS Access key with ability to create lambda function and obtain logs",
        blank=True,
        null=True,
    )
    aws_secret_key = models.CharField(
        max_length=255, help_text="corresponding AWS secret key", blank=True, null=True
    )
    aws_region = models.CharField(
        max_length=255,
        help_text="AWS Region to deploy Lambda function to",
        default="eu-west-1",
    )
    lambda_name = models.CharField(
        max_length=255, help_text="AWS Lambda Function Name", blank=True, null=True
    )
    exchange_api_key = models.CharField(
        max_length=255,
        help_text="API Key for communication with exchange",
        blank=True,
        null=True,
    )
    exchange_api_secret = models.CharField(
        max_length=255,
        help_text="Corresponding Exchange API Secret",
        blank=True,
        null=True,
    )
    vigil_funds_alert_channel_id = models.UUIDField()
    vigil_wrapper_error_channel_id = models.UUIDField()
