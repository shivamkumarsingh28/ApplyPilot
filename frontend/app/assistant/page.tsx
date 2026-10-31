"use client";
import { useEffect, useRef, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { NoticeListItem } from "@/lib/types";

type Turn = { role: "me" | "bot"; text: string; agent?: string | null; blocked?: boolean; tools?: { tool: string; ok: boolean }[]; ts: string };
type ChatResponse = { answer: string; agent: string | null; blocked: boolean; tools_used: { tool: string; ok: boolean }[] };

const EXAMPLES = [
  "What deadlines are coming up this week?",
  "Am I eligible for this post?",
  "What is the last date?",
  "What photo size do I need?",
  "What is the application fee?",
  "Is this notice safe?",
  "Which documents do I need?",
];

const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function Assistant() {
  const [notices, setNotices] = useState<NoticeListItem[]>([]);
  const [noticeId, setNoticeId] = useState("");
  const [turns, setTurns] = useState<Turn[]>([
    { role: "bot", text: "Hi! I can answer from your notices, check eligibility, deadlines, documents and photo rules. Pick a notice (optional), then ask me anything.", ts: now() },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { api.get<NoticeListItem[]>("/notices").then(setNotices).catch(() => {}); }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, busy]);

  async function send(message: string) {
    const q = message.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    setText("");
    setTurns((t) => [...t, { role: "me", text: q, ts: now() }]);
    try {
      const r = await api.post<ChatResponse>("/assistant/chat", { message: q, notice_id: noticeId ? Number(noticeId) : null });
      setTurns((t) => [...t, { role: "bot", text: r.answer, agent: r.agent, blocked: r.blocked, tools: r.tools_used, ts: now() }]);
    } catch (err) {
      setTurns((t) => [...t, { role: "bot", text: "Sorry, I could not reach the assistant. Check your connection and try again.", ts: now() }]);
      setError(err instanceof Error ? err.message : "The assistant is not available");
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  return (
    <>
      <h1>Assistant</h1>
      <p className="muted">Your ApplyPilot chatbot — answers only from your own notices and profile. Try Telegram/WhatsApp too: send a notice PDF to the bot and ask the same questions there.</p>
      <Card>
        <div className="chat-shell">
          <label htmlFor="n">Notice to talk about (optional)</label>
          <select id="n" value={noticeId} onChange={(e) => setNoticeId(e.target.value)}>
            <option value="">Any notice (I will ask if needed)</option>
            {notices.map((n) => <option key={n.id} value={n.id}>#{n.id} {n.title.slice(0, 60)}</option>)}
          </select>

          <div className="chips" aria-label="Suggested questions">
            {EXAMPLES.map((e) => <button key={e} type="button" className="chip" disabled={busy} onClick={() => send(e)}>{e}</button>)}
          </div>

          <div className="chat" aria-live="polite">
            {turns.map((t, i) => (
              <div key={i} className={`chat-row ${t.role === "me" ? "me" : ""}`}>
                {t.role === "bot" && <div className="avatar" aria-hidden="true">{"\u2726"}</div>}
                <div>
                  <div className={`msg ${t.role}`}>{t.text}</div>
                  <div className="msg-meta">
                    <span className="muted small">{t.ts}</span>
                    {t.blocked ? <Badge tone="warn">blocked by guardrails</Badge> : t.agent ? <Badge tone="info">{t.agent.replace(/_/g, " ")}</Badge> : null}
                    {(t.tools ?? []).map((x, j) => <Badge key={j} tone={x.ok ? "good" : "bad"}>{x.tool}</Badge>)}
                    {t.role === "bot" && i > 0 && (
                      <button type="button" className="link small" onClick={() => navigator.clipboard?.writeText(t.text)}>Copy</button>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {busy && (
              <div className="chat-row">
                <div className="avatar" aria-hidden="true">{"\u2726"}</div>
                <div className="msg bot typing" aria-label="Assistant is typing"><i /><i /><i /></div>
              </div>
            )}
            <div ref={end} />
          </div>

          <ErrorText error={error} />
          <form className="composer" onSubmit={(e) => { e.preventDefault(); send(text); }}>
            <div>
              <label htmlFor="m">Your message</label>
              <input
                ref={inputRef}
                id="m"
                value={text}
                maxLength={500}
                onChange={(e) => setText(e.target.value)}
                placeholder="Ask about dates, fees, eligibility, documents..."
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); } }}
              />
            </div>
            <button type="button" className="secondary" disabled={!turns.some((t) => t.role === "me") || busy} onClick={() => setTurns(turns.slice(0, 1))}>Clear</button>
            <button disabled={busy || !text.trim()}>{busy ? "Thinking..." : "Send \u27A4"}</button>
          </form>
          <p className="muted small">Enter sends. Answers cite the notice — always confirm dates and fees on the official portal.</p>
        </div>
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Assistant /></AuthGate>;
}
