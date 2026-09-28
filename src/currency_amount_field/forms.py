from django import forms

from .widgets import CurrencyWidget

# Characters a user (or our own JS) might legitimately have in a formatted
# amount besides digits, sign and decimal point.
_GROUPING_CHARS = (",", " ", " ", " ")


class CurrencyFormField(forms.DecimalField):
    """
    A DecimalField that tolerates thousands separators on input, and renders
    with `CurrencyWidget` so they're shown (and kept live) on output too.
    """

    widget = CurrencyWidget

    def to_python(self, value):
        if isinstance(value, str):
            for char in _GROUPING_CHARS:
                value = value.replace(char, "")
            value = value.strip()
        return super().to_python(value)
