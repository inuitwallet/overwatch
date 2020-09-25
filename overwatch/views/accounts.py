from django.contrib import messages
from django import forms
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic.base import View

from overwatch.forms import ExchangeForm, AWSForm
from overwatch.models import Exchange, AWS


class AWSAccount(View):
    @staticmethod
    def post(request):
        """
        Create AWS Account
        """
        form = AWSForm(request.POST)

        if not form.is_valid():
            messages.add_message(
                request, messages.ERROR, "Failed to create new AWS account"
            )
            return redirect("{}#accounts".format(reverse("index")))
        else:
            aws_account = form.save(commit=False)
            aws_account.owner = request.user
            aws_account.save()
            messages.add_message(request, messages.SUCCESS, "Created new AWS account")
            return redirect("{}#accounts".format(reverse("index")))

    @staticmethod
    def get(request, pk):
        """
        Delete AWS account
        """
        aws_account = get_object_or_404(AWS, pk=pk)
        aws_account.delete()
        return redirect("{}#accounts".format(reverse("index")))


class ExchangeAccount(View):
    @staticmethod
    def post(request):
        """
        Create Exchange Account
        """
        form = ExchangeForm(request.POST)

        if not form.is_valid():
            messages.add_message(
                request, messages.ERROR, "Failed to create new exchange account"
            )
            return redirect("{}#accounts".format(reverse("index")))
        else:
            exchange_account = form.save(commit=False)
            exchange_account.owner = request.user
            exchange_account.save()
            messages.add_message(
                request, messages.SUCCESS, "Created new exchange account"
            )
            return redirect("{}#accounts".format(reverse("index")))

    @staticmethod
    def get(request, pk):
        """
        Delete Exchange account
        """
        exchange_account = get_object_or_404(Exchange, pk=pk)
        exchange_account.delete()
        return redirect("{}#accounts".format(reverse("index")))
