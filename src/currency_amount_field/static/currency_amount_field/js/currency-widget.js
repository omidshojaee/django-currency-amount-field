(function () {
  "use strict";

  function groupInteger(digits) {
    return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  function formatValue(raw) {
    var negative = raw.indexOf("-") === 0;
    var s = raw.replace(/[^0-9.]/g, "");

    var firstDot = s.indexOf(".");
    if (firstDot !== -1) {
      s = s.slice(0, firstDot + 1) + s.slice(firstDot + 1).replace(/\./g, "");
    }

    var parts = s.split(".");
    var intPart = parts[0] || "";
    var fracPart = parts.length > 1 ? parts[1] : undefined;

    intPart = intPart.replace(/^0+(?=\d)/, "");
    var grouped = intPart ? groupInteger(intPart) : "";

    var result = grouped;
    if (fracPart !== undefined) {
      result += "." + fracPart.slice(0, 2);
    }
    if (!result) {
      return "";
    }
    return (negative ? "-" : "") + result;
  }

  function attach(input) {
    if (input.dataset.currencyFieldAttached) {
      return;
    }
    input.dataset.currencyFieldAttached = "1";

    input.addEventListener("input", function () {
      var before = input.value;
      var selectionFromEnd = before.length - input.selectionStart;
      var after = formatValue(before);
      input.value = after;
      var pos = Math.max(0, after.length - selectionFromEnd);
      input.setSelectionRange(pos, pos);
    });

    input.addEventListener("blur", function () {
      input.value = formatValue(input.value);
    });
  }

  function init(root) {
    var scope = root || document;
    var inputs = scope.querySelectorAll("input.currency-field-input");
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
})();
