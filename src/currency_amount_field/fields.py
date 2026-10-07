from django.core import checks
from django.db import models
from django.utils.choices import flatten_choices
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from .codes import CURRENCY_CHOICES
from .forms import CurrencyFormField

DEFAULT_CURRENCY_MAX_LENGTH = 3

#: Django renders the models of a migration state with this ``__module__``.
_MIGRATION_STATE_MODULE = "__fake__"


def _is_default_choices(choices):
    """True when ``choices`` is (or equals) the package's own currency list."""
    return choices is None or list(choices) == list(CURRENCY_CHOICES)


class CurrencyCodeField(models.CharField):
    """
    The sibling `CharField` that `CurrencyField` adds to a model.

    When ``choices`` is the package's own list it is left out of the migration
    (it is rebuilt from the package when the field is loaded), so adding a
    currency to the list in a new release never needs a new migration. A custom
    ``choices`` list is kept in migrations as usual.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("choices", CURRENCY_CHOICES)
        kwargs.setdefault("max_length", DEFAULT_CURRENCY_MAX_LENGTH)
        super().__init__(*args, **kwargs)
        # True for the field `CurrencyField` creates on its own, False for one a
        # developer declares. Not part of the migration.
        self._auto_created = False

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if _is_default_choices(kwargs.get("choices")):
            kwargs.pop("choices", None)
        if kwargs.get("max_length") == DEFAULT_CURRENCY_MAX_LENGTH:
            kwargs.pop("max_length")
        return name, path, args, kwargs

    def contribute_to_class(self, cls, name, **kwargs):
        existing = next((f for f in cls._meta.local_fields if f.name == name), None)
        if existing is not None:
            if self._auto_created:
                # The copy a child class gets from an abstract base: its own
                # `CurrencyField` already created this field.
                return
            if existing._auto_created:
                # The developer declared the field after the amount field had
                # already created one: the developer's declaration wins.
                cls._meta.local_fields.remove(existing)
            # Otherwise it is a real duplicate and Django will report it.
        super().contribute_to_class(cls, name, **kwargs)


class CurrencyField(models.DecimalField):
    """
    A DecimalField for monetary amounts.

    On top of the usual DecimalField behaviour, it:

    * adds a sibling `CharField` to the model that holds an ISO 4217 currency
      code (e.g. "USD"), named `<field_name>_currency` unless
      `currency_field_name` is given, and placed right after the amount;
    * uses a form widget that displays (and keeps updated while typing)
      thousands separators, so a stray extra digit is visually obvious
      instead of silently multiplying the value by 10.

    Example::

        class Invoice(models.Model):
            total = CurrencyField(max_digits=12, decimal_places=2,
                                   default_currency="USD")

    In migrations the amount and its currency are two ordinary fields, listed
    explicitly, so adding a `CurrencyField` to an existing table works like
    adding any two columns.
    """

    def __init__(
        self,
        *args,
        currency_field_name=None,
        default_currency=None,
        currency_max_length=DEFAULT_CURRENCY_MAX_LENGTH,
        currency_choices=None,
        **kwargs,
    ):
        kwargs.setdefault("max_digits", 14)
        kwargs.setdefault("decimal_places", 2)
        self.currency_field_name = currency_field_name
        self.default_currency = default_currency
        self.currency_max_length = currency_max_length
        # None means "the package's own list", looked up when the model loads.
        self.currency_choices = currency_choices
        super().__init__(*args, **kwargs)

    def _sibling_choices(self):
        return CURRENCY_CHOICES if self.currency_choices is None else self.currency_choices

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        self.currency_field_name = self.currency_field_name or f"{name}_currency"

        if cls.__module__ == _MIGRATION_STATE_MODULE:
            # A migration state lists the currency field itself; adding another
            # here would put a column in the state that no migration created.
            return
        if any(f.name == self.currency_field_name for f in cls._meta.local_fields):
            return

        options = {}
        if self.default_currency:
            options["default"] = self.default_currency
        currency_field = CurrencyCodeField(
            max_length=self.currency_max_length,
            choices=self._sibling_choices(),
            verbose_name=format_lazy("{} {}", self.verbose_name, _("currency")),
            **options,
        )
        currency_field._auto_created = True
        # Sort right after the amount instead of after every other field.
        currency_field.creation_counter = self.creation_counter + 0.5
        cls.add_to_class(self.currency_field_name, currency_field)

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        if self.default_currency:
            codes = {str(code) for code, _label in flatten_choices(self._sibling_choices())}
            if self.default_currency not in codes:
                errors.append(
                    checks.Error(
                        f"default_currency={self.default_currency!r} is not one of the "
                        "currency choices.",
                        hint="Use an ISO 4217 code from currency_choices, in capitals.",
                        obj=self,
                        id="currency_amount_field.E001",
                    )
                )
        return errors

    def formfield(self, **kwargs):
        defaults = {"form_class": CurrencyFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.currency_field_name and self.currency_field_name != f"{name}_currency":
            kwargs["currency_field_name"] = self.currency_field_name
        if self.default_currency:
            kwargs["default_currency"] = self.default_currency
        if self.currency_max_length != DEFAULT_CURRENCY_MAX_LENGTH:
            kwargs["currency_max_length"] = self.currency_max_length
        if not _is_default_choices(self.currency_choices):
            kwargs["currency_choices"] = self.currency_choices
        return name, path, args, kwargs
