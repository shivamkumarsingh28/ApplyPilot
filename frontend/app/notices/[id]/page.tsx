"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { Answer, Eligibility, Notice, Readiness } from "@/lib/types";

const VERDICT = {
  eligible: ["good", "You look eligible"],
  not_eligible: ["bad", "You may not be eligible"],
  needs_info: ["warn", "Add details to check eligibility"],
} as const;

function NoticeDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [notice, setNotice] = useState<Notice | null>(null);
  const [elig, setElig] = useState<Eligibility | null>(null);
  const [ready, setReady] = useState<Readiness | null>(null);
  const [chat, setChat] = useState<{ q: string; a: Answer }[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Notice>(`/notices/${id}`).then(setNotice).catch((e) => setError(e.message));
    api.get<Eligibility>(`/notices/${id}/eligibility`).then(setElig).catch(() => {});
    api.get<Readiness>(`/notices/${id}/readiness`).then(setReady).catch(() => {});
  }, [id]);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setBusy(true);
    setQuestion("");
    try {
      const a = await api.post<Answer>(`/notices/${id}/ask`, { question: q });
      setChat((c) => [...c, { q, a }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not answer");
    } finally {
      setBusy(false);
    }
  }

  if (!notice) return <ErrorText error={error} />;
  const s = notice.structured;
  const scam = notice.scam_report;
  return (
    <>
      <h1>{notice.title}</h1>
      {notice.shared && <p className="muted small">Shared notice — already processed once, so you got it instantly.</p>}
      {notice.apply_link ? (
        <p><a className="btn" href={notice.apply_link} target="_blank" rel="noopener noreferrer">Apply on the official website</a>{" "}
          <span className="muted small">{notice.apply_link}</span></p>
      ) : (
        <p className="muted small">No official apply link was found in this notice.</p>
      )}
      <ErrorText error={error} />
      <div className="grid">
        <Card title="Key facts">
          <table><tbody>
            {s.doc_type && <tr><th>Type</th><td>{(s.kind ?? s.doc_type).replace(/_/g, " ")}</td></tr>}
            {s.start_date && <tr><th>Start date</th><td>{s.start_date}</td></tr>}
            {s.vacancies ? <tr><th>Vacancies</th><td>{s.vacancies}</td></tr> : null}
            {s.salary?.amount ? <tr><th>Salary</th><td>{s.salary.currency} {s.salary.amount}</td></tr> : null}
            <tr><th>Last date</th><td>{s.last_date ?? "Not found"}</td></tr>
            <tr><th>Age</th><td>{s.age.min ?? "?"} to {s.age.max ?? "?"} years{s.age.as_of ? ` (as on ${s.age.as_of})` : ""}</td></tr>
            <tr><th>Relaxation</th><td>{Object.entries(s.age.relaxations).map(([k, v]) => `${k.toUpperCase()} +${v}`).join(", ") || "None found"}</td></tr>
            <tr><th>Qualification</th><td>{s.qualification.level ?? "Not found"}{s.qualification.min_percentage ? `, min ${s.qualification.min_percentage}%` : ""}</td></tr>
            <tr><th>Fee</th><td>{s.fee ? `${s.fee.currency} ${s.fee.amount}` : "Not found"}</td></tr>
            <tr><th>Stages</th><td>{s.selection_stages.join(" > ") || "Not found"}</td></tr>
          </tbody></table>
          {s.needs_review.length > 0 && <p className="muted small">Check these against the original: {s.needs_review.map((r) => r.field).join(", ")}</p>}
          <p className="muted small">Read by: {s.method}. Always confirm with the official notice.</p>
        </Card>

        <Card title="Is this notice safe?">
          <p><Badge tone={scam.level === "high" ? "bad" : scam.level === "medium" ? "warn" : "good"}>{scam.level} risk</Badge> <span className="muted small">score {scam.score}/100</span></p>
          {scam.reasons.length ? <ul>{scam.reasons.map((r) => <li key={r}>{r}</li>)}</ul> : <p className="muted">No warning signs found.</p>}
          <p className="muted small">{scam.disclaimer}</p>
        </Card>
      </div>

      <div className="grid">
        <Card title="Am I eligible?">
          {!elig ? <p className="muted">Loading...</p> : (
            <>
              <p><Badge tone={VERDICT[elig.verdict][0]}>{VERDICT[elig.verdict][1]}</Badge></p>
              <ul className="plain">
                {elig.checks.map((c) => (
                  <li key={c.rule}><strong>{c.rule}</strong> <Badge tone={c.status === "pass" ? "good" : c.status === "fail" ? "bad" : "warn"}>{c.status}</Badge><br /><span className="muted small">{c.detail}</span></li>
                ))}
              </ul>
              {elig.missing_profile_fields.length > 0 && <p><Link href="/profile">Complete your profile</Link> ({elig.missing_profile_fields.join(", ")})</p>}
              <p className="muted small">{elig.disclaimer}</p>
            </>
          )}
        </Card>

        <Card title="Ready to apply?">
          {!ready ? <p className="muted">Loading...</p> : (
            <>
              <div className="bar" aria-label={`${ready.percent}% ready`}><div style={{ width: `${ready.percent}%` }} /></div>
              <p>{ready.percent}% of documents ready{ready.days_left !== null ? `, ${ready.days_left} days left` : ""}</p>
              {ready.missing.length > 0 && <><strong>Missing</strong><ul>{ready.missing.map((m) => <li key={m.kind}>{m.label}</li>)}</ul></>}
              <p>
                <Link className="btn" href={`/photo?notice=${notice.id}`}>Fix photo and signature</Link>{" "}
                <Link href="/vault">Open vault</Link>
              </p>
            </>
          )}
        </Card>
      </div>

      <Card title="Before you apply">
        <p>
          <button onClick={async () => { const blob = await api.blob(`/notices/${notice.id}/checklist`); window.open(URL.createObjectURL(blob), "_blank"); }}>Print checklist</button>{" "}
          <span className="muted small">One page with key facts, eligibility, ready/missing documents and submission-day steps. Print it or save as PDF.</span>
        </p>
      </Card>

      <Card title="Ask this notice">
        <div className="chat">
          {chat.map((m, i) => (
            <div key={i}>
              <div className="msg me">{m.q}</div>
              <div className="msg">{m.a.answer}</div>
              {m.a.citations.length > 0 && <p className="muted small">From page{m.a.citations.length > 1 ? "s" : ""} {[...new Set(m.a.citations.map((c) => c.page))].join(", ")}</p>}
            </div>
          ))}
        </div>
        <form className="row" onSubmit={ask}>
          <div><label htmlFor="q">Your question</label><input id="q" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Is there a physical test? What is the fee?" /></div>
          <button disabled={busy || !question.trim()}>{busy ? "..." : "Ask"}</button>
        </form>
      </Card>
      <p><button className="danger" onClick={async () => { await api.del(`/notices/${id}`); router.push("/notices"); }}>Delete notice</button></p>
    </>
  );
}

export default function Page() {
  return <AuthGate><NoticeDetail /></AuthGate>;
}
