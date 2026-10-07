import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .widgets import CurrencyWidget

# Arabic-Indic (U+0660..) and Persian (U+06F0..) digits, read as 0-9.
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# Arabic decimal and thousands separators, the Arabic comma and the Unicode minus.
_PUNCTUATION = str.maketrans({"٫": ".", "٬": ",", "،": ",", "−": "-"})

# A grouping separator: a comma or one kind of space, and always the same one.
_GROUP = r"[,    ]"
_AMOUNT = re.compile(
    rf"""
    ^(?=[^\d]*\d)                                   # at least one digit
    [+-]?
    (?:\d{{1,3}}(?P<sep>{_GROUP})\d{{3}}(?:(?P=sep)\d{{3}})*   # 1,234,567
       |\d+)?                                        # or 1234567, or nothing (.5)
    (?:\.\d*)?$                                      # optional .fraction
    """,
    re.VERBOSE,
)
_GROUPING_CHARS = re.compile(_GROUP)
# What a mistyped (rather than non-numeric) amount is made of.
_NUMBER_LIKE = re.compile(r"[\d,.+\-    ]+")


class CurrencyFormField(forms.DecimalField):
    """
    A DecimalField that accepts thousands separators and renders with
    `CurrencyWidget`, which shows (and keeps live) the grouping.

    The dot is the decimal point and a comma (or a space) may only separate
    groups of three digits: ``1,234.56`` and ``1 234.56`` are read, ``12,50``
    or ``1.234,56`` are rejected instead of being guessed at, because reading
    ``12,50`` as 1250 would be exactly the kind of silent mistake this field
    exists to prevent. Persian and Arabic-Indic digits and separators are read
    as well. Fields built with ``localize=True`` use Django's locale handling
    instead.
    """

    widget = CurrencyWidget
    default_error_messages = {
        "invalid_grouping": _(
            "Enter a number with a dot as the decimal point; commas may only "
            "separate thousands (for example 1,234.56)."
        ),
    }

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        if self.decimal_places is not None:
            attrs["data-decimal-places"] = str(self.decimal_places)
        return attrs

    def _clean_amount(self, text):
        text = text.translate(_DIGITS).translate(_PUNCTUATION).strip()
        if not text:
            return text
        if not _AMOUNT.match(text):
            # Digits with commas or spaces in the wrong places read as a
            # decimal comma or a typo; anything else is simply not a number.
            if _NUMBER_LIKE.fullmatch(text) and _GROUPING_CHARS.search(text):
                code = "invalid_grouping"
            else:
                code = "invalid"
            raise ValidationError(self.error_messages[code], code=code)
        return _GROUPING_CHARS.sub("", text)

    def to_python(self, value):
        if isinstance(value, str) and not self.localize:
            value = self._clean_amount(value)
        return super().to_python(value)
