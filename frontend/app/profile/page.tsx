"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { ExtraField, Profile } from "@/lib/types";

const slug = (label: string) => label.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 41);

const TEXT_FIELDS: [string, string, string?][] = [
  ["full_name", "Full name"], ["father_name", "Father's name"], ["mother_name", "Mother's name"], ["dob", "Date of birth", "date"],
  ["email", "Email", "email"], ["phone", "Mobile number", "tel"], ["alternate_phone", "Alternate mobile number", "tel"],
  ["address_line", "Permanent address"], ["correspondence_address", "Correspondence address (if different)"],
  ["city", "City / town / village"], ["district", "District"],
  ["state", "State"], ["pincode", "PIN / postal code"], ["nationality", "Nationality"], ["category", "Category (general, obc, sc, st, ews)"],
  ["identification_mark", "Visible identification mark (e.g. mole on left cheek)"],
];
const EDUCATION_FIELDS: [string, string, string?][] = [
  ["board_10", "Class 10th board / university (e.g. CBSE)"],
  ["qualification_year_10", "Year of passing (10th)", "number"], ["percentage_10", "Percentage of marks (10th)", "number"],
  ["qualification_year", "Year of passing (highest qualification)", "number"], ["percentage", "Percentage (highest qualification)", "number"],
  ["percentage_graduation", "Percentage of marks (graduation)", "number"],
];
const NUMERIC_KEYS = ["qualification_year", "percentage", "qualification_year_10", "percentage_10", "percentage_graduation"];
const QUALS = ["", "below_10th", "10th", "12th", "diploma", "graduate", "postgraduate", "doctorate"];

