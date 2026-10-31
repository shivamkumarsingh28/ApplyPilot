/* Popup logic: sign in, scan the active tab, ask the API to map fields, let the user review, then fill. */
const $ = (id) => document.getElementById(id);
let state = { token: null, api: "http://localhost:8000/api/v1", mappings: [], fields: [] };

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

async function scan() {
  $("status").textContent = "Scanning...";
  $("rows").innerHTML = ""; $("fill").hidden = true;
  try {
    const tab = await activeTab();
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["lib/fieldScanner.js", "lib/filler.js", "content.js"] });
    const { fields } = await chrome.tabs.sendMessage(tab.id, { type: "applypilot:scan" });
    if (!fields.length) { $("status").textContent = "No fillable fields found on this page."; return; }
    await loadVault(fields.filter((f) => f.type === "file"));
    const result = await call("/forms/map", { fields: fields.filter((f) => f.type !== "file") });
    state.fields = fields; state.mappings = result.mappings;
    $("status").textContent = result.summary.filled + " of " + result.summary.total + " fields ready. " + result.summary.needs_review + " need a look.";
    renderRows();
  } catch (e) { $("status").textContent = "Error: " + e.message; }
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
  if (!fileFields.length) { ul.innerHTML = "<li class='muted'>No file fields on this page.</li>"; return; }
  const res = await fetch(state.api + "/documents", { headers: { Authorization: "Bearer " + state.token } });
  if (!res.ok) return;
  const docs = await res.json();
  for (const field of fileFields) {
    for (const d of docs) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.textContent = `${field.label || "file"} ← ${d.filename} (${d.kind})`;
      btn.addEventListener("click", () => attach(field, d));
      li.appendChild(btn);
      ul.appendChild(li);
    }
  }
}

async function attach(field, docRow) {
  $("status").textContent = "Attaching " + docRow.filename + "...";
  try {
    const res = await fetch(state.api + "/documents/" + docRow.id + "/download", { headers: { Authorization: "Bearer " + state.token } });
    if (!res.ok) throw new Error("Download failed");
    const bytes = Array.from(new Uint8Array(await res.arrayBuffer()));
    const tab = await activeTab();
    const out = await chrome.tabs.sendMessage(tab.id, { type: "applypilot:attach", index: field.index, bytes, filename: docRow.filename, mime: docRow.mime });
    if (out && out.attached) { $("status").textContent = "Attached " + docRow.filename + ". Review it on the page."; return; }
    // Fallback (plan 4.7): some sites block script attachment — save to downloads instead.
    const blobUrl = URL.createObjectURL(new Blob([new Uint8Array(bytes)], { type: docRow.mime }));
    const a = document.createElement("a");
    a.href = blobUrl; a.download = docRow.filename; a.click();
    URL.revokeObjectURL(blobUrl);
    $("status").textContent = "This site blocked automatic attach. Please attach this file yourself: it is in your downloads now.";
  } catch (e) { $("status").textContent = "Error: " + e.message; }
}

async function fill() {
  const boxes = Array.from($("rows").querySelectorAll('input[type=checkbox]')).filter((b) => b.checked);
  const items = boxes.map((b) => { const m = state.mappings[Number(b.dataset.i)]; return { index: m.index, value: m.value, needsReview: m.needs_review }; });
  const tab = await activeTab();
  const res = await chrome.tabs.sendMessage(tab.id, { type: "applypilot:fill", items });
  $("status").textContent = "Filled " + res.filled + " fields." + (res.missing.length ? " " + res.missing.length + " could not be found." : "");
}

$("signin").addEventListener("click", signIn);
$("logout").addEventListener("click", signOut);
$("scan").addEventListener("click", scan);
$("fill").addEventListener("click", fill);
load();
