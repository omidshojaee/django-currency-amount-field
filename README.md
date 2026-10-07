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
- It adds a sibling currency-code `CharField` to the model, right after the
  amount (default name `<field>_currency`), so an amount always carries its
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
`total_currency` (a `CharField` of ISO codes, defaulting to `"USD"`, labelled
"total currency" and required: it can't be cleared in a form).

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
  `manage.py check` reports a code that is not one of the choices
  (`currency_amount_field.E001`). Without it the currency starts empty and a
  form makes you pick one.
- `currency_choices` — override the list of `(code, label)` choices
  (defaults to `currency_amount_field.codes.CURRENCY_CHOICES`, a common subset of
  ISO 4217). Grouped choices work too.
- `currency_max_length` — length of the currency-code column (default `3`).

All other `DecimalField` arguments (`max_digits`, `decimal_places`,
`validators`, etc.) work as usual.

If you declare the currency field yourself (a `CurrencyCodeField` named like
the sibling), yours is used, whether you write it before or after the amount.

## What you can type

The dot is the decimal point; a comma (or a space) may only separate groups of
three digits:

| You type | You get |
|---|---|
| `1234`, `1,234`, `1 234`, `1,234,567.89` | `1234`, `1234`, `1234`, `1234567.89` |
| `۱۲۳۴`, `١٢٣٤`, `۱٬۲۳۴٫۵` (Persian / Arabic digits and separators) | `1234`, `1234`, `1234.5` |
| `12,50`, `1.234,56`, `1,23` | **an error**, not a guess |

`12,50` is refused instead of being read as 1250: silently turning a decimal
comma into a hundredfold amount is exactly the mistake this field exists to
prevent. Scientific notation (`1e3`) and underscores (`1_000`) are refused too.
Fields built with `localize=True` use Django's locale handling instead.

## How the formatting works

- `CurrencyWidget.format_value` groups the stored decimal for display
  (`1234567.89` → `1,234,567.89`).
- `currency-widget.js` re-groups the input live as the user types, keeps as
  many decimals as the field has (`decimal_places` is passed to the script; a
  field with `decimal_places=0` takes no point), keeps the digits in the script
  the user types them in (Persian digits stay Persian), and leaves an
  IME composition alone until it ends. It also works inside Django admin inline
  formsets added dynamically.
- `CurrencyFormField.to_python` removes the thousands separators before
  handing the value to `DecimalField`, so the grouped display never
  affects what gets saved.
- The script finds its inputs by a `data-currency-widget` attribute, so a
  `class` you pass to `CurrencyWidget` (for Bootstrap, say) is added to the
  package's class instead of replacing it.

## Migrations

The amount and its currency are two ordinary fields in a migration, so adding a
`CurrencyField` to a table that already has rows works like adding any two
columns. The default currency list is not written into migrations: a release that
adds a currency never needs a new migration from you. Options you set
(`currency_choices`, `currency_field_name`, ...) are written as usual.

**Upgrading from 1.0.0:** the first `makemigrations` after upgrading produces one
`AlterField` for each currency field (the field is now required and labelled
after its amount). It changes no column.

## Development

```bash
pip install -e ".[test]"
pytest              # Python
node --test tests/js/format.test.mjs   # the widget script
```
