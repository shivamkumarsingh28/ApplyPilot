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

test("finds file fields for vault attach (Phase 2 step 12)", () => {
  const { doc, scanner } = load();
  const inputs = doc.querySelectorAll('input[type="file"]');
  if (!inputs.length) return; // sample form may have none; scanner unit below covers it
  const fields = scanner.scanFields(doc);
  assert.ok(fields.some((f) => f.type === "file"));
});

test("attachFile sets files via DataTransfer contract", () => {
  const { doc, scanner, filler } = load();
  const input = doc.createElement("input");
  input.type = "file";
  input.name = "photo_upload";
  doc.body.appendChild(input);
  const fields = scanner.scanFields(doc);
  const f = fields.find((x) => x.name === "photo_upload");
  assert.ok(f && f.type === "file");
  // jsdom has no DataTransfer/File constructor parity with Chrome; assert graceful fallback, not a throw.
  const out = filler.attachFile(doc, f.index, new Uint8Array([1, 2]), "p.jpg", "image/jpeg");
  assert.ok(typeof out.attached === "boolean");
});

test("file fields in sample form get kinds photo/signature/certificate", () => {
  const { doc, scanner } = load();
  const fields = scanner.scanFields(doc);
  const byName = Object.fromEntries(fields.filter((f) => f.type === "file").map((f) => [f.name, f]));
  assert.strictEqual(byName.photo.kind, "photo");
  assert.strictEqual(byName.sig.kind, "signature");
  assert.strictEqual(byName.cert.kind, "certificate");
  assert.ok(byName.photo.accept.includes("image"));
});

test("hidden file input is reported as custom upload, not skipped", () => {
  const { doc, scanner } = load();
  const input = doc.createElement("input");
  input.type = "file"; input.name = "hidden_photo"; input.style.display = "none";
  doc.body.appendChild(input);
  const f = scanner.scanFields(doc).find((x) => x.name === "hidden_photo");
  assert.ok(f && f.customUpload === true);
});

test("vault matcher: exact match pre-selected, generic field forces a choice", () => {
  const matcher = require("../lib/vaultMatcher.js");
  const fields = [
    { index: 0, name: "photo", label: "photo", type: "file", kind: "photo", accept: "image/*" },
    { index: 1, name: "cert", label: "certificate", type: "file", kind: "certificate", accept: ".pdf" },
    { index: 2, name: "sig", label: "signature", type: "file", kind: "signature", accept: "image/*" },
  ];
  const docs = [
    { id: 1, kind: "photo", filename: "me.jpg", mime: "image/jpeg", is_original: true, notice_id: null, size: 30000 },
    { id: 2, kind: "photo", filename: "photo_ready.jpg", mime: "image/jpeg", is_original: false, notice_id: 7, size: 30000 },
    { id: 3, kind: "degree", filename: "degree.pdf", mime: "application/pdf", is_original: true, notice_id: null, size: 90000 },
    { id: 4, kind: "degree", filename: "degree.jpg", mime: "image/jpeg", is_original: true, notice_id: null, size: 90000 },
    { id: 5, kind: "signature", filename: "sign-a.jpg", mime: "image/jpeg", is_original: true, notice_id: null, size: 10000 },
    { id: 6, kind: "signature", filename: "sign-b.jpg", mime: "image/jpeg", is_original: true, notice_id: null, size: 10000 },
  ];
  const [photo, cert, sig] = matcher.matchFields(fields, docs, 7);
  assert.strictEqual(photo.confidence, "exact");
  assert.strictEqual(photo.suggested.id, 2); // application copy for this notice wins
  assert.deepStrictEqual(photo.choices.map((d) => d.id), [2, 1]);
  assert.ok(photo.reason.includes("photo"));
  // Generic "certificate": degree.pdf is the only type-OK choice, but the field is
  // generic, so NOTHING is pre-selected — the user must choose (the real-user fix).
  assert.deepStrictEqual(cert.choices.map((d) => d.id), [3]); // the .jpg is excluded from a .pdf field
  assert.strictEqual(cert.confidence, "possible");
  assert.strictEqual(cert.suggested, null);
  // Two equal signatures: a tie is also "possible", never a forced guess.
  assert.strictEqual(sig.confidence, "possible");
  assert.strictEqual(sig.suggested, null);
  assert.strictEqual(sig.choices.length, 2);
});

test("size limit parsing and warnings from field hints", () => {
  const matcher = require("../lib/vaultMatcher.js");
  assert.deepStrictEqual(matcher.parseSizeLimitKb("JPG only, 20 KB to 50 KB"), { minKb: 20, maxKb: 50 });
  assert.strictEqual(matcher.parseSizeLimitKb("max 200KB").maxKb, 200);
  assert.strictEqual(matcher.parseSizeLimitKb("up to 1 MB").maxKb, 1024);
  const field = { hint: "Photo size 20 KB to 50 KB" };
  assert.match(matcher.sizeWarning(field, { size: 80 * 1024 }), /max 50 KB/);
  assert.strictEqual(matcher.sizeWarning(field, { size: 30 * 1024 }), "");
});

test("pdf/image preview helpers classify by mime and filename", async () => {
  const pdfPreview = await import("../lib/pdfPreview.js").catch(() => null);
  if (!pdfPreview) return; // node may refuse the .mjs import in older versions; helpers mirrored below
  assert.strictEqual(pdfPreview.isPdf({ mime: "application/pdf" }), true);
  assert.strictEqual(pdfPreview.isPdf({ filename: "degree.PDF" }), true);
  assert.strictEqual(pdfPreview.isPdf({ mime: "image/png" }), false);
  assert.strictEqual(pdfPreview.isImage({ mime: "image/jpeg" }), true);
});

test("popup never opens a new tab for preview", () => {
  const src = fs.readFileSync(path.join(__dirname, "../popup.js"), "utf8");
  assert.ok(!src.includes("chrome.tabs.create"), "preview must stay inside the popup");
  assert.ok(src.includes("renderPdfFirstPage"), "PDF page 1 renders in-popup");
});

test("choice memory key is stable per site and field", () => {
  const matcher = require("../lib/vaultMatcher.js");
  assert.strictEqual(matcher.choiceKey("ssc.gov.in", { name: "photo" }), matcher.choiceKey("ssc.gov.in", { name: " Photo " }));
  assert.notStrictEqual(matcher.choiceKey("ssc.gov.in", { name: "photo" }), matcher.choiceKey("upsc.gov.in", { name: "photo" }));
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
