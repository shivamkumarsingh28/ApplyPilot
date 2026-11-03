"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, ErrorText, Spinner } from "@/components/ui";
import { api } from "@/lib/api";

function ChatApps() {
  const [linked, setLinked] = useState<boolean | null>(null);
  const [code, setCode] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(600);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = () => api.get<{ linked: boolean }>("/bot/status").then((r) => setLinked(r.linked)).catch(() => setLinked(false));
  useEffect(() => { loadStatus(); }, []);
  useEffect(() => {
    if (!code || linked) return;
    const poll = setInterval(loadStatus, 5000);
    const tick = setInterval(() => setSeconds((s) => Math.max(0, s - 1)), 1000);
    return () => { clearInterval(poll); clearInterval(tick); };
  }, [code, linked]);

  async function makeCode() {
    setError(null);
    try {
      const r = await api.post<{ code: string }>("/bot/link-code");
      setCode(r.code); setSeconds(600); setCopied(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not create a code"); }
  }

  const mm = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

  return (
    <>
      <h1>Chat apps</h1>
      <p className="muted">Ask questions and get deadline reminders where you already chat. Connecting takes about a minute.</p>
      <div className="grid">
        <Card title="Telegram">
          <p>{linked === null ? <Spinner label="Checking…" /> : linked ? <Badge tone="good">✓ Connected</Badge> : <Badge tone="info">Not connected</Badge>}</p>
          {linked ? (
            <>
              <p className="ok">Connected. Send a notice PDF to the bot to try it.</p>
              <ul className="plain">
                <li>Send a PDF — I read it.</li>
                <li>Ask any question about it.</li>
                <li>Send a photo with the caption “photo” — I fix it to the rules.</li>
                <li>Type /deadlines for what is due soon.</li>
                <li>You get a reminder 3 days before a deadline.</li>
              </ul>
              <p><button type="button" className="danger" onClick={async () => { await api.post("/bot/unlink", {}); setLinked(false); setCode(null); }}>Disconnect</button></p>
            </>
          ) : (
            <>
              <ol>
                <li>Open your ApplyPilot Telegram bot and press <strong>Start</strong>.</li>
                <li>Send it the message below (Copy makes it one tap):</li>
              </ol>
              {code ? (
                <>
                  <p style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <code style={{ fontSize: 17, background: "var(--card2)", padding: "10px 14px", borderRadius: 8 }}>/link {code}</code>
                    <button type="button" className="secondary" onClick={async () => { await navigator.clipboard?.writeText(`/link ${code}`); setCopied(true); }}>{copied ? "Copied ✓" : "Copy"}</button>
                  </p>
                  <p className="muted small">Code expires in {mm}. This page updates by itself when you connect.</p>
                </>
              ) : (
                <p><button type="button" onClick={makeCode}>Create my link code</button></p>
              )}
            </>
          )}
          <ErrorText error={error} />
        </Card>

        <Card title="WhatsApp">
          <p><Badge tone="warn">Experimental</Badge></p>
          <p className="muted">The same assistant works on WhatsApp once a WhatsApp Business number is connected by the admin. Until then, Telegram and the website have everything.</p>
          <ul className="plain">
            <li>Send a PDF — I read it.</li>
            <li>Ask any question about it.</li>
            <li>Type /deadlines for what is due soon.</li>
          </ul>
        </Card>
      </div>

      <Card title="Stay safe in chat">
        <p className="muted">Chat apps are not end-to-end private for bots. Never send passwords, OTPs or ID numbers in chat. ApplyPilot never asks for them.</p>
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><ChatApps /></AuthGate>;
}
