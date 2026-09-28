from django.db import models
from django.utils.translation import gettext_lazy as _

from .codes import CURRENCY_CHOICES
from .forms import CurrencyFormField


class CurrencyCodeField(models.CharField):
    """
    The sibling `CharField` that `CurrencyField` attaches to a model.

    Guards its own `contribute_to_class` against being added twice, which
    Django's migration replay would otherwise trigger: when a migration's
    `CreateModel` operation is rendered into a model class, both this field
    and the `CurrencyField` it belongs to appear as separate entries, and
    whichever is processed first re-triggers `CurrencyField`'s side effect
    of adding this field again.
    """

    def contribute_to_class(self, cls, name, **kwargs):
        if any(f.name == name for f in cls._meta.local_fields):
            return
        super().contribute_to_class(cls, name, **kwargs)


class CurrencyField(models.DecimalField):
    """
    A DecimalField for monetary amounts.

    On top of the usual DecimalField behaviour, it:

    * automatically adds a sibling `CharField` on the model to hold an ISO
      4217 currency code (e.g. "USD"), named `<field_name>_currency` unless
      `currency_field_name` is given;
    * uses a form widget that displays (and keeps updated while typing)
      thousands separators, so a stray extra digit is visually obvious
      instead of silently multiplying the value by 10.

    Example::

        class Invoice(models.Model):
            total = CurrencyField(max_digits=12, decimal_places=2,
                                   default_currency="USD")
    """

    def __init__(
        self,
        *args,
        currency_field_name=None,
        default_currency=None,
        currency_max_length=3,
        currency_choices=CURRENCY_CHOICES,
        **kwargs,
    ):
        kwargs.setdefault("max_digits", 14)
        kwargs.setdefault("decimal_places", 2)
        self.currency_field_name = currency_field_name
        self.default_currency = default_currency
        self.currency_max_length = currency_max_length
        self.currency_choices = currency_choices
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        self.currency_field_name = self.currency_field_name or f"{name}_currency"

        if not any(
            f.name == self.currency_field_name for f in cls._meta.local_fields
        ):
            currency_field = CurrencyCodeField(
                max_length=self.currency_max_length,
                choices=self.currency_choices,
                default=self.default_currency,
                blank=bool(self.default_currency),
                verbose_name=_("currency"),
            )
            cls.add_to_class(self.currency_field_name, currency_field)

        super().contribute_to_class(cls, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {"form_class": CurrencyFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["currency_field_name"] = self.currency_field_name
        kwargs["default_currency"] = self.default_currency
        kwargs["currency_max_length"] = self.currency_max_length
        kwargs["currency_choices"] = self.currency_choices
        return name, path, args, kwargs
