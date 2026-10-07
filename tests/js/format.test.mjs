// Runs with Node's built-in test runner:  node --test tests/js/
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const here = path.dirname(fileURLToPath(import.meta.url));
const script = path.join(
  here,
  "../../src/currency_amount_field/static/currency_amount_field/js/currency-widget.js",
);

// The script only needs a window and a document to load; the formatting
// function does not touch the page.
const window = {};
const document = { addEventListener() {}, querySelectorAll() { return []; } };
vm.runInNewContext(fs.readFileSync(script, "utf8"), { window, document });
const { formatValue } = window.CurrencyAmountField;

const cases = JSON.parse(fs.readFileSync(path.join(here, "format_cases.json"), "utf8"));

for (const { input, places, expected } of cases) {
  test(`formatValue(${JSON.stringify(input)}, ${places === undefined ? "default" : places})`, () => {
    assert.equal(formatValue(input, places), expected);
  });
}

test("the script exposes the helpers it documents", () => {
  assert.equal(typeof window.CurrencyAmountField.attach, "function");
  assert.equal(typeof window.CurrencyAmountField.init, "function");
});
