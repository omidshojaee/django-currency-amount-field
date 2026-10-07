"""CurrencyField on real models: the currency sibling, forms, checks, deconstruct."""

from decimal import Decimal

import pytest
from django import forms
from django.db import models
from django.test.utils import isolate_apps

from currency_amount_field import codes
from currency_amount_field.fields import CurrencyCodeField, CurrencyField
from currency_amount_field.forms import CurrencyFormField
from currency_amount_field.widgets import CurrencyWidget
from tests.testapp import models as m

pytestmark = pytest.mark.django_db


def names(model):
    return [f.name for f in model._meta.fields]


def form_for(model):
    meta = type("Meta", (), {"model": model, "fields": "__all__"})
    return type(f"{model.__name__}Form", (forms.ModelForm,), {"Meta": meta})


# --- the sibling currency field ----------------------------------------------


def test_the_currency_field_is_added_right_after_the_amount():
    assert names(m.Invoice) == ["id", "label", "total", "total_currency", "notes"]
    assert list(form_for(m.Invoice)().fields) == ["label", "total", "total_currency", "notes"]


def test_default_currency_is_the_siblings_default():
    assert m.Invoice().total_currency == "USD"
    assert m.Invoice._meta.get_field("total_currency").default == "USD"


def test_without_a_default_currency_nothing_is_forced_on_the_column():
    sibling = m.NoDefault._meta.get_field("price_currency")
    assert not sibling.has_default()
    assert m.NoDefault().price_currency == ""


def test_saving_without_a_default_currency_does_not_violate_not_null():
    # used to raise: NOT NULL constraint failed ... price_currency
    saved = m.NoDefault.objects.create(price=Decimal("5"))
    saved.refresh_from_db()
    assert saved.price_currency == ""


def test_a_form_demands_a_currency_when_there_is_no_default():
    form = form_for(m.NoDefault)(data={"price": "5"})
    assert not form.is_valid()
    assert "price_currency" in form.errors
    ok = form_for(m.NoDefault)(data={"price": "5", "price_currency": "EUR"})
    assert ok.is_valid() and ok.save().price_currency == "EUR"


def test_the_currency_cannot_be_wiped_even_when_there_is_a_default():
    # used to be accepted and saved as '' (the sibling was blank=True)
    form = form_for(m.Invoice)(data={"label": "x", "total": "5", "total_currency": ""})
    assert not form.is_valid()
    assert "total_currency" in form.errors
    assert m.Invoice._meta.get_field("total_currency").blank is False


def test_a_form_keeps_the_default_as_the_initial_choice():
    assert form_for(m.Invoice)().fields["total_currency"].initial == "USD"


def test_the_currency_label_names_its_amount():
    assert str(m.Invoice._meta.get_field("total_currency").verbose_name) == "total currency"
    assert str(m.Two._meta.get_field("price_currency").verbose_name) == "price currency"
    assert str(m.Two._meta.get_field("cost_currency").verbose_name) == "cost currency"


def test_two_amounts_get_two_currencies_and_a_shared_one_can_be_named():
    assert names(m.Two) == ["id", "price", "price_currency", "cost", "cost_currency"]
    assert names(m.Shared) == ["id", "price", "price_currency", "cost"]


def test_custom_options_reach_the_currency_field():
    unit = m.Custom._meta.get_field("unit")
    assert unit.max_length == 4 and unit.default == "EUR"
    assert [code for code, _ in unit.choices] == ["EUR", "GBP"]


# --- a currency field the developer declares ---------------------------------


@pytest.mark.parametrize("model", [m.ManualAfter, m.ManualBefore])
def test_a_declared_currency_field_wins_wherever_it_is_declared(model):
    field = model._meta.get_field("price_currency")
    assert field.default == "EUR"
    assert [code for code, _ in field.choices] == ["EUR"]
    assert [f.name for f in model._meta.local_fields].count("price_currency") == 1
    assert field._auto_created is False


def test_the_package_currency_field_is_marked_as_automatic():
    assert m.Invoice._meta.get_field("total_currency")._auto_created is True


# --- inheritance ---------------------------------------------------------------


def test_an_abstract_base_passes_both_fields_down_once():
    assert names(m.Child) == ["id", "amount", "amount_currency", "name"]
    assert m.Child._meta.get_field("amount_currency").default == "USD"


def test_a_child_can_replace_the_currency_field_of_an_abstract_base():
    field = m.OverridingChild._meta.get_field("amount_currency")
    assert field.default == "GBP" and [code for code, _ in field.choices] == ["GBP"]
    assert names(m.OverridingChild).count("amount_currency") == 1


# --- forms and storage ----------------------------------------------------------


def test_the_model_formfield_is_the_currency_form_field():
    formfield = m.Invoice._meta.get_field("total").formfield()
    assert isinstance(formfield, CurrencyFormField)
    assert isinstance(formfield.widget, CurrencyWidget)
    assert formfield.widget.attrs["data-decimal-places"] == "2"


