"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, Empty, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { Application } from "@/lib/types";

const STATUSES = ["planned", "in_progress", "submitted", "closed"];

function Tracker() {
  const [rows, setRows] = useState<Application[]>([]);
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = () => api.get<Application[]>("/applications").then(setRows).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    try { await api.post("/applications", { title, deadline: deadline || null }); setTitle(""); setDeadline(""); load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not add"); }
  }

  return (
    <>
      <h1>Application tracker</h1>
      <Card title="Add an application">
        <form className="row" onSubmit={add}>
          <div><label htmlFor="t">Name</label><input id="t" required value={title} onChange={(e) => setTitle(e.target.value)} /></div>
          <div><label htmlFor="d">Deadline</label><input id="d" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} /></div>
          <button>Add</button>
        </form>
        <ErrorText error={error} />
      </Card>
      <Card>
        {rows.length === 0 ? <Empty>No applications yet.</Empty> : (
          <table>
            <thead><tr><th>Application</th><th>Deadline</th><th>Status</th><th /></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id}>
                <td>{r.title.slice(0, 70)}</td>
                <td>{r.deadline ?? "-"} {r.days_left !== null && <Badge tone={r.days_left < 0 ? "bad" : r.days_left <= 7 ? "warn" : "good"}>{r.days_left < 0 ? "passed" : `${r.days_left}d`}</Badge>}</td>
                <td><select aria-label="Status" value={r.status} onChange={async (e) => { await api.patch(`/applications/${r.id}`, { status: e.target.value }); load(); }}>{STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</select></td>
                <td><button className="danger" onClick={async () => { await api.del(`/applications/${r.id}`); load(); }}>Remove</button></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Tracker /></AuthGate>;
}
