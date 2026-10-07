(function () {
  "use strict";

  var DEFAULT_DECIMAL_PLACES = 2;
  var SELECTOR = "input[data-currency-widget], input.currency-field-input";

  var ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";
  var PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

  // Read Persian and Arabic-Indic digits and separators as plain 0-9 . , -
  function toAscii(text) {
    return text
      .replace(/[٠-٩]/g, function (d) { return String(d.charCodeAt(0) - 0x0660); })
      .replace(/[۰-۹]/g, function (d) { return String(d.charCodeAt(0) - 0x06F0); })
      .replace(/٫/g, ".") // Arabic decimal separator
      .replace(/[٬،]/g, ",") // Arabic thousands separator, Arabic comma
      .replace(/−/g, "-"); // Unicode minus
  }

  // Keep the script the user is typing in: Persian in, Persian out.
  function digitSet(text) {
    if (/[۰-۹]/.test(text)) {
      return PERSIAN_DIGITS;
    }
    if (/[٠-٩]/.test(text)) {
      return ARABIC_INDIC_DIGITS;
    }
    return null;
  }

  function withDigits(text, digits) {
    if (!digits) {
      return text;
    }
    return text.replace(/[0-9]/g, function (d) { return digits.charAt(Number(d)); });
  }

  function groupInteger(digits) {
    return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function parsePlaces(value) {
    var places = parseInt(value, 10);
    return isNaN(places) || places < 0 ? DEFAULT_DECIMAL_PLACES : places;
  }

  function formatValue(raw, decimalPlaces) {
    var places = decimalPlaces === undefined ? DEFAULT_DECIMAL_PLACES : decimalPlaces;
    var digits = digitSet(raw);
    var ascii = toAscii(raw);
    var negative = ascii.indexOf("-") === 0;
    var s = ascii.replace(/[^0-9.]/g, "");

    var firstDot = s.indexOf(".");
    if (firstDot !== -1) {
      s = s.slice(0, firstDot + 1) + s.slice(firstDot + 1).replace(/\./g, "");
    }

    var parts = s.split(".");
    var intPart = parts[0] || "";
    // A field without decimals has no use for a point or anything after it.
    var fracPart = places > 0 && parts.length > 1 ? parts[1] : undefined;

    intPart = intPart.replace(/^0+(?=\d)/, "");
    var grouped = intPart ? groupInteger(intPart) : "";

    var result = grouped;
    if (fracPart !== undefined) {
      result += "." + fracPart.slice(0, places);
    }
    if (!result) {
      return "";
    }
    return withDigits((negative ? "-" : "") + result, digits);
  }

  function attach(input) {
    if (input.dataset.currencyFieldAttached) {
      return;
    }
    input.dataset.currencyFieldAttached = "1";

    function places() {
      return parsePlaces(input.dataset.decimalPlaces);
    }

    input.addEventListener("input", function (event) {
      // Reformatting in the middle of an IME composition breaks the composition.
      if (event && event.isComposing) {
        return;
      }
      var before = input.value;
      var selectionFromEnd = before.length - input.selectionStart;
      var after = formatValue(before, places());
      input.value = after;
      var pos = Math.max(0, after.length - selectionFromEnd);
      input.setSelectionRange(pos, pos);
    });

    input.addEventListener("compositionend", function () {
      input.value = formatValue(input.value, places());
    });

    input.addEventListener("blur", function () {
      input.value = formatValue(input.value, places());
    });
  }

  function init(root) {
    var scope = root || document;
    if (!scope.querySelectorAll) {
      return;
    }
    var inputs = scope.querySelectorAll(SELECTOR);
    for (var i = 0; i < inputs.length; i++) {
      attach(inputs[i]);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    init(document);
  });

  // Django admin fires this on the newly-added row when you add an inline
  // formset entry; re-scan so the new row's input gets the same behaviour.
  document.addEventListener("formset:added", function (event) {
    init(event.target || document);
  });

  // For tests and for pages that add inputs by hand.
  window.CurrencyAmountField = { formatValue: formatValue, attach: attach, init: init };
})();
