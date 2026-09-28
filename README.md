# django-currency-amount-field

Django's `DecimalField` has a UX trap in the admin: amounts are shown as a
plain, ungrouped number, so a stray extra digit is invisible. Typing
`10000000` instead of `1,000,000` looks almost identical to the eye and
turns a million into ten million with no warning.

`CurrencyField` fixes this without asking you to build anything:

- It's a drop-in `DecimalField` subclass, so it works with `ModelForm`,
  the admin, migrations, etc.
- Its form widget groups digits with thousands separators as you type
  (via a small vanilla-JS file, no dependencies), so a typo is visually
  obvious immediately: `1,000,000` vs `10,000,000`.
- It automatically adds a sibling currency-code `CharField` to the model
  (default name `<field>_currency`), so an amount always carries its
  currency.

## Install

```bash
pip install django-currency-amount-field
```

Add `"currency_amount_field"` to `INSTALLED_APPS` (needed for the static
JS/CSS to be collected).

## Usage

```python
from django.db import models
from currency_amount_field.fields import CurrencyField


class Invoice(models.Model):
    total = CurrencyField(max_digits=12, decimal_places=2,
                                 default_currency="USD")
```

This generates two columns: `total` (the `DecimalField`) and
`total_currency` (a `CharField` of ISO codes, defaulting to `"USD"`).

No further admin configuration is required — `ModelForm.formfield()` picks
up the comma-grouping widget automatically:

```python
from django.contrib import admin


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    fields = ["total", "total_currency"]
```

### Options

- `currency_field_name` — override the sibling field's name.
- `default_currency` — default value for the sibling field (e.g. `"USD"`).
- `currency_choices` — override the list of `(code, label)` choices
  (defaults to `currency_amount_field.codes.CURRENCY_CHOICES`, a common subset of
  ISO 4217).
- `currency_max_length` — length of the currency-code column (default `3`).

All other `DecimalField` arguments (`max_digits`, `decimal_places`,
`validators`, etc.) work as usual.

## How the formatting works

- `CurrencyWidget.format_value` groups the stored decimal for display
  (`1234567.89` → `1,234,567.89`).
- `currency-widget.js` re-groups the input live as the user types
  (including inside Django admin inline formsets added dynamically).
- `CurrencyFormField.to_python` strips thousands separators before
  handing the value to `DecimalField`, so the grouped display never
  affects what gets saved.

## Development

```bash
pip install -e ".[test]"
pytest
```
