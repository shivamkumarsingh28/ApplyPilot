# ApplyPilot Extension — Complete Code Document

This is the **only document file created for the `extension/` folder**, as requested. It is not called README.
Read it top to bottom and you will understand **every file and every important line of code**:
how the popup, the page scanner, and the filler fit together, how vault files get attached to a
form, and exactly where to add future features.

> **What this is:** a Manifest V3 Chrome extension that fills job/admission forms from the user's
> ApplyPilot profile — and, since Phase 2, attaches vault documents (photo, signature, marksheets)
> to file fields. Two inviolable rules shape every line: **the extension never submits a form**,
> and **sensitive fields (password, captcha, OTP, ID/payment) are never touched**.

> **Vault-attach enhancement:** each file field is now classified (`photo`, `signature`,
> `marksheet_10/12`, `degree`, `caste_certificate`, `domicile`, `id_proof`, `birth_certificate`,
> `certificate`, `other`) from its label/name/`accept` by `fieldScanner.fileKindFor`, with nearby
> hint text ("JPG only, max 200KB") captured and hidden inputs flagged `customUpload` instead of
> being skipped. `lib/vaultMatcher.js` scores vault documents per field — exact kind first,
> notice application copies above originals — and **excludes type-incompatible files** (no PDF
> offered for an `image/*` field). The popup shows one card per file field with the best match
> pre-selected, a changeable dropdown, per-field status, and **Attach all suggested**. Attach still
> happens only on click: bytes are fetched from the vault at that moment, set via `DataTransfer`,
> the input is outlined green, and blocked sites fall back to a downloads save with instructions.
> Manual test: load the extension unpacked, open `samples/sample_form.html`, sign in, Scan —
> photo/signature/certificate fields each show their suggested vault file.

> **User-in-between (never force a guess):** matching returns a confidence. `exact` (one clear
> kind+type winner, non-generic field) is pre-selected; `possible` (tie between two files, or a
> generic field like "certificate") pre-selects **nothing** — the popup shows a "Please choose"
> badge and Attach stays disabled until the user picks. Every card shows a *Why* line (which vault
> tag/type/copy won), file sizes in KB, a **Preview** (image thumbnail inline; PDFs render page 1
> to a canvas in the popup via `lib/pdfPreview.js` + vendored pdf.js — never a new tab, so the
> user never loses their place mid-form),
> and a size warning when the chosen file breaks the field's hint ("max 50 KB"). A successful
> attach outlines the field green **and** prints a visible "✓ ApplyPilot: filename" label next to
> it on the page. Choices are remembered per website + field (`choice:<host>:<field>` in
> `chrome.storage.local`) and pre-selected next time. **Attach all** attaches only `exact`
> matches — `possible` fields always wait for the user.

---

## Contents

