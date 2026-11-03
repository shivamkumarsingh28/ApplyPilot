"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ErrorText } from "@/components/ui";
import ThemeToggle from "@/components/ThemeToggle";
import { api, auth } from "@/lib/api";

const PROVIDER_LABEL: Record<string, string> = { google: "Continue with Google", github: "Continue with GitHub", linkedin: "Continue with LinkedIn" };

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", full_name: "" });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [providers, setProviders] = useState<string[]>([]);
  useEffect(() => { api.get<{ providers: string[] }>("/auth/providers").then((r) => setProviders(r.providers)).catch(() => {}); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = mode === "login" ? { email: form.email, password: form.password } : form;
      const res = await api.post<{ access_token: string }>(`/auth/${mode}`, body);
      auth.set(res.access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card login" onSubmit={submit}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>ApplyPilot</h1><ThemeToggle />
      </div>
      <p className="muted">Read notices, fix your photo and signature, and fill forms in one click.</p>
      <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
      {providers.map((p) => (
        <p key={p}><a className="btn provider-btn" href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/oauth/${p}/start`}>{PROVIDER_LABEL[p] ?? `Continue with ${p}`}</a></p>
      ))}
      {providers.length > 0 && <p className="muted small" style={{ textAlign: "center" }}>— or use email —</p>}
      {mode === "register" && (
        <p><label htmlFor="n">Full name</label><input id="n" autoComplete="name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></p>
      )}
      <p><label htmlFor="e">Email</label><input id="e" type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></p>
      <p>
        <label htmlFor="p">Password</label>
        <span style={{ display: "flex", gap: 8 }}>
          <input id="p" type={showPw ? "text" : "password"} autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <button type="button" className="secondary" onClick={() => setShowPw(!showPw)} aria-pressed={showPw}>{showPw ? "Hide" : "Show"}</button>
        </span>
        {mode === "register" && <span className={form.password.length >= 8 ? "ok small" : "muted small"}>{form.password.length >= 8 ? "✓ At least 8 characters" : "At least 8 characters"}</span>}
      </p>
      <ErrorText error={error} />
      <p><button disabled={busy} style={{ width: "100%" }}>{busy ? "One moment…" : mode === "login" ? "Log in" : "Create account"}</button></p>
      <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "New here? Create an account" : "Have an account? Log in"}
      </button>
      {mode === "register" && <p className="muted small">By continuing you agree to the Terms and Privacy Policy. We never ask for ID numbers.</p>}
    </form>
  );
}
