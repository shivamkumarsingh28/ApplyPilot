"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, Empty, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { Application } from "@/lib/types";

const STATUSES = ["planned", "in_progress", "submitted", "closed"];

function Tracker() {
  const [rows, setRows] = useState<Application[]>([]);
  const [view, setView] = useState<"list" | "board">("list");
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
      <div className="tabs" role="tablist" aria-label="Tracker view">
        <button type="button" className={view === "list" ? "active" : ""} onClick={() => setView("list")}>List</button>
        <button type="button" className={view === "board" ? "active" : ""} onClick={() => setView("board")}>Board</button>
      </div>
      {view === "board" ? (
        <div className="board">
          {STATUSES.map((st) => (
            <div key={st} className="board-col">
              <h3 style={{ textTransform: "capitalize" }}>{st.replace("_", " ")}</h3>
              {rows.filter((r) => r.status === st).map((r) => (
                <div key={r.id} className="board-card">
                  <strong>{r.title.slice(0, 50)}</strong>
                  <div className="muted small">{r.deadline ?? "no date"}</div>
                  {r.days_left !== null && <Badge tone={r.days_left < 0 ? "bad" : r.days_left <= 3 ? "bad" : r.days_left <= 7 ? "warn" : "good"}>{r.days_left < 0 ? "passed" : `${r.days_left} days left`}</Badge>}
                  <div><select aria-label={`Move ${r.title}`} value={r.status} onChange={async (e) => { try { await api.patch(`/applications/${r.id}`, { status: e.target.value }); load(); } catch (err) { setError(err instanceof Error ? err.message : "Could not update"); } }}>{STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</select></div>
                </div>
              ))}
              {rows.filter((r) => r.status === st).length === 0 && <p className="muted small">Nothing here.</p>}
            </div>
          ))}
        </div>
      ) : (
      <Card>
        {rows.filter((r) => r.days_left !== null && r.days_left <= 7 && ["planned", "in_progress"].includes(r.status)).length > 0 && (
          <>
            <h3>Closing soon</h3>
            <ul className="plain">{rows.filter((r) => r.days_left !== null && r.days_left <= 7 && ["planned", "in_progress"].includes(r.status)).map((r) => (
              <li key={r.id}><strong>{r.title.slice(0, 60)}</strong> <Badge tone="bad">{r.days_left! < 0 ? "passed" : `${r.days_left} days left`}</Badge> <span className="muted small">{r.deadline}</span></li>
            ))}</ul>
            <h3>All applications</h3>
          </>
        )}
        {rows.length === 0 ? <Empty>No applications yet. Add one above, or open a notice and it is tracked for you.</Empty> : (
          <table>
            <thead><tr><th>Application</th><th>Deadline</th><th>Status</th><th /></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id}>
                <td>{r.title.slice(0, 70)}</td>
                <td>{r.deadline ?? "-"} {r.days_left !== null && <Badge tone={r.days_left < 0 ? "bad" : r.days_left <= 7 ? "warn" : "good"}>{r.days_left < 0 ? "passed" : `${r.days_left}d`}</Badge>}</td>
                <td><select aria-label="Status" value={r.status} onChange={async (e) => { try { await api.patch(`/applications/${r.id}`, { status: e.target.value }); load(); } catch (err) { setError(err instanceof Error ? err.message : "Could not update"); } }}>{STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}</select></td>
                <td><button className="danger" onClick={async () => { if (!window.confirm(`Remove "${r.title.slice(0, 60)}" from your tracker?`)) return; try { await api.del(`/applications/${r.id}`); load(); } catch (err) { setError(err instanceof Error ? err.message : "Could not remove"); } }}>Remove</button></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </Card>
      )}
    </>
  );
}

export default function Page() {
  return <AuthGate><Tracker /></AuthGate>;
}
