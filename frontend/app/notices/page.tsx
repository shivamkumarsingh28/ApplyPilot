"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, Empty, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { Notice, NoticeListItem } from "@/lib/types";

function Notices() {
  const router = useRouter();
  const [list, setList] = useState<NoticeListItem[]>([]);
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.get<NoticeListItem[]>("/notices").then(setList).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const form = new FormData();
    if (file) form.append("file", file);
    if (text.trim()) form.append("text", text);
    try {
      const n = await api.upload<Notice>("/notices", form);
      router.push(`/notices/${n.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
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
        </form>
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
