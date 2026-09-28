from decimal import Decimal

import pytest
from django import forms

from currency_field.forms import CurrencyFormField
from currency_field.widgets import CurrencyWidget, group_decimal_string

# Model-level behaviour (the sibling currency field getting added,
# ModelForm wiring, DB round-tripping) is exercised against a real app in
# the separate testbed project at ../django-currency-field-testbed, not
# here - this package's own tests only cover the pure form/widget logic.


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1234", Decimal("1234")),
        ("1,234", Decimal("1234")),
        ("1,234,567.89", Decimal("1234567.89")),
        ("-1,234.50", Decimal("-1234.50")),
        (" 1,000 ", Decimal("1000")),
    ],
)
def test_form_field_strips_grouping_separators(raw, expected):
    formfield = CurrencyFormField()
    assert formfield.clean(raw) == expected


def test_form_field_still_rejects_garbage():
    formfield = CurrencyFormField()
    with pytest.raises(forms.ValidationError):
        formfield.clean("not-a-number")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("1234", "1,234"),
        ("1234567.89", "1,234,567.89"),
        ("-1234.5", "-1,234.5"),
        ("0", "0"),
        ("12", "12"),
    ],
)
def test_group_decimal_string(raw, expected):
    assert group_decimal_string(raw) == expected


def test_widget_format_value_groups_thousands():
    widget = CurrencyWidget()
    assert widget.format_value("1000000") == "1,000,000"
    assert widget.format_value(None) is None


def test_stray_digit_is_visually_obvious_after_grouping():
    # This is the bug this package exists to fix: without grouping,
    # "10000000" reads just like "1000000" plus a digit you might not
    # notice. Grouped, "1,000,000" -> "10,000,000" is unmistakable.
    assert group_decimal_string("1000000") == "1,000,000"
    assert group_decimal_string("10000000") == "10,000,000"
