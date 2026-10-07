"""The form field and widget: what is accepted, what is refused, how it renders."""

from decimal import Decimal

import pytest
from django import forms
from django.test import override_settings
from django.utils import translation

from currency_amount_field.forms import CurrencyFormField
from currency_amount_field.widgets import CurrencyWidget, group_decimal_string

# Model-level behaviour is in test_model_fields.py and test_migrations.py.


def clean(raw, **kwargs):
    return CurrencyFormField(**kwargs).clean(raw)


def error_code(raw, **kwargs):
    with pytest.raises(forms.ValidationError) as caught:
        clean(raw, **kwargs)
    return caught.value.error_list[0].code


# --- what is accepted --------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1234", "1234"),
        ("1,234", "1234"),
        ("1,234,567.89", "1234567.89"),
        ("-1,234.50", "-1234.50"),
        (" 1,000 ", "1000"),
        ("+5", "5"),
        (".5", "0.5"),
        ("5.", "5"),
        ("0.5", "0.5"),
        ("1 234 567", "1234567"),  # a space groups just like a comma
        ("1 234", "1234"),  # no-break space
        ("1 234", "1234"),  # narrow no-break space
        ("−5", "-5"),  # the Unicode minus sign
    ],
)
def test_form_field_reads_grouped_amounts(raw, expected):
    assert clean(raw) == Decimal(expected)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("۱۲۳۴", "1234"),  # Persian digits
        ("١٢٣٤", "1234"),  # Arabic-Indic digits
        ("۱,۲۳۴", "1234"),
        ("۱٬۲۳۴٫۵", "1234.5"),  # Arabic thousands and decimal separators
        ("۱٬۲۳۴٬۵۶۷", "1234567"),
        ("12٫5", "12.5"),
    ],
)
def test_form_field_reads_persian_and_arabic_digits_and_separators(raw, expected):
    assert clean(raw) == Decimal(expected)


# --- what is refused instead of guessed -------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "12,50",  # a decimal comma: was read as 1250
        "12,5",  # was 125
        "0,5",  # was 5
        ",5",
        "1,23",
        "1,2,3",
        "1,,000",
        "1 23",
        "1.234,56",  # European grouping: was 1.23456
        "1,234,56",
        "1,234 567",  # two kinds of separator
        "1 234,567",
        "1,234.5,6",
        "۱۲,۵۰",  # the same mistake in Persian digits
    ],
)
def test_ambiguous_commas_are_refused_not_guessed(raw):
    assert error_code(raw) == "invalid_grouping"


def test_the_grouping_message_explains_the_format():
    with pytest.raises(forms.ValidationError) as caught:
        clean("12,50")
    assert "dot" in caught.value.messages[0] and "1,234.56" in caught.value.messages[0]


@pytest.mark.parametrize(
    "raw", ["not-a-number", "abc", "1e3", "1_000", "NaN", "Infinity", "-", "+", ".", "--5", "1.2.3", "1,000,abc"]
)
def test_garbage_is_still_rejected_as_not_a_number(raw):
    assert error_code(raw) == "invalid"


def test_empty_values_follow_required():
    assert clean("", required=False) is None
    assert error_code("") == "required"
    assert error_code("   ") == "required"


def test_django_validators_still_apply_to_the_cleaned_value():
    assert error_code("1,234.567", max_digits=6, decimal_places=2) in {"max_decimal_places", "max_digits"}
    assert error_code("5", min_value=Decimal("10")) == "min_value"


def test_localize_true_leaves_parsing_to_djangos_locale_handling():
    with override_settings(USE_THOUSAND_SEPARATOR=True), translation.override("de"):
        assert clean("1.234,56", localize=True) == Decimal("1234.56")


def test_has_changed_compares_cleaned_values():
    field = CurrencyFormField()
    assert not field.has_changed(Decimal("1000.00"), "1,000.00")
    assert not field.has_changed(Decimal("1000"), "۱٬۰۰۰")
    assert field.has_changed(Decimal("1000"), "1,001")


# --- widget ----------------------------------------------------------------


def test_widget_format_value_groups_thousands():
    widget = CurrencyWidget()
    assert widget.format_value("1000000") == "1,000,000"
    assert widget.format_value(Decimal("1234567.80")) == "1,234,567.80"
    assert widget.format_value(None) is None
    assert widget.format_value("") is None  # Django turns "" into None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1234", "1,234"),
        ("1234567.89", "1,234,567.89"),
        ("-1234.5", "-1,234.5"),
        ("0", "0"),
        ("12", "12"),
        (".5", "0.5"),
        ("12,50", "12,50"),  # not a plain number: left alone
        ("1E+7", "1E+7"),
        ("NaN", "NaN"),
        ("+1234", "+1234"),
        ("²", "²"),  # a superscript is not a digit we group
    ],
)
def test_group_decimal_string(raw, expected):
    assert group_decimal_string(raw) == expected


def test_stray_digit_is_visually_obvious_after_grouping():
    # This is the bug this package exists to fix: without grouping,
    # "10000000" reads just like "1000000" plus a digit you might not
    # notice. Grouped, "1,000,000" -> "10,000,000" is unmistakable.
    assert group_decimal_string("1000000") == "1,000,000"
    assert group_decimal_string("10000000") == "10,000,000"


def test_widget_default_attrs():
    assert CurrencyWidget().attrs == {
        "inputmode": "decimal",
        "autocomplete": "off",
        "data-currency-widget": "true",
        "class": "currency-field-input",
    }


def test_a_class_you_pass_is_added_to_the_packages_not_replacing_it():
    assert CurrencyWidget(attrs={"class": "form-control"}).attrs["class"] == "form-control currency-field-input"
    # ... without ever listing the package's class twice
    attrs = CurrencyWidget(attrs={"class": "currency-field-input wide"}).attrs
    assert attrs["class"] == "currency-field-input wide"
    assert CurrencyWidget(attrs={"class": None}).attrs["class"] == "currency-field-input"


def test_the_script_can_find_the_input_whatever_its_class():
    html = CurrencyWidget(attrs={"class": "form-control"}).render("amount", "1234")
    assert "data-currency-widget" in html
    assert 'class="form-control currency-field-input"' in html
    assert 'value="1,234"' in html


def test_other_attrs_still_override_the_defaults():
    attrs = CurrencyWidget(attrs={"inputmode": "numeric", "placeholder": "0.00"}).attrs
    assert attrs["inputmode"] == "numeric" and attrs["placeholder"] == "0.00"


def test_the_script_is_told_how_many_decimals_the_field_has():
    field = CurrencyFormField(max_digits=12, decimal_places=4)
    assert field.widget.attrs["data-decimal-places"] == "4"
    assert CurrencyFormField(max_digits=12, decimal_places=0).widget.attrs["data-decimal-places"] == "0"
    assert "data-decimal-places" not in CurrencyFormField().widget.attrs


def test_widget_declares_its_static_files():
    media = str(CurrencyWidget().media)
    assert "currency_amount_field/js/currency-widget.js" in media
    assert "currency_amount_field/css/currency-widget.css" in media


def test_a_rejected_value_is_shown_back_exactly_as_typed():
    class F(forms.Form):
        amount = CurrencyFormField()

    form = F(data={"amount": "12,50"})
    assert not form.is_valid()
    assert 'value="12,50"' in str(form["amount"])