def test_a_form_saves_the_ungrouped_amount():
    form = form_for(m.Invoice)(data={"label": "a", "total": "1,234,567.89", "total_currency": "EUR"})
    assert form.is_valid(), form.errors
    invoice = form.save()
    invoice.refresh_from_db()
    assert invoice.total == Decimal("1234567.89") and invoice.total_currency == "EUR"


def test_a_form_refuses_a_decimal_comma_instead_of_saving_a_hundredfold_amount():
    form = form_for(m.Invoice)(data={"label": "a", "total": "12,50", "total_currency": "USD"})
    assert not form.is_valid()
    assert form.errors["total"].as_data()[0].code == "invalid_grouping"


def test_amounts_with_four_decimals_round_trip():
    saved = m.Precise.objects.create(rate=Decimal("1.2345"))
    saved.refresh_from_db()
    assert saved.rate == Decimal("1.2345")
    assert form_for(m.Precise)().fields["rate"].widget.attrs["data-decimal-places"] == "4"


# --- system checks ---------------------------------------------------------------


@isolate_apps("tests.testapp")
def test_a_default_currency_that_is_not_a_choice_is_reported():
    class Bad(models.Model):
        price = CurrencyField(default_currency="usd")

        class Meta:
            app_label = "testapp"

    assert [e.id for e in Bad.check()] == ["currency_amount_field.E001"]


@isolate_apps("tests.testapp")
def test_a_default_currency_from_custom_choices_is_fine():
    class Good(models.Model):
        price = CurrencyField(default_currency="XYZ", currency_choices=[("XYZ", "Zed")])

        class Meta:
            app_label = "testapp"

    assert Good.check() == []


@isolate_apps("tests.testapp")
def test_grouped_custom_choices_are_understood():
    class Grouped(models.Model):
        price = CurrencyField(
            default_currency="EUR",
            currency_choices=[("Europe", [("EUR", "Euro")]), ("Other", [("USD", "Dollar")])],
        )

        class Meta:
            app_label = "testapp"

    assert Grouped.check() == []


def test_the_test_models_pass_the_system_checks():
    from django.core import checks

    assert [e for e in checks.run_checks() if e.id.startswith(("currency_amount_field", "fields."))] == []


# --- deconstruct: what ends up in a migration ---------------------------------------


def test_a_default_amount_field_leaves_everything_default_out_of_the_migration():
    _, _, args, kwargs = m.Invoice._meta.get_field("total").deconstruct()
    assert args == []
    assert kwargs == {"max_digits": 14, "decimal_places": 2, "default_currency": "USD"}


def test_the_default_currency_list_is_not_written_to_migrations():
    _, _, _, amount = m.Invoice._meta.get_field("total").deconstruct()
    _, _, _, sibling = m.Invoice._meta.get_field("total_currency").deconstruct()
    assert "currency_choices" not in amount
    assert "choices" not in sibling and "max_length" not in sibling
    assert sibling["default"] == "USD"


def test_custom_options_are_written_to_migrations():
    _, _, _, amount = m.Custom._meta.get_field("price").deconstruct()
    _, _, _, sibling = m.Custom._meta.get_field("unit").deconstruct()
    assert amount["currency_field_name"] == "unit"
    assert amount["currency_max_length"] == 4
    assert amount["currency_choices"] == [("EUR", "Euro"), ("GBP", "Pound")]
    assert sibling["choices"] == [("EUR", "Euro"), ("GBP", "Pound")] and sibling["max_length"] == 4


def test_fields_built_from_old_migrations_deconstruct_like_new_ones():
    """Migrations written by earlier versions spelled every option out."""
    old = CurrencyField(
        currency_choices=list(codes.CURRENCY_CHOICES),
        currency_field_name="total_currency",
        currency_max_length=3,
        decimal_places=2,
        default_currency="USD",
        max_digits=14,
    )
    old.set_attributes_from_name("total")
    new = m.Invoice._meta.get_field("total")
    assert old.deconstruct()[3] == new.deconstruct()[3]

    old_sibling = CurrencyCodeField(
        blank=True,
        choices=list(codes.CURRENCY_CHOICES),
        default="USD",
        max_length=3,
        verbose_name="currency",
    )
    assert "choices" not in old_sibling.deconstruct()[3]


def test_clone_keeps_every_option():
    for model, name in [(m.Invoice, "total"), (m.Custom, "price"), (m.Precise, "rate")]:
        field = model._meta.get_field(name)
        assert field.clone().deconstruct()[1:] == field.deconstruct()[1:]


def test_the_package_version_is_consistent():
    import re
    from pathlib import Path

    import currency_amount_field

    text = (Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)
    assert currency_amount_field.__version__ == declared
