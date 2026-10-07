from django.db import models

from currency_amount_field.fields import CurrencyCodeField, CurrencyField


class NoDefault(models.Model):
    price = CurrencyField()


class Invoice(models.Model):
    label = models.CharField(max_length=20, blank=True)
    total = CurrencyField(default_currency="USD")
    notes = models.CharField(max_length=20, blank=True)


class ManualAfter(models.Model):
    """The developer declares the currency field after the amount."""

    price = CurrencyField()
    price_currency = CurrencyCodeField(max_length=3, choices=[("EUR", "Euro")], default="EUR")


class ManualBefore(models.Model):
    price_currency = CurrencyCodeField(max_length=3, choices=[("EUR", "Euro")], default="EUR")
    price = CurrencyField()


class Base(models.Model):
    amount = CurrencyField(default_currency="USD")

    class Meta:
        abstract = True


class Child(Base):
    name = models.CharField(max_length=20, blank=True)


class OverridingChild(Base):
    amount_currency = CurrencyCodeField(max_length=3, choices=[("GBP", "Pound")], default="GBP")


class Two(models.Model):
    price = CurrencyField(default_currency="USD")
    cost = CurrencyField(default_currency="EUR")


class Shared(models.Model):
    price = CurrencyField(default_currency="USD")
    cost = CurrencyField(currency_field_name="price_currency")


class Custom(models.Model):
    price = CurrencyField(
        default_currency="EUR",
        currency_choices=[("EUR", "Euro"), ("GBP", "Pound")],
        currency_field_name="unit",
        currency_max_length=4,
    )


class Precise(models.Model):
    rate = CurrencyField(max_digits=12, decimal_places=4, default_currency="USD")
