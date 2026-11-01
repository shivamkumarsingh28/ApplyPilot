/* Popup logic: sign in, scan the active tab, ask the API to map fields, let the user review, then fill.
   File fields are matched to vault documents (lib/vaultMatcher.js): one suggested
   file per field, incompatible types hidden, attach on click only. Never submits. */
const $ = (id) => document.getElementById(id);
let state = { token: null, api: "http://localhost:8000/api/v1", mappings: [], fields: [], fileMatches: [], tabId: null };

let _pdfPreviewMod = null;
async function loadPdfPreview() {
  // pdf.js is large; load it lazily, only when a PDF preview is requested.
  if (!_pdfPreviewMod) _pdfPreviewMod = await import("./lib/pdfPreview.js");
  return _pdfPreviewMod;
}

async function load() {
  const saved = await chrome.storage.local.get(["token", "api"]);
  state.token = saved.token || null;
  state.api = saved.api || state.api;
  $("api").value = state.api;
  render();
}

function render() {
  $("login").hidden = !!state.token;
  $("main").hidden = !state.token;
  $("logout").hidden = !state.token;
}

async function call(path, body) {
  const res = await fetch(state.api + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + state.token },
    body: JSON.stringify(body),
  });
  if (res.status === 401) { await signOut(); throw new Error("Session expired. Sign in again."); }
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

async function signIn() {
  $("login-error").textContent = "";
  const api = $("api").value.replace(/\/$/, "");
  try {
    const res = await fetch(api + "/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: $("email").value, password: $("password").value }),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Sign in failed");
    const data = await res.json();
    state.token = data.access_token; state.api = api;
    await chrome.storage.local.set({ token: state.token, api });
    $("password").value = "";
    render();
  } catch (e) { $("login-error").textContent = e.message; }
}

async function signOut() {
  state.token = null;
  await chrome.storage.local.remove("token");
  render();
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function ensureInjected(tab) {
  try {
    await chrome.tabs.sendMessage(tab.id, { type: "applypilot:ping" });
  } catch (e) {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["lib/fieldScanner.js", "lib/filler.js", "lib/vaultMatcher.js", "content.js"],
    });
  }
}

async function scan() {
  $("status").textContent = "Scanning...";
  $("rows").innerHTML = ""; $("vault").innerHTML = ""; $("fill").hidden = true; $("attach-all").hidden = true;
  try {
    const tab = await activeTab();
    state.tabId = tab.id;
    await ensureInjected(tab);
    const { fields } = await chrome.tabs.sendMessage(tab.id, { type: "applypilot:scan" });
    if (!fields.length) { $("status").textContent = "No fillable fields found on this page."; return; }
    state.fields = fields;
    await loadVault(fields.filter((f) => f.type === "file"));
    const result = await call("/forms/map", { fields: fields.filter((f) => f.type !== "file") });
    state.mappings = result.mappings;
    $("status").textContent = result.summary.filled + " of " + result.summary.total + " fields ready. " + result.summary.needs_review + " need a look.";
    renderRows();
  } catch (e) {
    const hint = /Receiving end|Could not establish connection|No tab/i.test(e.message)
      ? " The extension could not reach this page — reload the tab, and avoid chrome:// or extension pages."
      : /Failed to fetch|NetworkError/i.test(e.message)
        ? " The ApplyPilot backend is not reachable — start it, and check the API address."
        : "";
    $("status").textContent = "Error: " + e.message + hint;
  }
}

function renderRows() {
  const ul = $("rows");
  ul.innerHTML = "";
  state.mappings.forEach((m, i) => {
    const field = state.fields.find((f) => f.index === m.index) || {};
    const li = document.createElement("li");
    if (m.skipped) {
      li.className = "skip"; li.textContent = (field.label || m.id) + ": skipped (never auto-filled)";
      ul.appendChild(li); return;
    }
    if (m.needs_review) li.className = "review";
    const head = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox"; box.checked = m.value !== null && !m.needs_review; box.dataset.i = i;
    head.append(box, " " + (field.label || m.id || "field"));
    const input = document.createElement("input");
    input.type = "text"; input.value = m.value || ""; input.placeholder = m.value === null ? m.reason : "";
    input.addEventListener("input", () => { m.value = input.value; box.checked = input.value !== ""; });
    li.append(head, input);
    ul.appendChild(li);
  });
  $("fill").hidden = false;
}

