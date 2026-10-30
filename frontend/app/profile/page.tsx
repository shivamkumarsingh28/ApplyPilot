"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { Profile } from "@/lib/types";

const TEXT_FIELDS: [string, string, string?][] = [
  ["full_name", "Full name"], ["father_name", "Father's name"], ["mother_name", "Mother's name"], ["dob", "Date of birth", "date"],
  ["email", "Email", "email"], ["phone", "Mobile number", "tel"], ["address_line", "Address"], ["city", "City"],
  ["state", "State"], ["pincode", "PIN / postal code"], ["nationality", "Nationality"], ["category", "Category (general, obc, sc, st, ews)"],
  ["qualification_year", "Year of passing", "number"], ["percentage", "Percentage", "number"],
];
const QUALS = ["", "below_10th", "10th", "12th", "diploma", "graduate", "postgraduate", "doctorate"];

function ProfilePage() {
  const [p, setP] = useState<Profile>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [code, setCode] = useState<string | null>(null);
  useEffect(() => { api.get<Profile>("/profile").then(setP).catch((e) => setError(e.message)); }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null); setError(null);
    const body: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(p)) {
      if (v === "" || v === null || v === undefined) continue;
      body[k] = ["qualification_year", "percentage"].includes(k) ? Number(v) : v;
    }
    try { setP(await api.put<Profile>("/profile", body)); setMsg("Saved"); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not save"); }
  }

  return (
    <>
      <h1>Your profile</h1>
      <p className="muted">This is what the browser extension fills into forms. We do not store ID, passport or payment numbers.</p>
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
          <p><label><input type="checkbox" style={{ width: "auto" }} checked={Boolean(p.ex_servicemen_ward)} onChange={(e) => setP({ ...p, ex_servicemen_ward: e.target.checked })} /> I am a ward of an ex-serviceman</label></p>
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
