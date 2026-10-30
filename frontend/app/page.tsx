"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, Empty } from "@/components/ui";
import { api } from "@/lib/api";
import type { Application, NoticeListItem, Summary } from "@/lib/types";

function tone(days: number | null): "good" | "warn" | "bad" | "info" {
  if (days === null) return "info";
  return days < 0 ? "bad" : days <= 7 ? "warn" : "good";
}

function fmtSaved(min: number): string {
  return min >= 60 ? `${Math.floor(min / 60)}h ${min % 60}m` : `${min}m`;
}

function Dashboard() {
  const [apps, setApps] = useState<Application[]>([]);
  const [notices, setNotices] = useState<NoticeListItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  async function downloadCalendar() {
    const blob = await api.blob("/applications/calendar.ics");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "applypilot-deadlines.ics"; a.click();
    URL.revokeObjectURL(url);
  }
  useEffect(() => {
    api.get<Application[]>("/applications").then(setApps).catch(() => {});
    api.get<NoticeListItem[]>("/notices").then(setNotices).catch(() => {});
    api.get<Summary>("/applications/summary").then(setSummary).catch(() => {});
  }, []);
  const open = apps.filter((a) => a.status === "planned" || a.status === "in_progress");
  return (
    <>
      <h1>Your applications</h1>
      {summary && (
        <Card title="At a glance" action={<button className="secondary" onClick={downloadCalendar}>Add deadlines to my calendar (.ics)</button>}>
          <p>
            <strong>{summary.open}</strong> open · <strong>{summary.submitted}</strong> submitted ·{" "}
            <strong>{summary.notices}</strong> notices read · <strong>{summary.documents_ready}</strong> documents ready ·{" "}
            Time saved: <strong>{fmtSaved(summary.time_saved_minutes)}</strong>
            {summary.next_deadline && <> · Next: {summary.next_title?.slice(0, 50)} — {summary.next_deadline} ({summary.next_days_left}d left)</>}
          </p>
        </Card>
      )}
      <div className="grid">
        <Card title="Deadlines" action={<Link href="/tracker">Open tracker</Link>}>
          {open.length === 0 ? <Empty>No open applications. Add a notice to start.</Empty> : (
            <ul className="plain">
              {open.slice(0, 6).map((a) => (
                <li key={a.id}>
                  {a.title.slice(0, 60)}{" "}
                  <Badge tone={tone(a.days_left)}>{a.days_left === null ? "no date" : a.days_left < 0 ? "closed" : `${a.days_left} days left`}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Quick start">
          <ol>
            <li><Link href="/profile">Fill your profile once</Link></li>
            <li><Link href="/notices">Add a job or admission notice</Link>, then ask it questions</li>
            <li><Link href="/photo">Fix your photo and signature</Link> for its exact rules</li>
            <li>Install the browser extension to fill the form in one click</li>
          </ol>
        </Card>
      </div>
      <Card title="Recent notices" action={<Link href="/notices">All notices</Link>}>
        {notices.length === 0 ? <Empty>Nothing yet.</Empty> : (
          <ul className="plain">
            {notices.slice(0, 5).map((n) => (
              <li key={n.id}><Link href={`/notices/${n.id}`}>{n.title.slice(0, 80)}</Link> <span className="muted small">last date {n.last_date ?? "not found"}</span></li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Dashboard /></AuthGate>;
}
