"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ErrorText } from "@/components/ui";
import { api, auth } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", full_name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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
      <h1>ApplyPilot</h1>
      <p className="muted">Read notices, fix your photo and signature, and fill forms in one click.</p>
      {mode === "register" && (
        <p><label htmlFor="n">Full name</label><input id="n" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></p>
      )}
      <p><label htmlFor="e">Email</label><input id="e" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></p>
      <p><label htmlFor="p">Password (8+ characters)</label><input id="p" type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></p>
      <ErrorText error={error} />
      <p><button disabled={busy}>{mode === "login" ? "Sign in" : "Create account"}</button></p>
      <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "New here? Create an account" : "Have an account? Sign in"}
      </button>
    </form>
  );
}
