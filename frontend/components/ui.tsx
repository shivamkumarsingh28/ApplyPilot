"use client";
import { useEffect, useState, type ReactNode } from "react";

export function Card({ title, children, action }: { title?: string; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="card">
      {(title || action) && (
        <div className="card-head">
          {title && <h2>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Badge({ tone, children }: { tone: "good" | "warn" | "bad" | "info"; children: ReactNode }) {
  const icon = tone === "good" ? "✓ " : tone === "bad" ? "✕ " : tone === "warn" ? "! " : "";
  return <span className={`badge ${tone}`}>{icon}{children}</span>;
}

/** Status chip with icon + word (spec 5.4): colour is never the only signal. */
export function StatusChip({ status }: { status: string }) {
  const map: Record<string, ["good" | "warn" | "bad" | "info", string]> = {
    eligible: ["good", "Eligible"], not_eligible: ["bad", "Not eligible"], needs_info: ["warn", "Needs info"],
    low: ["good", "Safe"], medium: ["warn", "Check carefully"], high: ["bad", "High risk"],
    verified: ["good", "Verified"], user_shared: ["info", "User uploaded"], private: ["info", "Only you"],
    planned: ["info", "Planned"], in_progress: ["warn", "In progress"], submitted: ["good", "Submitted"], closed: ["bad", "Closed"],
  };
  const [tone, label] = map[status] ?? ["info", status.replace(/_/g, " ")];
  return <Badge tone={tone}>{label}</Badge>;
}

export function ErrorText({ error }: { error: string | null }) {
  return error ? <p className="error" role="alert">⚠ {error}</p> : null;
}

export function Empty({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <p className="muted">{children}</p>
      {action}
    </div>
  );
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }).map((_, i) => <div key={i} className="skeleton" style={{ width: `${92 - i * 14}%` }} />)}
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  // span, not p: callers often place it inside a paragraph, and <p> cannot nest.
  return <span className="spinner-row" role="status"><span className="spinner" aria-hidden="true" /> {label}</span>;
}

/** Toast with Undo (spec 8.3). Controlled by the parent via `toast` state. */
export type ToastState = { text: string; undo?: () => void } | null;

export function Toast({ toast, close }: { toast: ToastState; close: () => void }) {
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(close, 8000);
    return () => clearTimeout(t);
  }, [toast, close]);
  if (!toast) return null;
  return (
    <div className="toast" role="status">
      <span>{toast.text}</span>
      {toast.undo && <button type="button" className="link" onClick={() => { toast.undo?.(); close(); }}>Undo</button>}
      <button type="button" className="link" onClick={close} aria-label="Dismiss">✕</button>
    </div>
  );
}

export function useToast(): [ToastState, (text: string, undo?: () => void) => void, () => void] {
  const [toast, setToast] = useState<ToastState>(null);
  return [toast, (text, undo) => setToast({ text, undo }), () => setToast(null)];
}

/** Confirmation dialog that names the thing (spec 8.3). Cancel is the default focus. */
export function ConfirmDialog({ open, title, body, confirmLabel, danger, onConfirm, onCancel }:
  { open: boolean; title: string; body: ReactNode; confirmLabel: string; danger?: boolean; onConfirm: () => void; onCancel: () => void }) {
  if (!open) return null;
  return (
    <div className="dialog-backdrop" role="presentation" onClick={onCancel}>
      <div className="dialog" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <h2>{title}</h2>
        <div>{body}</div>
        <div className="dialog-actions">
          <button type="button" className="secondary" autoFocus onClick={onCancel}>Cancel</button>
          <button type="button" className={danger ? "danger-solid" : ""} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}

/** Dates the human way (spec 8.6): "14 Nov 2026", never DD/MM confusion. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "not found";
  const d = new Date(iso + (iso.length === 10 ? "T00:00:00" : ""));
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function daysChip(days: number | null): ReactNode {
  if (days === null) return <Badge tone="info">no date</Badge>;
  if (days < 0) return <Badge tone="bad">closed</Badge>;
  if (days === 0) return <Badge tone="bad">last day today</Badge>;
  if (days <= 3) return <Badge tone="bad">{days} days left</Badge>;
  if (days <= 7) return <Badge tone="warn">{days} days left</Badge>;
  return <Badge tone="good">{days} days left</Badge>;
}