async function loadVault(fileFields) {
  const ul = $("vault");
  ul.innerHTML = "";
  if (!window.ApplyPilotVault) { // popup.html must load lib/vaultMatcher.js before popup.js
    ul.innerHTML = "<li class='muted'>Extension file missing (lib/vaultMatcher.js). Reload the extension in chrome://extensions.</li>";
    return;
  }
  if (!fileFields.length) { ul.innerHTML = "<li class='muted'>No file (upload) fields on this page.</li>"; return; }
  const res = await fetch(state.api + "/documents", { headers: { Authorization: "Bearer " + state.token } });
  if (!res.ok) { ul.innerHTML = "<li class='muted'>Could not load your vault. Sign in again?</li>"; return; }
  const docs = await res.json();
  const tab = state.tabId ? await chrome.tabs.get(state.tabId).catch(() => null) : null;
  const host = tab && tab.url ? new URL(tab.url).hostname : "";
  // The notice open in ApplyPilot is not known here; copies made for any notice still rank above originals.
  state.fileMatches = window.ApplyPilotVault.matchFields(fileFields, docs, null);
  const memory = await chrome.storage.local.get(null);
  for (const match of state.fileMatches) {
    const f = match.field;
    const li = document.createElement("li");
    li.className = "filefield";
    const title = document.createElement("div");
    title.textContent = (f.label || f.name || "File") + " — needs: " + String(f.kind || "file").replace(/_/g, " ")
      + (f.accept ? " (" + f.accept + ")" : "") + (f.customUpload ? " [custom upload widget]" : "");
    const badge = document.createElement("span");
    badge.className = "badge " + match.confidence;
    badge.textContent = match.confidence === "exact" ? "Exact match" : match.confidence === "possible" ? "Please choose" : "No file";
    title.append(" ", badge);
    const why = document.createElement("div");
    why.className = "muted small";
    why.textContent = (f.hint ? f.hint + " · " : "") + "Why: " + match.reason;
    const row = document.createElement("div");
    row.className = "row";
    const sel = document.createElement("select");
    sel.dataset.index = f.index;
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = match.choices.length ? "— choose a file —" : "No matching file in your vault — add it in ApplyPilot first";
    sel.appendChild(empty);
    const remembered = memory[window.ApplyPilotVault.choiceKey(host, f)];
    match.choices.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d.id;
      opt.textContent = d.filename + " (" + d.kind.replace(/_/g, " ") + (d.is_original ? "" : ", copy")
        + (d.size ? ", " + Math.max(1, Math.round(d.size / 1024)) + " KB" : "") + ")";
      sel.appendChild(opt);
    });
    // Pre-select only a confident suggestion or a remembered choice. A "possible" match
    // stays unchosen on purpose: mid-form, a forced wrong guess is worse than one tap.
    const preselect = (match.suggested && match.suggested.id) || remembered;
    if (preselect && match.choices.some((d) => String(d.id) === String(preselect))) sel.value = String(preselect);
    const warn = document.createElement("div");
    warn.className = "warn small";
    const previewImg = document.createElement("img");
    previewImg.className = "thumb";
    previewImg.alt = "Preview of the chosen file";
    previewImg.hidden = true;
    const previewCanvas = document.createElement("canvas");
    previewCanvas.className = "thumb";
    previewCanvas.hidden = true;
    const previewNote = document.createElement("div");
    previewNote.className = "muted small";
    let previewBlobUrl = "";
    const clearPreview = () => {
      previewImg.hidden = true; previewImg.removeAttribute("src");
      previewCanvas.hidden = true; previewNote.textContent = "";
      if (previewBlobUrl) { URL.revokeObjectURL(previewBlobUrl); previewBlobUrl = ""; }
    };
    const sync = () => {
      const docRow = match.choices.find((d) => String(d.id) === sel.value);
      warn.textContent = docRow ? window.ApplyPilotVault.sizeWarning(f, docRow) : "";
      btn.disabled = !docRow;
      clearPreview();
    };
    const previewBtn = document.createElement("button");
    previewBtn.textContent = "Preview";
    previewBtn.className = "small";
    // Preview stays INSIDE the popup (image = thumbnail, PDF = page 1 on a canvas).
    // Never a new tab: the user is mid-form and must not lose their place.
    previewBtn.addEventListener("click", async () => {
      const docRow = match.choices.find((d) => String(d.id) === sel.value);
      if (!docRow) { previewNote.textContent = "Choose a file first."; return; }
      previewNote.textContent = "Loading preview...";
      try {
        const res = await fetch(state.api + "/documents/" + docRow.id + "/download", { headers: { Authorization: "Bearer " + state.token } });
        if (!res.ok) throw new Error("download " + res.status);
        const blob = await res.blob();
        clearPreview();
        if ((docRow.mime || "").startsWith("image/")) {
          previewBlobUrl = URL.createObjectURL(blob);
          previewImg.src = previewBlobUrl; previewImg.hidden = false;
          previewNote.textContent = docRow.filename;
        } else if ((docRow.mime || "").toLowerCase().includes("pdf") || docRow.filename.toLowerCase().endsWith(".pdf")) {
          const mod = await loadPdfPreview();
          const info = await mod.renderPdfFirstPage(await blob.arrayBuffer(), previewCanvas, 200);
          previewCanvas.hidden = false;
          previewNote.textContent = docRow.filename + " — page 1 of " + info.pages + " (preview only, nothing opened)";
        } else {
          previewNote.textContent = docRow.filename + ": preview is not available for this file type. Use Attach and check it on the page.";
        }
      } catch (err) { previewNote.textContent = "Preview failed: " + err.message; }
    });
    const btn = document.createElement("button");
    btn.textContent = "Attach";
    const st = document.createElement("span");
    st.className = "muted small";
    st.dataset.statusFor = f.index;
    btn.addEventListener("click", async () => {
      const docRow = match.choices.find((d) => String(d.id) === sel.value);
      if (!docRow) { st.textContent = "Choose a file first."; return; }
      await chrome.storage.local.set({ [window.ApplyPilotVault.choiceKey(host, f)]: docRow.id });
      await attach(f, docRow, st);
    });
    sel.addEventListener("change", sync);
    row.append(sel, previewBtn, btn, st);
    li.append(title, why, row, warn, previewImg, previewCanvas, previewNote);
    ul.appendChild(li);
    sync();
  }
  // Attach-all uses only confident suggestions; "please choose" fields are left for the user.
  $("attach-all").hidden = !state.fileMatches.some((m) => m.suggested);
}

