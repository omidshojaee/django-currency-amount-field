# Changelog

## Unreleased

### Fixed

- **A decimal comma was read as a thousands separator.** `12,50` became `1250`,
  `12,5` became `125`, `1.234,56` became `1.23456`, with no error. Commas and spaces
  are now accepted only between groups of three digits; anything else is refused with
  a message that explains the format. `1e3` and `1_000` are refused too.
- **Adding a `CurrencyField` to a table that already had rows could not be migrated**
  (`NOT NULL constraint failed ... <name>_currency` on SQLite). A migration state
  no longer grows a hidden currency column; the amount and its currency are two
  ordinary fields in the migration.
- **Without `default_currency`, saving an amount raised `IntegrityError`** because the
  currency column got a default of `None`. It now has no default.
- **The currency could be cleared in a form** even when it had a default, and was saved
  as `""`. It is no longer `blank`.
- **The widget script never attached when you passed your own `class`**, which
  replaced the package's. The classes are merged, and the script also finds its inputs
  by a `data-currency-widget` attribute.
- **Persian and Arabic-Indic digits were deleted while typing** (`۱۲۳۴` left an empty
  box). They are kept, in the script they were typed in, along with the Arabic decimal
  and thousands separators; the server reads them too.
- **The script cut every field to two decimals**, losing data in `decimal_places=3` or
  `4` fields. The field's `decimal_places` is passed to the script.
- A currency field you declare yourself *after* the amount field was silently
  dropped; yours is now used.
- `__version__` disagreed with `pyproject.toml`.

### Changed

- The currency field is placed right after its amount in the model and in forms, not
  after every other field, and is labelled "<amount> currency".
- The default currency list and `max_length=3` are no longer written to migrations, so
  adding a currency to the list in a new release does not change anyone's migrations.
  **After upgrading, `makemigrations` produces one `AlterField` per currency field**
  (it is now required, and relabelled); no column changes.
- `manage.py check` reports a `default_currency` that is not one of the choices
  (`currency_amount_field.E001`).
- The script does not reformat during an IME composition, and exposes
  `window.CurrencyAmountField.formatValue`.

### Packaging

- Tests for the model field, migrations (on a table with rows) and the script
  (`node --test tests/js/format.test.mjs`); CI for Python 3.10 to 3.14 and Django 5.2, 6.0 and 6.1;
  the publish workflow runs the tests and `twine check` first.
- Django 6.0 and 6.1 and Python 3.14 classifiers; `setuptools>=77` for the SPDX
  license expression.
