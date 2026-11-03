"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, Empty, Skeleton, StatusChip, daysChip, fmtDate } from "@/components/ui";
import { api, auth } from "@/lib/api";
import type { Application, NoticeListItem, Summary } from "@/lib/types";

const fmtSaved = (min: number) => (min >= 60 ? `${Math.floor(min / 60)}h ${min % 60}m` : `${min}m`);

function Landing() {
  return (
    <main className="container hero">
      <p><strong className="brand" style={{ fontSize: 22 }}>ApplyPilot</strong> <Link href="/login" style={{ float: "right" }}>Log in</Link></p>
      <h1>Stop losing chances to paperwork.</h1>
      <p style={{ fontSize: 18, maxWidth: 640 }}>ApplyPilot reads job and exam notices, tells you if you can apply, fixes your photo and signature, and fills the form. Right in Telegram, WhatsApp or your browser.</p>
      <p>
        <Link className="btn" href="/login">Get started free</Link>{" "}
        <a className="btn" href="#how" style={{ background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line)" }}>See how it works</a>
      </p>
      <p className="muted small">Free and open source. Your files are encrypted. We never submit a form for you.</p>

      <div className="grid" style={{ marginTop: 28 }}>
        <Card title="A 40-page notice nobody reads"><p className="muted">We read it once and answer with the page for every fact.</p></Card>
        <Card title="A photo rejected by 2 KB"><p className="muted">The studio makes the exact pixels, KB and background the portal asks for.</p></Card>
        <Card title="The same form, typed again and again"><p className="muted">Your profile fills it in one click. You review, you submit.</p></Card>
      </div>

      <Card title="How it works">
        <ol id="how">
          <li><strong>Send the notice</strong> — PDF, photo, or paste the text.</li>
          <li><strong>Check your eligibility</strong> — with the reason and the page for each rule.</li>
          <li><strong>Fix your photo and signature</strong> — to the notice&apos;s exact rules.</li>
          <li><strong>Fill the form</strong> — with the extension. You press submit.</li>
        </ol>
      </Card>

      <div className="grid">
        <Card title="Use it where you are">
          <ul className="plain">
            <li><strong>Website</strong> — everything, on phone or computer.</li>
            <li><strong>Telegram &amp; WhatsApp</strong> — send a PDF, ask questions, get reminders.</li>
            <li><strong>Browser extension</strong> — fills forms and attaches your vault files.</li>
          </ul>
        </Card>
        <Card title="Safety and privacy">
          <ul className="plain">
            <li>Only you can see your files. They are encrypted.</li>
            <li>We never submit your form. We never ask for ID numbers.</li>
            <li>Every answer shows its page. Check the official notice.</li>
          </ul>
        </Card>
      </div>
      <Card title="Questions">
        <ul className="plain">
          <li><strong>Is it free?</strong> Yes, and open source.</li>
          <li><strong>Does it submit forms?</strong> Never. You always press submit.</li>
          <li><strong>Which model do you use?</strong> Meta&apos;s Muse Spark for reading and answers; a local Llama embedding model for search. Your documents stay yours.</li>
        </ul>
        <p><Link className="btn" href="/login">Get started free</Link></p>
      </Card>
    </main>
  );
}

type SetupState = { basics: boolean; notice: boolean; photo: boolean; chat: boolean };

function Dashboard() {
  const [apps, setApps] = useState<Application[]>([]);
  const [notices, setNotices] = useState<NoticeListItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [setup, setSetup] = useState<SetupState | null>(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      api.get<Application[]>("/applications").then(setApps),
      api.get<NoticeListItem[]>("/notices").then(setNotices),
      api.get<Summary>("/applications/summary").then(setSummary),
      api.get<Record<string, unknown>>("/profile").then((p) => {
        setName(String(p.full_name ?? "").split(" ")[0]);
        setSetup((s) => ({ ...(s ?? { basics: false, notice: false, photo: false, chat: false }), basics: Boolean(p.dob && p.qualification) }));
      }),
      api.get<{ kind: string; is_original: boolean }[]>("/documents").then((docs) =>
        setSetup((s) => ({ ...(s ?? { basics: false, notice: false, photo: false, chat: false }), photo: docs.some((d) => !d.is_original) }))),
      api.get<{ linked?: boolean }>("/bot/status").then((r) => setSetup((s) => ({ ...(s ?? { basics: false, notice: false, photo: false, chat: false }), chat: Boolean(r.linked) }))).catch(() =>
        setSetup((s) => ({ ...(s ?? { basics: false, notice: false, photo: false, chat: false }), chat: false }))),
    ]).finally(() => setLoading(false));
  }, []);
  useEffect(() => { setSetup((s) => (s ? { ...s, notice: notices.length > 0 } : s)); }, [notices.length]);

  const open = apps.filter((a) => ["planned", "in_progress"].includes(a.status));
  const next = [...open].sort((a, b) => (a.days_left ?? 9999) - (b.days_left ?? 9999))[0];
  const steps: [keyof SetupState, string, string, string][] = [
    ["basics", "Add your basics", "1 min — we need your date of birth and qualification to check if you can apply.", "/profile"],
    ["notice", "Add your first notice", "1 min — upload a notice PDF or paste its text. We read it for you.", "/notices"],
    ["photo", "Fix your photo and signature", "2 min — get files that match the portal's rules.", "/photo"],
    ["chat", "Connect Telegram or WhatsApp", "1 min — ask questions and get reminders in your chat app.", "/chat-apps"],
  ];
  const doneCount = setup ? steps.filter(([k]) => setup[k]).length : 0;

  return (
    <>
      <h1>{name ? `Hi ${name}` : "Your applications"}</h1>
      {loading ? <Skeleton lines={4} /> : (
        <>
          {setup && doneCount < steps.length ? (
            <Card title={`Setup: ${doneCount} of ${steps.length} done`} action={<span className="muted small">About {5 - doneCount} min left</span>}>
              <ol className="checklist">
                {steps.map(([key, title, why, href], i) => (
                  <li key={key} className={setup[key] ? "done" : ""}>
                    <span className="n" aria-hidden="true">{setup[key] ? "✓" : i + 1}</span>
                    <span style={{ flex: 1 }}><strong>{title}</strong><br /><span className="muted small">{why}</span></span>
                    {!setup[key] && <Link className="btn" href={href}>Start</Link>}
                  </li>
                ))}
              </ol>
              <p className="muted small">You can skip any step and come back. Nothing is submitted for you, ever.</p>
            </Card>
          ) : setup ? <p><Badge tone="good">Setup complete</Badge> <span className="muted small">Nice — everything below is ready when you are.</span></p> : null}

          {next ? (
            <Card title="Next deadline">
              <p style={{ fontSize: 19 }}><strong>{next.title.slice(0, 70)}</strong> {daysChip(next.days_left)} <StatusChip status={next.status} /></p>
              <p className="muted">Last date {fmtDate(next.deadline)}</p>
              <p>{next.notice_id ? <Link className="btn" href={`/notices/${next.notice_id}`}>Open notice</Link> : <Link className="btn" href="/tracker">Open tracker</Link>}</p>
            </Card>
          ) : (
            <Card title="Add your first notice">
              <p className="muted">Upload a notice PDF or paste its text. We read it and tell you if you can apply — usually in under a minute.</p>
              <p><Link className="btn" href="/notices">Add a notice</Link> <span className="muted small">No notice handy? Add one from Notices, then ask the assistant about it.</span></p>
            </Card>
          )}

          <Card title="Quick actions">
            <div className="grid2">
              <Link className="btn" href="/notices">＋ Add a notice</Link>
              <Link className="btn" href="/assistant">✦ Ask the assistant</Link>
              <Link className="btn" href="/photo">▣ Fix a photo</Link>
              <Link className="btn" href="/vault">▦ Open vault</Link>
            </div>
            {summary && <p className="muted small" style={{ marginTop: 12 }}>{summary.open} open · {summary.submitted} submitted · {summary.notices} notices read · {summary.documents_ready} documents ready · time saved about {fmtSaved(summary.time_saved_minutes)}</p>}
          </Card>

          <div className="grid">
            <Card title="My applications" action={<Link href="/tracker">Tracker</Link>}>
              {open.length === 0 ? <Empty>No open applications yet. Add a notice to start.</Empty> : (
                <ul className="plain">{open.slice(0, 5).map((a) => (
                  <li key={a.id}>{a.title.slice(0, 55)} <span className="muted small">{fmtDate(a.deadline)}</span> {daysChip(a.days_left)} <StatusChip status={a.status} /></li>
                ))}</ul>
              )}
            </Card>
            <Card title="Recent notices" action={<Link href="/notices">All notices</Link>}>
              {notices.length === 0 ? <Empty>Nothing yet. Your read notices will appear here.</Empty> : (
                <ul className="plain">{notices.slice(0, 5).map((n) => (
                  <li key={n.id}><Link href={`/notices/${n.id}`}>{n.title.slice(0, 70)}</Link> <span className="muted small">last date {fmtDate(n.last_date)}</span></li>
                ))}</ul>
              )}
            </Card>
          </div>

          {setup && !setup.chat && (
            <Card title="Get reminders where you already are">
              <p className="muted">Connect Telegram or WhatsApp: send a notice PDF in chat, ask questions, and get a reminder 3 days before a deadline.</p>
              <p><Link className="btn" href="/chat-apps">Connect a chat app</Link></p>
            </Card>
          )}
        </>
      )}
    </>
  );
}

export default function Page() {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  useEffect(() => { setSignedIn(Boolean(auth.get())); }, []);
  if (signedIn === null) return null;
  if (!signedIn) return <Landing />;
  return <AuthGate><Dashboard /></AuthGate>;
}