async function attach(field, docRow, statusEl) {
  const set = (t) => { if (statusEl) statusEl.textContent = t; $("status").textContent = t; };
  set("Attaching " + docRow.filename + "...");
  try {
    const tab = state.tabId ? await chrome.tabs.get(state.tabId).catch(() => null) || await activeTab() : await activeTab();
    await ensureInjected(tab);
    const res = await fetch(state.api + "/documents/" + docRow.id + "/download", { headers: { Authorization: "Bearer " + state.token } });
    if (!res.ok) throw new Error("Vault download failed (" + res.status + ")");
    const bytes = Array.from(new Uint8Array(await res.arrayBuffer()));
    const out = await chrome.tabs.sendMessage(tab.id, { type: "applypilot:attach", index: field.index, bytes, filename: docRow.filename, mime: docRow.mime });
    if (out && out.attached) { set("Attached " + docRow.filename + " ✓ — check it on the page before submitting."); return; }
    // Fallback: some sites block script attachment — save to downloads instead.
    const blobUrl = URL.createObjectURL(new Blob([new Uint8Array(bytes)], { type: docRow.mime }));
    const a = document.createElement("a");
    a.href = blobUrl; a.download = docRow.filename; a.click();
    URL.revokeObjectURL(blobUrl);
    set("This site blocked automatic attach (" + ((out && out.reason) || "unknown") + "). " + docRow.filename + " is in your downloads — attach it manually"
      + (field.customUpload ? " using the page's Upload button." : "."));
  } catch (e) { set("Error: " + e.message); }
}

async function attachAll() {
  for (const match of state.fileMatches) {
    if (!match.suggested) continue; // only confident matches; "please choose" waits for the user
    const st = document.querySelector("[data-status-for='" + match.field.index + "']");
    if (st) st.textContent = "Exact matches only — check the “Please choose” fields yourself.";
    await attach(match.field, match.suggested, st);
  }
}

async function fill() {
  const boxes = Array.from($("rows").querySelectorAll('input[type=checkbox]')).filter((b) => b.checked);
  const items = boxes.map((b) => { const m = state.mappings[Number(b.dataset.i)]; return { index: m.index, value: m.value, needsReview: m.needs_review }; });
  const tab = await activeTab();
  await ensureInjected(tab);
  const res = await chrome.tabs.sendMessage(tab.id, { type: "applypilot:fill", items });
  $("status").textContent = "Filled " + res.filled + " fields." + (res.missing.length ? " " + res.missing.length + " could not be found." : "");
}

$("signin").addEventListener("click", signIn);
$("logout").addEventListener("click", signOut);
$("scan").addEventListener("click", scan);
$("fill").addEventListener("click", fill);
$("attach-all").addEventListener("click", attachAll);
load();
