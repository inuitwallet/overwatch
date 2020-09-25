from django import forms
from django.forms import PasswordInput

from overwatch.models import Exchange, AWS


class AWSForm(forms.ModelForm):
    class Meta:
        model = AWS
        fields = ["identifier", "region", "access_key", "secret_key"]
        widgets = {"access_key": PasswordInput(), "secret_key": PasswordInput()}


class ExchangeForm(forms.ModelForm):
    class Meta:
        model = Exchange
        fields = ["identifier", "exchange", "key", "secret"]
        widgets = {
            "key": PasswordInput(),
            "secret": PasswordInput(),
        }
