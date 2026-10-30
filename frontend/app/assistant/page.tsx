"use client";
import { useEffect, useRef, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { NoticeListItem } from "@/lib/types";

type Turn = {
  q: string;
  answer: string;
  agent: string | null;
  blocked: boolean;
  tools: { tool: string; ok: boolean }[];
};
type ChatResponse = { answer: string; agent: string | null; blocked: boolean; tools_used: { tool: string; ok: boolean }[] };

const EXAMPLES = ["What deadlines are coming up this week?", "Am I eligible for this post?", "What photo size do I need?", "Is this notice safe?"];

function Assistant() {
  const [notices, setNotices] = useState<NoticeListItem[]>([]);
  const [noticeId, setNoticeId] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { api.get<NoticeListItem[]>("/notices").then(setNotices).catch(() => {}); }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [turns]);

  async function send(message: string) {
    const q = message.trim();
    if (!q) return;
    setBusy(true);
    setError(null);
    setText("");
    try {
      const r = await api.post<ChatResponse>("/assistant/chat", { message: q, notice_id: noticeId ? Number(noticeId) : null });
      setTurns((t) => [...t, { q, answer: r.answer, agent: r.agent, blocked: r.blocked, tools: r.tools_used }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The assistant is not available");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Assistant</h1>
      <p className="muted">Ask about your notices, eligibility, documents, photo rules and deadlines. It only sees your own data.</p>
      <Card>
        <label htmlFor="n">Notice to talk about (optional)</label>
        <select id="n" value={noticeId} onChange={(e) => setNoticeId(e.target.value)}>
          <option value="">Any (I will ask if needed)</option>
          {notices.map((n) => <option key={n.id} value={n.id}>#{n.id} {n.title.slice(0, 50)}</option>)}
        </select>
        <div className="chat">
          {turns.length === 0 && <p className="muted small">Try: {EXAMPLES.map((e) => <button key={e} className="secondary" style={{ margin: 4 }} onClick={() => send(e)}>{e}</button>)}</p>}
          {turns.map((t, i) => (
            <div key={i}>
              <div className="msg me">{t.q}</div>
              <div className="msg">{t.answer}</div>
              <p className="muted small">
                {t.blocked ? <Badge tone="warn">blocked by guardrails</Badge> : t.agent && <Badge tone="info">{t.agent.replace("_", " ")}</Badge>}{" "}
                {t.tools.map((x, j) => <Badge key={j} tone={x.ok ? "good" : "bad"}>{x.tool}</Badge>)}
              </p>
            </div>
          ))}
          <div ref={end} />
        </div>
        <ErrorText error={error} />
        <form className="row" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <div><label htmlFor="m">Your message</label><input id="m" value={text} maxLength={500} onChange={(e) => setText(e.target.value)} placeholder="Ask anything about your applications" /></div>
          <button disabled={busy || !text.trim()}>{busy ? "..." : "Send"}</button>
        </form>
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Assistant /></AuthGate>;
}