1. [The one idea behind the extension](#1-the-one-idea-behind-the-extension)
2. [Folder map](#2-folder-map)
3. [End-to-end flows](#3-end-to-end-flows)
4. [File-by-file, line-by-line](#4-file-by-file-line-by-line)
   - 4.1 `manifest.json` — permissions and wiring
   - 4.2 `popup.html` + `popup.css` — the popup shell
   - 4.3 `popup.js` — popup brain: sign-in, scan, review, fill, vault attach
   - 4.4 `content.js` — the in-page message bridge
   - 4.5 `lib/fieldScanner.js` — finding and labelling form fields
   - 4.6 `lib/filler.js` — writing values and attaching files like a human
   - 4.7 `tests/scanner.test.js` — how the tests prove it works
   - 4.8 `package.json` (+ lockfile)
5. [The message protocol (popup ⇄ page)](#5-the-message-protocol-popup--page)
6. [Security and privacy model](#6-security-and-privacy-model)
7. [How to load, run, and test](#7-how-to-load-run-and-test)
8. [How to add a new feature (recipes)](#8-how-to-add-a-new-feature-recipes)
9. [Known limitations and improvement ideas](#9-known-limitations-and-improvement-ideas)
10. [Glossary](#10-glossary)

---

## 1. The one idea behind the extension

The extension is **three pieces with strict jobs**, mirroring the backend's layering:

```
┌─────────────┐   chrome.tabs.sendMessage    ┌──────────────┐   direct function calls   ┌───────────────┐
│  popup.js   │ ───────────────────────────► │  content.js  │ ────────────────────────► │ fieldScanner  │
│ (extension  │ ◄─────────────────────────── │  (injected   │                           │ filler        │
│  context)   │        sendResponse          │   into page) │                           │ (pure DOM)    │
└─────────────┘                              └──────────────┘                           └───────────────┘
      │  fetch (Bearer token)
      ▼
  Backend API  /auth/login · /forms/map · /documents · /documents/{id}/download
```

- **The popup** is the UI and the only piece that talks to the backend or holds the token.
- **The content script** is a thin bridge injected into the active tab *only when the user opens
  the popup and scans* (the `activeTab` permission model — no always-on access to pages).
- **The two `lib/` modules are pure DOM code** with no `chrome.*` APIs, which is why they run
  unchanged inside jsdom in the unit tests. All intelligence about *what value goes where* lives
  in the backend (`/forms/map`); the extension's page-side job is only: describe fields faithfully,
  then write exactly what the user approved.

The field-index contract ties scanner to filler: the scanner stamps each element with
`data-applypilot-idx="<n>"`, and the filler (or a later attach call) finds the element again by
that attribute. Indexes are assigned by the scanner alone — popup code must never invent one.

---

## 2. Folder map

```
extension/
├── DOCUMENT.md          ◄── this file (the only document created for this folder)
├── manifest.json        MV3 manifest: popup, permissions, host access
├── popup.html           popup markup (login section + main section)
├── popup.css            popup styling (360px fixed-width panel)
├── popup.js             popup logic: auth, scan orchestration, review UI, fill, vault attach
├── content.js           injected bridge: answers scan / fill / attach messages
├── lib/
│   ├── fieldScanner.js  pure DOM: find fields, label them, describe them (+ file fields)
│   └── filler.js        pure DOM: set values like a human typing; attach files via DataTransfer
├── tests/
│   └── scanner.test.js  node:test + jsdom tests over the sample form fixture
├── package.json         test + syntax-check scripts; jsdom devDependency
└── package-lock.json    locked dependency tree (generated — do not hand-edit)
```

The test fixture form lives outside this folder: `samples/sample_form.html` at the repo root
(a realistic government-style table form, shared with backend demos).

---

## 3. End-to-end flows

### Flow A — fill a form (the core loop)

```
1. User signs in in the popup (email/password → POST /auth/login → token in chrome.storage.local).
2. User opens the target form tab and clicks "Scan this page".
3. popup.js injects lib/fieldScanner.js, lib/filler.js, content.js into the tab (in that order:
   the libs define window.ApplyPilotScanner/Filler before content.js can answer messages).
4. popup sends {type:"applypilot:scan"} → content.js returns the field descriptors.
5. File-type fields are split off for the vault list (Flow B); the rest go to POST /forms/map
   with the token. The BACKEND maps fields→profile values with confidences (extension decides nothing).
6. popup renders one review row per mapping: checkbox (pre-checked only when a value exists AND
   needs no review), an editable text input (placeholder explains why it's empty), skipped rows
   greyed with the reason. The user edits/unchecks — nothing is written yet.
7. "Fill selected fields" → {type:"applypilot:fill", items:[{index, value, needsReview}]} →
   filler writes each value with framework-friendly events and outlines it (blue = filled,
   amber = please double-check). Status line reports filled/missing counts.
8. The user reviews the page and submits it themselves. Always.
```

### Flow B — attach a vault file to a file field

```
1. During scan, loadVault() lists file fields; it fetches GET /documents (names/kinds only in the
   UI — file bytes are NOT downloaded yet).
2. Each (file field × document) pair becomes a button "Photo upload ← passport.jpg (photo)".
3. Click → download that one document (GET /documents/{id}/download, Bearer) → send bytes to the
   page as {type:"applypilot:attach", index, bytes, filename, mime}.
4. filler.attachFile builds a File, puts it in a DataTransfer, assigns input.files, fires
   input+change. Success → status confirms; the file lived only in memory.
5. If attach fails (site blocks scripted assignment / jsdom-like environments), fallback: the
   popup saves the file to the user's downloads and says exactly: "This site blocked automatic
   attach. Please attach this file yourself: it is in your downloads now."
```

### Flow C — session expiry

Any backend 401 (popup `call()` or scan) → `signOut()`: token removed from storage, UI returns to
the login section with "Session expired. Sign in again." The API base URL is kept so re-login is
one click.

---

## 4. File-by-file, line-by-line

Line numbers refer to the files as they are today. Trivial lines are grouped.

### 4.1 `manifest.json` (11 lines)

| Lines | What and why |
|---|---|
| L1-4 | Manifest V3, name/version/description. The description restates the review-first promise — it's what the Chrome Web Store shows. |
| L5 | `action.default_popup = popup.html` + title: the toolbar button opens the popup. No background service worker is declared — the extension is fully event/user-driven, which is both simpler and more private. |
| L6 | `permissions`: `activeTab` (access the current tab **only** when the user invokes the extension — the least-privilege way to inject), `scripting` (to inject the three files on scan), `storage` (token + API URL in `chrome.storage.local`). No `tabs`, no history, no cookies. |
| L7 | `host_permissions`: only `http://localhost:8000/*` (the dev backend) is pre-granted for fetch. |
| L8 | `optional_host_permissions: https://*/*` — production backend origins are requested at runtime when the user points the popup at a real API URL, instead of demanding all-sites access at install. |
| L9 | `minimum_chrome_version: 110` — guarantees the MV3 + `DataTransfer` behaviours the filler relies on. |

### 4.2 `popup.html` + `popup.css`

**`popup.html`** (32 lines) — two mutually exclusive sections toggled by `hidden`:
`#login` (API address, email, password, Sign in, `#login-error` alert region) and
`#main` (Scan button, `#status` line, `#rows` review list, Fill button, the **Vault files**
section with `#vault`, and the standing "Nothing is submitted" note). A header row holds the
wordmark + Sign out (hidden until signed in). `popup.js` loads last, after all elements exist.

**`popup.css`** (13 lines) — a fixed 360px panel, system font, the same palette tokens as the web
app (brand `#2f5bea`, muted `#667085` — duplicated literals, see §9). Lists scroll (`max-height`
+ overflow) so long forms don't stretch the popup; `.review` rows get an amber left border
(matches the amber outline the filler draws on the page); `.skip` rows are greyed. Buttons are
full-width primaries except `.link`/`.small` variants.

### 4.3 `popup.js` (147 lines) — the popup brain

| Lines | What and why |
|---|---|
| L1-3 | Header comment (the contract), `$` id-helper, and `state`: `{token, api, mappings, fields}` — the only popup state. `api` defaults to the local backend. |
| L5-11 | `load()`: restore `token`/`api` from `chrome.storage.local`, show the saved API URL, `render()`. Runs at script end (L147). |
| L13-17 | `render()`: signed-in → show `#main` + Sign out, hide `#login`; signed-out → the inverse. Single source of truth for the two-section UI. |
| L19-27 | `call(path, body)`: JSON POST with the Bearer token. 401 → `signOut()` + throw "Session expired" (Flow C); other non-OK → throw the backend's `detail` or the status text. This is the popup's `lib/api.ts` equivalent — keep all backend calls going through it (the two vault fetches noted below are the exceptions to align, §9). |
| L29-45 | `signIn()`: reads the API field (trailing slash stripped), plain `fetch` login (no token yet), stores `{token, api}`, clears the password field from the DOM, re-renders; failures land in `#login-error`. `signOut()` (L47-51): drop the stored token, re-render. |
| L53-56 | `activeTab()`: the current tab in the current window — every page operation targets exactly this tab. |
| L58-77 | `scan()`: the Flow A orchestrator. Sets "Scanning…", clears old rows, injects the three scripts **in order** (libs before bridge), asks for fields, and if none: a clear status and stop. Splits off file fields → `loadVault(fileFields)`. Sends the remaining fields to `/forms/map`, stores `fields` + `mappings`, prints the summary ("N of M fields ready. K need a look."), and renders review rows. Errors surface in the status line (never a dead popup). |
| L79-98 | `renderRows()`: one `<li>` per mapping, built with DOM APIs (no `innerHTML` with user data — field labels are page-controlled text and must never become markup). Skipped mappings render as a grey explanation row. Otherwise: a checkbox (pre-checked only when `value !== null && !needs_review` — uncertain values require an explicit opt-in), the label, and an editable input whose placeholder explains emptiness (`m.reason`); typing in the input updates `m.value` and checks the box. The Fill button is revealed last. |
| L100-125 | `loadVault(fileFields)` + `attach(field, docRow)`: Flow B. Empty file-field list → an explanatory row. Fetches the document list (metadata only). Builds one button per field×document pair. `attach` downloads the bytes only now, converts them to a plain array (message passing can't carry an ArrayBuffer view portably), sends `applypilot:attach`, and on failure performs the **downloads fallback**: Blob → object URL → synthetic anchor `download` click → the exact "attach it yourself, it's in your downloads" status. |
| L127-133 | `fill()`: collects checked rows → `{index, value, needsReview}` items → `applypilot:fill` → status "Filled N fields" (+ how many indexes weren't found, e.g. if the page changed since scan). |
| L135-146 | Event wiring: sign-in, sign-out, scan, fill buttons; `load()` kickoff. All listeners attach at the bottom after every function is defined. |

### 4.4 `content.js` (21 lines) — the in-page bridge

| Lines | What and why |
|---|---|
| L1-8 | Header comment: injected **only** on user action (never auto-run on sites); documents the two original message types. |
| L10-11 | IIFE + `window.__applypilotLoaded` guard: re-injecting on a second scan must not register duplicate listeners (which would double-fill). |
| L12 | One `chrome.runtime.onMessage` listener for everything. |
| L13-14 | `applypilot:scan` → `ApplyPilotScanner.scanFields(document)` + the page hostname (for status/debugging), via `sendResponse`. |
| L15-16 | `applypilot:fill` → `ApplyPilotFiller.fillFields(document, msg.items)`, response is `{filled, missing}`. |
| L17-19 | `applypilot:attach` → bytes arrive as a plain array, re-wrapped in `Uint8Array`, → `attachFile(document, index, bytes, filename, mime)`; response `{attached, reason?}`. |
| L20 | `return false` — responses are synchronous; no async channel is kept open. |

### 4.5 `lib/fieldScanner.js` (122 lines) — describing the page

Pure DOM, dual export (browser global `window.ApplyPilotScanner` / CommonJS for tests — the
tail block picks based on `module`). Vocabulary: each found control becomes a **descriptor**
`{index, id, name, label, placeholder, type, autocomplete, pattern, options}` (+ `accept` for files).

| Lines | What and why |
|---|---|
| L1-10 | Header (purity, the `data-applypilot-idx` contract, jsdom-runnable), IIFE `(root)`, `"use strict"`. |
| L12 | `SKIP_TYPES` — types never returned: hidden/submit/button/image/reset/password. **File is deliberately absent** (Phase 2: file fields are detected for vault attach; the *filler's* text path still never writes them — the backend mapper also hard-skips them). |
| L13 | `ATTR = "data-applypilot-idx"` — the stamp name shared with the filler. |
| L15-17 | `clean()`: collapse whitespace, strip trailing `*`/`:` label decorations ("Name of Candidate *:" → "Name of Candidate"). |
| L19-23 | `isVisible()`: hidden attribute/`aria-hidden`/computed `display:none`/`visibility:hidden` — invisible controls (honeypots, collapsed sections) are not fillable. |
| L26-48 | `labelFor(el)` — the label-resolution cascade, most-trustworthy first: explicit `<label for=id>` → wrapping `<label>` (minus the control's own value) → `aria-labelledby` targets → `aria-label` → **previous table cell** (government portals put labels in the adjacent `<td>` — this line is why the sample form works) → preceding sibling text → placeholder/title/name fallback. Good labels are the single biggest input to backend mapping quality. |
| L50-54 | `optionsOf(select)`: value+label pairs, dropping the empty "--Select--" placeholder so the backend matches real options only. |
| L56-106 | `scanFields(doc)`: iterate `input, select, textarea`. Type resolution (select/textarea by tag, else the `type` attribute, defaulting text). Skips: `SKIP_TYPES`, disabled. **File inputs** (Phase 2) get their own descriptor with the `accept` attribute and are returned, not skipped. Read-only non-file controls are skipped (can't be filled anyway). **Radios** are grouped by name into one descriptor whose `options` accumulate each button's own label, with the fieldset `<legend>` as the group label; only the first radio of a group is stamped (the filler re-expands the group by name). **Checkboxes are skipped entirely** — consent must be a human click. Every accepted control is stamped with its index **as it is described**, so the filler can find it later even if the DOM shifts. |
| L108-111 | Return shape `{index, id (or name, or field-N), name, label, placeholder, type, autocomplete, pattern, options}` — exactly what the backend's `FormField` schema accepts. |
| L113-115 | `{scanFields, labelFor, ATTR}` exports. |

### 4.6 `lib/filler.js` (69 lines) — writing like a human

Also pure DOM, dual export (`window.ApplyPilotFiller`). Two operations:

| Lines | What and why |
|---|---|
| L1-8 | Header: values are written "the way a person typing would" so React/Vue/Angular notice; never submits; never touches password/file/captcha inputs via the text path. |
| L9 | `(root)` IIFE + strict. |
| L11 | Shares `ATTR` with the scanner (duplicated literal, single-character contract — keep in sync). |
| L13-23 | `setNativeValue(el, value)`: the framework-compatibility core. Modern frameworks wrap the `value` setter for change tracking, so a naive `el.value = x` is invisible to them. This grabs the **prototype's** setter (from `HTMLInputElement`/`HTMLSelectElement`/`HTMLTextAreaElement` as appropriate), calls it directly to bypass the wrapper, then dispatches bubbling `input` + `change` events so the framework re-reads and validates the new value. |
| L25-46 | `fillFields(doc, items)`: per item — empty values skipped; find by `data-applypilot-idx` (missing → recorded in `missing`, e.g. the page navigated); radios re-expand the named group and check the matching value radio (dispatching input/change); everything else via `setNativeValue`. Each written element gets an outline: brand blue `#2f5bea` = filled, amber `#e0a100` = needs review, plus a `title` tooltip saying which. Returns `{filled, missing}` — the popup reports both. |
| L48-62 | `attachFile(doc, index, bytes, filename, mime)` (Phase 2): locate the input, require `type === "file"`, build a real `File`, put it in a `DataTransfer`, assign `input.files` (the only scriptable way), fire `input` + `change`. All wrapped in try/catch returning `{attached:false, reason}` — sites *can* block this, and the popup's downloads fallback depends on the honest failure. |
| L64-66 | Exports `{fillFields, setNativeValue, attachFile}`. |

### 4.7 `tests/scanner.test.js` (85 lines) — node:test + jsdom

| Lines | What and why |
|---|---|
| L1-16 | Harness: loads `samples/sample_form.html` into jsdom (`runScripts: "outside-only"` so the fixture's own scripts, if any, don't run), makes it the global `window`, and `require`s both lib modules fresh per test via `load()` — proving the pure-DOM claim (no `chrome.*` anywhere). |
| L18-28 | Scanner finds the fields and reads **table-style labels** exactly ("Name of Candidate", "Father's Name"), the DOB placeholder, and 3 state options. |
| L30-37 | Safety: no password/checkbox descriptors ever; radios collapse into one grouped descriptor with options `M/F`. |
| L39-52 | File fields (Phase 2): when the fixture has file inputs they're reported; and a synthetic file input gets a descriptor + `attachFile` returns a boolean verdict without throwing (jsdom lacks Chrome's `DataTransfer` fidelity, so the test asserts the *graceful contract*, not success — honest testing of an environment difference). |
| L54-85 | Filling: text/select/radio filled by index, `change` events actually fire (counter listener), values land in the DOM; skipped/unknown indexes reported in `missing`. |

Run via `npm test` (`node --test`). `npm run check` syntax-checks all four JS sources with
`node --check` — the cheap gate before loading the extension.

### 4.8 `package.json` (12 lines)

`name/version/private` + two scripts (`test`, `check` above) and the single devDependency
`jsdom ^24` (the DOM the tests run in). No runtime dependencies — the shipped extension is
dependency-free vanilla JS, which keeps the Web Store review surface tiny. `package-lock.json`
pins the jsdom tree; regenerate with `npm install`, never hand-edit.

---

## 5. The message protocol (popup ⇄ page)

All messages are `chrome.tabs.sendMessage(tabId, …)` from the popup; `content.js` answers
synchronously via `sendResponse`. Scripts must be injected (`executeScript` with the two libs,
then content.js) before the first message — `scan()` is the only injector.

| Message | Payload | Response | Handler |
|---|---|---|---|
| `applypilot:scan` | — | `{fields: Descriptor[], url: hostname}` | `scanner.scanFields` |
| `applypilot:fill` | `{items: [{index, value, needsReview}]}` | `{filled: number, missing: number[]}` | `filler.fillFields` |
| `applypilot:attach` | `{index, bytes: number[], filename, mime}` | `{attached: boolean, reason?: string}` | `filler.attachFile` |

Backend calls (popup only, Bearer token): `POST /auth/login`, `POST /forms/map`,
`GET /documents`, `GET /documents/{id}/download`. Field descriptors sent to `/forms/map`
exclude file fields (the backend would skip them anyway; vault handles them locally).

---

## 6. Security and privacy model

- **Least privilege by permission:** `activeTab` + user-invoked injection only; no persistent
  content script, no `<all_urls>`, production API origins requested as *optional* permissions.
- **Token storage:** `chrome.storage.local` (extension-private, not page-readable). Cleared on
  sign-out and on any 401. The password field is cleared from the DOM after login.
- **Files in Flow B** are fetched with the token, held only as in-memory bytes/arrays, attached or
  downloaded-on-fallback, and **never** written to extension storage.
- **Never-fill list is enforced twice:** the scanner withholds password/checkbox (and captcha-like
  types via skip types), and the backend mapper independently skips password/file/captcha/OTP/
  ID/payment fields — a bug in one layer cannot fill a password.
- **Review-first:** only confident, backend-approved values are pre-checked; everything is
  editable in the popup; outlines on the page distinguish filled vs check-me; submission is
  always the user's own click.
- **No markup injection:** popup rows are built with DOM APIs; page-controlled labels are only
  ever assigned as text/properties, never `innerHTML`.

---

## 7. How to load, run, and test

```powershell
# Load unpacked: chrome://extensions → Developer mode → Load unpacked → select this folder.
# Point the popup's "API address" at your backend (default http://localhost:8000/api/v1).

cd extension
node --test tests\scanner.test.js   # or: npm test
npm run check                       # syntax-check popup.js, content.js, both libs
```

Dev loop: edit → `chrome://extensions` → reload card → reopen popup. The injected libs are
re-fetched from disk on every scan (the `__applypilotLoaded` guard prevents duplicate listeners
within the same page session).

---

## 8. How to add a new feature (recipes)

**Fill a new profile attribute (e.g. blood group):** backend first (profile schema + mapper
synonym) — the extension usually needs **no change**: the descriptor already carries label/name,
and the review row renders whatever mapping returns. Only if a new *input kind* appears (e.g.
`type="date"` pickers with segmented UI) do you touch `filler.setNativeValue`.

**Handle a new field widget (e.g. custom dropdown divs):** extend `fieldScanner` to describe it
as an existing descriptor type (options array included) so backend mapping keeps working; extend
`filler` to write it; add a jsdom fixture case. Resist adding a fourth message type until a
widget truly can't be expressed as scan/fill/attach.

**New vault action (e.g. "attach my photo to all file fields"):** popup-only change —
`loadVault`/`attach` already have the pieces; batch the `attach` calls and summarise per-field
results in `#vault`. Keep the downloads fallback per failed field.

**New chat-app-like surface (e.g. a side panel):** MV3 side panels reuse the same popup logic
shape: keep backend calls in the extension context, keep page writes behind the
scan/fill/attach protocol. Don't move token handling into the page context.

**Rules:** never add a `type` to the scanner's output without a filler path (or an explicit
vault path); never pre-check a row the backend flagged `needs_review`; never call the backend
from content/lib code (token stays in the popup); keep lib modules `chrome.*`-free so the jsdom
tests keep covering them; run `npm test` + `npm run check` before loading.

---

## 9. Known limitations and improvement ideas

1. **Palette duplication:** popup.css hard-codes the web app's colours; if the brand changes,
   update both places (or generate popup.css tokens from the same source).
2. **Two vault fetches bypass `call()`** (popup.js `loadVault`/`attach` use raw `fetch`), so a
   401 mid-attach won't auto-sign-out. Route them through a shared helper like the frontend's
   `api.ts` `blob()` path.
3. **`state.fields` vs mappings drift:** after `scan()`, `renderRows` looks fields up by index;
   if a site re-renders between scan and fill, indexes go stale — `missing` counts surface it,
   but a "rescan" prompt on any missing would be friendlier.
4. **Attach is one file per click.** Batch attach + drag-from-popup (the plan's drag variant)
   would reuse `attachFile`; dragging needs a dragstart payload design the current protocol
   doesn't have.
5. **Framework coverage:** `setNativeValue` covers React/Vue/Angular controlled inputs; heavily
   custom widgets (canvas inputs, shadow-DOM components) won't be found by `querySelectorAll` —
   shadow-root traversal in the scanner is the upgrade path.
6. **jsdom ≠ Chrome for `DataTransfer`:** `attachFile` success is only proven in a real browser;
   add a manual test page (`samples/` fixture with a file input) to the QA checklist, or a
   Playwright pass.
7. **API URL is free text** — a typo fails opaquely at login. Validate/normalise on blur and
   offer the optional host-permission request flow for non-localhost URLs (declared in the
   manifest but not yet requested in code).

---

## 10. Glossary

- **Descriptor** — the scanner's JSON description of one field (label, type, options, index).
- **Index (`data-applypilot-idx`)** — the stamp linking a descriptor to its live DOM element.
- **Mapping** — the backend's answer per field: profile key, value, confidence, needs_review, skipped.
- **Review row** — the popup's checkbox + editable input for one mapping; the human approval gate.
- **Downloads fallback** — when a site blocks scripted file attachment, saving the vault file to
  Downloads with instructions instead of failing silently.
- **activeTab** — Chrome's permission granting tab access only on user invocation.
