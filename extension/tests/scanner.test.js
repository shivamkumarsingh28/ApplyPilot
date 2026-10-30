const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const html = fs.readFileSync(path.join(__dirname, "../../samples/sample_form.html"), "utf8");

function load() {
  const dom = new JSDOM(html, { runScripts: "outside-only" });
  global.window = dom.window;
  const scanner = require("../lib/fieldScanner.js");
  const filler = require("../lib/filler.js");
  return { doc: dom.window.document, scanner, filler };
}

test("finds fields and reads table-style labels", () => {
  const { doc, scanner } = load();
  const fields = scanner.scanFields(doc);
  const byName = Object.fromEntries(fields.map((f) => [f.name, f]));
  assert.strictEqual(byName.cname.label, "Name of Candidate");
  assert.strictEqual(byName.fname.label, "Father's Name");
  assert.strictEqual(byName.dob.placeholder, "DD/MM/YYYY");
  assert.strictEqual(byName.state.options.length, 3);
});

test("skips password, checkbox and groups radios", () => {
  const { doc, scanner } = load();
  const fields = scanner.scanFields(doc);
  assert.ok(!fields.some((f) => f.type === "password" || f.type === "checkbox"));
  const gender = fields.find((f) => f.name === "gender");
  assert.strictEqual(gender.type, "radio");
  assert.deepStrictEqual(gender.options.map((o) => o.value), ["M", "F"]);
});

test("fills text, select and radio fields and fires change events", () => {
  const { doc, scanner, filler } = load();
  const fields = scanner.scanFields(doc);
  const idx = (name) => fields.find((f) => f.name === name).index;
  let changed = 0;
  doc.querySelector('[name="cname"]').addEventListener("change", () => changed++);
  const res = filler.fillFields(doc, [
    { index: idx("cname"), value: "Rahul Kumar Singh" },
    { index: idx("dob"), value: "10/03/2007", needsReview: true },
    { index: idx("state"), value: "BR" },
    { index: idx("gender"), value: "M" },
  ]);
  assert.strictEqual(res.filled, 4);
  assert.strictEqual(doc.querySelector('[name="cname"]').value, "Rahul Kumar Singh");
  assert.strictEqual(doc.querySelector('[name="state"]').value, "BR");
  assert.strictEqual(doc.querySelector('[name="gender"][value="M"]').checked, true);
  assert.strictEqual(changed, 1);
  assert.match(doc.querySelector('[name="dob"]').title, /double-check/);
});

test("does not fill unknown indexes and never submits", () => {
  const { doc, filler } = load();
  let submitted = false;
  doc.getElementById("apply").addEventListener("submit", () => { submitted = true; });
  const res = filler.fillFields(doc, [{ index: 999, value: "x" }]);
  assert.deepStrictEqual(res.missing, [999]);
  assert.strictEqual(submitted, false);
});
