"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, Empty, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { IngestJob, Notice, NoticeListItem } from "@/lib/types";

function Notices() {
  const router = useRouter();
  const [list, setList] = useState<NoticeListItem[]>([]);
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

  return (
    <>
      <h1>Notices</h1>
      <Card title="Add a notice">
        <form onSubmit={add}>
          <p><label htmlFor="f">Upload PDF, image or text file</label><input id="f" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></p>
          <p className="muted small">or paste the notice text</p>
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the notification text here" aria-label="Notice text" />
          <ErrorText error={error} />
          <p><button disabled={busy || (!file && !text.trim())}>{busy ? "Reading notice..." : "Read this notice"}</button></p>
          {job && (
            <p className="muted" role="status">
              Background ingest: {job.status}
              {job.status === "ready" && job.notice_id ? <> — <Link href={`/notices/${job.notice_id}`}>{job.title ?? "open notice"}</Link> {job.summary.join(" · ")}</> : null}
              {job.status === "failed" ? ` — ${job.error}` : ""}
            </p>
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
        {list.length === 0 ? <Empty>No notices yet.</Empty> : (
          <table>
            <thead><tr><th>Title</th><th>Last date</th><th>Safety</th></tr></thead>
            <tbody>
              {list.map((n) => (
                <tr key={n.id}>
                  <td><Link href={`/notices/${n.id}`}>{n.title.slice(0, 80)}</Link></td>
                  <td>{n.last_date ?? "not found"}</td>
                  <td><Badge tone={n.scam_level === "high" ? "bad" : n.scam_level === "medium" ? "warn" : "good"}>{n.scam_level ?? "-"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Notices /></AuthGate>;
}
