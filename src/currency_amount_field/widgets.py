from django import forms


class CurrencyWidget(forms.TextInput):
    """
    A text input that displays decimal amounts grouped with thousands
    separators (e.g. "1,000,000.00"). The `currency-widget.js` static file
    keeps that grouping live as the user types, so an accidental extra digit
    is visually obvious (e.g. typing one more "0" turns "1,000,000" into
    "10,000,000" instead of silently becoming a 10x bigger, ungrouped number).

    Values are still submitted/parsed with the separators in place;
    `CurrencyFormField.to_python` strips them before decimal
    conversion, so this is purely a display/UX layer over a normal
    DecimalField.
    """

    class Media:
        js = ("currency_amount_field/js/currency-widget.js",)
        css = {"all": ("currency_amount_field/css/currency-widget.css",)}

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "currency-field-input",
            "inputmode": "decimal",
            "autocomplete": "off",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def format_value(self, value):
        value = super().format_value(value)
        if value in (None, ""):
            return value
        return group_decimal_string(value)


def group_decimal_string(value):
    """Insert thousands separators into a decimal string like "1234.5"."""
    s = str(value).strip()
    sign = ""
    if s.startswith("-"):
        sign, s = "-", s[1:]

    if "." in s:
        int_part, frac_part = s.split(".", 1)
    else:
        int_part, frac_part = s, None

    int_part = int_part or "0"
    if not int_part.isdigit():
        # Not a plain number we know how to group (e.g. already contains
        # separators, or is some other free-form value) - leave it alone.
        return value

    groups = []
    while len(int_part) > 3:
        groups.insert(0, int_part[-3:])
        int_part = int_part[:-3]
    groups.insert(0, int_part)
    grouped = ",".join(groups)

    if frac_part is not None:
        return f"{sign}{grouped}.{frac_part}"
    return f"{sign}{grouped}"
