"""
A pragmatic (non-exhaustive) list of ISO 4217 currency codes for use as the
default `choices` on the currency-code field that `CurrencyField`
generates. Pass your own `currency_choices=` to `CurrencyField` if you
need currencies not listed here.
"""

CURRENCY_CHOICES = [
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("GBP", "British Pound"),
    ("JPY", "Japanese Yen"),
    ("CHF", "Swiss Franc"),
    ("CAD", "Canadian Dollar"),
    ("AUD", "Australian Dollar"),
    ("NZD", "New Zealand Dollar"),
    ("CNY", "Chinese Yuan"),
    ("HKD", "Hong Kong Dollar"),
    ("SGD", "Singapore Dollar"),
    ("INR", "Indian Rupee"),
    ("BRL", "Brazilian Real"),
    ("MXN", "Mexican Peso"),
    ("ZAR", "South African Rand"),
    ("SEK", "Swedish Krona"),
    ("NOK", "Norwegian Krone"),
    ("DKK", "Danish Krone"),
    ("PLN", "Polish Zloty"),
    ("TRY", "Turkish Lira"),
    ("AED", "UAE Dirham"),
    ("SAR", "Saudi Riyal"),
    ("KRW", "South Korean Won"),
    ("RUB", "Russian Ruble"),
    ("IRR", "Iranian Rial"),
]
