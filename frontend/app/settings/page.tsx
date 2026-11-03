"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Card, ConfirmDialog, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { Profile } from "@/lib/types";

function Settings() {
  const [share, setShare] = useState(() => (typeof window !== "undefined" ? localStorage.getItem("applypilot_share") ?? "ask" : "ask"));
  const [lang, setLang] = useState(() => (typeof window !== "undefined" ? localStorage.getItem("applypilot_lang") ?? "en" : "en"));
  const [profile, setProfile] = useState<Profile | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.get<Profile>("/profile").then(setProfile).catch(() => {}); }, []);

  async function downloadData() {
    setError(null);
    try {
      const [prof, notices, docs, apps] = await Promise.all([
        api.get("/profile"), api.get("/notices"), api.get("/documents"), api.get("/applications"),
      ]);
      const blob = new Blob([JSON.stringify({ profile: prof, notices, documents: docs, applications: apps }, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "my-applypilot-data.json"; a.click();
      URL.revokeObjectURL(url);
      setMsg("Downloaded. This file has your profile and lists — keep it private.");
    } catch (e) { setError(e instanceof Error ? e.message : "Download failed"); }
  }

  return (
    <>
      <h1>Settings</h1>
      <Card title="Language">
        <label htmlFor="lang">Reply language (saved on this device)</label>
        <select id="lang" value={lang} onChange={(e) => { setLang(e.target.value); localStorage.setItem("applypilot_lang", e.target.value); }}>
          <option value="en">English</option>
          <option value="hi">हिन्दी (Hindi) — coming soon</option>
        </select>
        <p className="muted small">Preview: {lang === "hi" ? "नमस्ते! मैं आपके नोटिस में मदद कर सकता हूँ।" : "Hello! I can help with your notices."}</p>
      </Card>

      <Card title="Sharing public notices">
        <label htmlFor="share">When you upload a public notice</label>
        <select id="share" value={share} onChange={(e) => { setShare(e.target.value); localStorage.setItem("applypilot_share", e.target.value); }}>
          <option value="ask">Ask me every time</option>
          <option value="always">Share it — help other students</option>
          <option value="never">Never share mine</option>
        </select>
        <p className="muted small">A shared notice is read once for everyone. Personal documents are never shared, whatever you choose here.</p>
      </Card>

      <Card title="Your data">
        <p className="muted">We keep your profile (encrypted), your vault files (encrypted), your notices and your applications. We never store ID numbers, passport or bank details.</p>
        {profile && <p className="small">Signed in as {String(profile.email ?? "")}. Profile fields filled: {Object.keys(profile).filter((k) => profile[k]).length}.</p>}
        <p><button type="button" className="secondary" onClick={downloadData}>Download my data</button></p>
        <ErrorText error={error} />
        {msg && <p className="ok">{msg}</p>}
      </Card>

      <Card title="Delete account">
        <p className="muted">This deletes your profile, vault files, notices and applications for this account. It cannot be undone. Shared public notices stay for other users, without your name.</p>
        <p><button type="button" className="danger" onClick={() => setConfirmDelete(true)}>Delete my account…</button></p>
      </Card>

      <ConfirmDialog open={confirmDelete} danger title="Delete your account?"
        body={<p>This will delete your profile, vault and applications. Type DELETE in the next step on the server is not needed — pressing Delete here is final.</p>}
        confirmLabel="Delete everything" onCancel={() => setConfirmDelete(false)}
        onConfirm={async () => {
          setConfirmDelete(false);
          setError("Account deletion is not enabled on this server yet. Contact the admin, or download your data above first.");
        }} />
    </>
  );
}

export default function Page() {
  return <AuthGate><Settings /></AuthGate>;
}
