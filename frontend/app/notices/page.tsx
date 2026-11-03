"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, Empty, ErrorText, fmtDate } from "@/components/ui";
import { api } from "@/lib/api";
import type { IngestJob, Notice, NoticeListItem } from "@/lib/types";

const JOB_STEPS = ["Reading", "Checking safety", "Finding key facts", "Ready"];

function Notices() {
  const router = useRouter();
  const [list, setList] = useState<NoticeListItem[]>([]);
  const [tab, setTab] = useState<"file" | "text">("file");
  const [filter, setFilter] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<IngestJob | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<{ title: string; url: string; snippet: string }[]>([]);

  const load = () => api.get<NoticeListItem[]>("/notices").then(setList).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (!job || ["ready", "failed"].includes(job.status)) {
      if (job?.status === "ready") load();
      return;
    }
    const t = setInterval(async () => {
      try { setJob(await api.get<IngestJob>(`/jobs/${job.id}`)); } catch {}
    }, 1500);
    return () => clearInterval(t);
  }, [job?.id, job?.status]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (file && !text.trim()) {
        const form = new FormData();
        form.append("file", file);
        const j = await api.upload<{ job_id: number }>("/jobs/ingest", form);
        setJob({ id: j.job_id, status: "queued", notice_id: null, error: "", source: "web", timings: {}, summary: [], title: null });
      } else {
        const form = new FormData();
        if (file) form.append("file", file);
        if (text.trim()) form.append("text", text);
        const n = await api.upload<Notice>("/notices", form);
        router.push(`/notices/${n.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function doSearch(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const q = query.trim();
    if (/^https?:\/\/\S+$/i.test(q)) {
      // A pasted link is not a search — save it as a notice directly.
      saveResult(q);
      setQuery("");
      return;
    }
    try {
      const r = await api.get<{ results: { title: string; url: string; snippet: string }[] }>(`/search?q=${encodeURIComponent(q)}`);
      setResults(r.results);
    } catch (err) { setError(err instanceof Error ? err.message : "Search failed"); }
  }

  async function saveResult(url: string) {
    try {
      const j = await api.post<{ job_id: number }>("/search/save", { url });
      setJob({ id: j.job_id, status: "queued", notice_id: null, error: "", source: "search", timings: {}, summary: [], title: null });
    } catch (err) { setError(err instanceof Error ? err.message : "Could not save that result"); }
  }

  const visible = list.filter((n) => !filter || n.title.toLowerCase().includes(filter.toLowerCase()));
  const stepIdx = job ? (job.status === "ready" ? 3 : job.status === "indexing" ? 2 : job.status === "reading" ? 0 : 0) : -1;
  return (
    <>
      <h1>Notices</h1>
      <p className="muted">One notice is read once and shared with everyone who uploads the same one. Only public notices here — personal documents belong in your <Link href="/vault">Vault</Link>.</p>
      <Card title="Add a notice">
        <div className="tabs" role="tablist" aria-label="Add a notice">
          <button type="button" className={tab === "file" ? "active" : ""} onClick={() => setTab("file")}>Upload file</button>
          <button type="button" className={tab === "text" ? "active" : ""} onClick={() => setTab("text")}>Paste text</button>
        </div>
        <form onSubmit={add}>
          {tab === "file" ? (
            <div className="dropzone">
              <label htmlFor="f">Drop a PDF, photo or text file, or choose one</label>
              <input id="f" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              <p className="muted small">PDF, photo or text, up to 15 MB. On a phone you can take a photo of the notice. If this notice is already read, you get it instantly.</p>
              {file && <p className="small">{file.name} · {(file.size / 1024).toFixed(0)} KB</p>}
            </div>
          ) : (
            <p><label htmlFor="paste">Notice text</label><textarea id="paste" value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the notification text here" /></p>
          )}
          <ErrorText error={error} />
          <p><button disabled={busy || (tab === "file" ? !file : !text.trim())}>{busy ? "Reading…" : "Read this notice"}</button>
            <span className="muted small"> Usually under a minute. You can leave this page — it keeps working.</span></p>
          {job && (
            <div role="status">
              <p className="progress">{job.status === "failed" ? `Could not read it: ${job.error}. Try a clearer photo or paste the text.` : (
                JOB_STEPS.map((s, i) => <span key={s}>{i > 0 ? " → " : ""}<strong style={{ color: i <= stepIdx ? "var(--primary)" : undefined }}>{s}</strong></span>)
              )}</p>
              {job.status === "ready" && job.notice_id ? <p><Link className="btn" href={`/notices/${job.notice_id}`}>Open: {job.title ?? "your notice"}</Link> <span className="muted small">{job.summary.join(" · ")}</span></p> : null}
            </div>
          )}
        </form>
      </Card>
      <Card title="Search the web for notices">
        <form className="row" onSubmit={doSearch}>
          <div><label htmlFor="q">Search the web, or paste a notice link to save it directly</label><input id="q" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="SSC recruitment 2026 — or paste https://… notice link" /></div>
          <button disabled={query.trim().length < 3}>{/^https?:\/\//i.test(query.trim()) ? "Save link as notice" : "Search"}</button>
        </form>
        {results.map((r) => (
          <p key={r.url}><a href={r.url} target="_blank" rel="noreferrer">{r.title || r.url}</a><br /><span className="muted small">{r.snippet}</span>{" "}
            <button type="button" className="secondary" onClick={() => saveResult(r.url)}>Save as notice</button></p>
        ))}
      </Card>
      <Card title="Saved notices">
        <p><label htmlFor="find">Search your notices</label><input id="find" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Title words…" /></p>
        {list.length === 0 ? (
          <Empty action={<Link className="btn" href="/assistant">Ask the assistant what to do first</Link>}>
            Nothing here yet. Upload your first notice above — we read it and show who can apply, the last date, and whether it looks safe.
          </Empty>
        ) : visible.length === 0 ? <Empty>No notice matches “{filter}”.</Empty> : (
          <ul className="plain">
            {visible.map((n) => (
              <li key={n.id}>
                <Link href={`/notices/${n.id}`}>{n.title.slice(0, 80)}</Link>
                <div>
                  <Badge tone={n.scam_level === "high" ? "bad" : n.scam_level === "medium" ? "warn" : "good"}>{n.scam_level === "high" ? "High risk" : n.scam_level === "medium" ? "Check carefully" : "Safe"}</Badge>
                  <span className="muted small">last date {fmtDate(n.last_date)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Notices /></AuthGate>;
}