function ProfilePage() {
  const [p, setP] = useState<Profile>({});
  const [extra, setExtra] = useState<ExtraField[]>([]);
  const [newLabel, setNewLabel] = useState("");
  const [newType, setNewType] = useState<ExtraField["type"]>("text");
  const [newOptions, setNewOptions] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState<string | null>(null);
  useEffect(() => {
    api.get<Profile>("/profile").then((prof) => { setP(prof); setExtra((prof.extra_fields as ExtraField[]) ?? []); })
      .catch((e) => setError(e.message));
  }, []);

  function addField() {
    const label = newLabel.trim();
    const key = slug(label);
    if (label.length < 2 || !key) { setError("Give the new field a name first."); return; }
    if (extra.some((f) => f.key === key)) { setError("You already have a field with this name."); return; }
    const options = newType === "select" ? newOptions.split(",").map((s) => s.trim()).filter(Boolean) : [];
    if (newType === "select" && !options.length) { setError("Add at least one option for a dropdown field."); return; }
    setExtra([...extra, { key, label, type: newType, options, value: null }]);
    setNewLabel(""); setNewOptions(""); setError(null);
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null); setError(null);
    const body: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(p)) {
      if (k === "extra_fields" || v === "" || v === null || v === undefined) continue;
      body[k] = NUMERIC_KEYS.includes(k) ? Number(v) : v;
    }
    body.extra_fields = extra.map((f) => ({ ...f, value: f.type === "number" && f.value !== null && f.value !== "" ? Number(f.value) : (f.value ?? null) }));
    try { const saved = await api.put<Profile>("/profile", body); setP(saved); setExtra((saved.extra_fields as ExtraField[]) ?? []); setMsg("Saved"); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not save"); }
  }

  const MATTER = [["dob", "date of birth"], ["category", "category"], ["qualification", "qualification"], ["percentage", "percentage"], ["state", "state"], ["phone", "mobile number"]] as const;
  const filledMatter = MATTER.filter(([k]) => p[k] !== undefined && p[k] !== "" && p[k] !== null);
  const pct = Math.round((filledMatter.length / MATTER.length) * 100);
  return (
    <>
      <h1>Your profile</h1>
      <p className="muted">This is what the browser extension fills into forms. 🔒 Only you can see this. We do not store ID, passport or payment numbers — that is deliberate.</p>
      <Card title={`Profile ${pct}% complete for eligibility checks`}>
        <div className="bar" aria-label={`${pct}% complete`}><div style={{ width: `${pct}%` }} /></div>
        {filledMatter.length < MATTER.length
          ? <p className="small">Still needed: {MATTER.filter(([k]) => !filledMatter.some(([f]) => f === k)).map(([, l]) => l).join(", ")}. These decide age limits and marks checks.</p>
          : <p className="ok small">Everything the eligibility check needs is here.</p>}
      </Card>
      <Card>
        <form onSubmit={save}>
          <div className="grid">
            {TEXT_FIELDS.map(([k, label, type]) => (
              <div key={k}><label htmlFor={k}>{label}</label><input id={k} type={type ?? "text"} step={type === "number" ? "any" : undefined} value={(p[k] as string | number | undefined) ?? ""} onChange={(e) => setP({ ...p, [k]: e.target.value })} /></div>
            ))}
            <div><label htmlFor="gender">Gender</label>
              <select id="gender" value={(p.gender as string) ?? ""} onChange={(e) => setP({ ...p, gender: e.target.value })}>
                <option value="">Select</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option>
              </select></div>
            <div><label htmlFor="q">Highest qualification</label>
              <select id="q" value={(p.qualification as string) ?? ""} onChange={(e) => setP({ ...p, qualification: e.target.value })}>
                {QUALS.map((q) => <option key={q} value={q}>{q ? q.replace("_", " ") : "Select"}</option>)}
              </select></div>
          </div>

          <h3>Education details (SSC / government forms ask these separately)</h3>
          <div className="grid">
            {EDUCATION_FIELDS.map(([k, label, type]) => (
              <div key={k}><label htmlFor={k}>{label}</label><input id={k} type={type ?? "text"} step={type === "number" ? "any" : undefined} value={(p[k] as string | number | undefined) ?? ""} onChange={(e) => setP({ ...p, [k]: e.target.value })} /></div>
            ))}
          </div>

          <h3>Declarations (asked on most government forms)</h3>
          <p><label><input type="checkbox" style={{ width: "auto" }} checked={p.ex_serviceman === true} onChange={(e) => setP({ ...p, ex_serviceman: e.target.checked })} /> I am an ex-serviceman</label></p>
          <p><label><input type="checkbox" style={{ width: "auto" }} checked={p.pwd === true} onChange={(e) => setP({ ...p, pwd: e.target.checked })} /> I am a PwD (Divyangjan) candidate</label></p>
          <p><label><input type="checkbox" style={{ width: "auto" }} checked={Boolean(p.ex_servicemen_ward)} onChange={(e) => setP({ ...p, ex_servicemen_ward: e.target.checked })} /> I am a ward of an ex-serviceman</label></p>
          <p className="muted small">Unticked means "No" on Yes/No form questions. Exam centre, post preferences and roll / certificate numbers are chosen per application, so they are not stored here — the extension will never fill ID numbers.</p>

          {extra.length > 0 && <h3>Your extra fields</h3>}
          <div className="grid">
            {extra.map((f, i) => (
              <div key={f.key}>
                <label htmlFor={`extra-${f.key}`}>{f.label}</label>
                {f.type === "select" ? (
                  <select id={`extra-${f.key}`} value={(f.value as string) ?? ""} onChange={(e) => setExtra(extra.map((x, j) => j === i ? { ...x, value: e.target.value } : x))}>
                    <option value="">Select</option>{f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input id={`extra-${f.key}`} type={f.type} value={(f.value as string | number | undefined) ?? ""} onChange={(e) => setExtra(extra.map((x, j) => j === i ? { ...x, value: e.target.value } : x))} />
                )}
                <button type="button" className="secondary" onClick={() => setExtra(extra.filter((_, j) => j !== i))}>Remove</button>
              </div>
            ))}
          </div>

          <h3>Add your own field</h3>
          <p className="muted small">Forms ask for things we do not list (for example: blood group, mother tongue, university name). Add a field, fill it once, and the extension will offer it on matching forms — always for your confirmation. ID numbers, passport, bank and card details are not stored.</p>
          <div className="grid">
            <div><label htmlFor="new-label">Field name</label><input id="new-label" value={newLabel} onChange={(e) => setNewLabel(e.target.value)} placeholder="e.g. Blood group" maxLength={80} /></div>
            <div><label htmlFor="new-type">Type</label>
              <select id="new-type" value={newType} onChange={(e) => setNewType(e.target.value as ExtraField["type"])}>
                <option value="text">Text</option><option value="number">Number</option><option value="date">Date</option><option value="select">Dropdown (choices)</option>
              </select></div>
            {newType === "select" && <div><label htmlFor="new-options">Choices (comma separated)</label><input id="new-options" value={newOptions} onChange={(e) => setNewOptions(e.target.value)} placeholder="A+, A-, B+, O+" /></div>}
          </div>
          <p><button type="button" className="secondary" onClick={addField}>Add field</button> <span className="muted small">Then fill it above and press Save profile.</span></p>

          <ErrorText error={error} />
          {msg && <p className="ok">{msg}</p>}
          <button>Save profile</button>
        </form>
      </Card>
      <Card title="Use ApplyPilot on Telegram">
        <p className="muted">Create a code, then send <code>/link CODE</code> to the bot.</p>
        <button className="secondary" onClick={async () => setCode((await api.post<{ code: string }>("/bot/link-code")).code)}>Create link code</button>
        {code && <p>Your code: <strong>{code}</strong> <span className="muted small">(valid 10 minutes)</span></p>}
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><ProfilePage /></AuthGate>;
}
