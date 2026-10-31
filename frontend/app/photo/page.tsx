"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { NoticeListItem, PhotoResult } from "@/lib/types";

function Studio() {
  const params = useSearchParams();
  const [kind, setKind] = useState<"photo" | "signature">("photo");
  const [notices, setNotices] = useState<NoticeListItem[]>([]);
  const [noticeId, setNoticeId] = useState(params.get("notice") ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [orig, setOrig] = useState<string | null>(null);
  const [custom, setCustom] = useState({ width: "", height: "", min_kb: "", max_kb: "" });
  const [background, setBackground] = useState("white");
  const [customColour, setCustomColour] = useState("");
  const [result, setResult] = useState<PhotoResult | null>(null);
  const [save, setSave] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.get<NoticeListItem[]>("/notices").then(setNotices).catch(() => {}); }, []);
  useEffect(() => {
    if (!file) return setOrig(null);
    const url = URL.createObjectURL(file);
    setOrig(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    form.append("save_to_vault", String(save));
    if (noticeId) form.append("notice_id", noticeId);
    form.append("background", customColour.trim() || background);
    (Object.entries(custom) as [string, string][]).forEach(([k, v]) => v && form.append(k, v));
    try {
      setResult(await api.upload<PhotoResult>("/photo/process", form));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process the image");
    } finally {
      setBusy(false);
    }
  }

  const outUrl = result ? `data:${result.mime};base64,${result.data_base64}` : null;
  return (
    <>
      <h1>Photo and signature studio</h1>
      <Card>
        <form onSubmit={run}>
          <div className="row">
            <div><label htmlFor="k">What are you fixing?</label>
              <select id="k" value={kind} onChange={(e) => setKind(e.target.value as "photo" | "signature")}>
                <option value="photo">Passport-size photo</option><option value="signature">Signature</option>
              </select></div>
            <div><label htmlFor="n">Use the rules from a notice</label>
              <select id="n" value={noticeId} onChange={(e) => setNoticeId(e.target.value)}>
                <option value="">Enter rules myself</option>
                {notices.map((n) => <option key={n.id} value={n.id}>{n.title.slice(0, 50)}</option>)}
              </select></div>
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            {(["width", "height", "min_kb", "max_kb"] as const).map((f) => (
              <div key={f}><label htmlFor={f}>{f === "width" ? "Width (px)" : f === "height" ? "Height (px)" : f === "min_kb" ? "Min KB" : "Max KB"}</label>
                <input id={f} inputMode="numeric" value={custom[f]} placeholder={noticeId ? "from notice" : ""} onChange={(e) => setCustom({ ...custom, [f]: e.target.value.replace(/\D/g, "") })} /></div>
            ))}
          </div>
          {kind === "photo" && (
            <div className="row" style={{ marginTop: 12 }}>
              <div><label htmlFor="bg">Background colour</label>
                <select id="bg" value={background} onChange={(e) => setBackground(e.target.value)}>
                  <option value="white">White</option><option value="light blue">Light blue</option>
                  <option value="blue">Blue</option><option value="grey">Grey</option><option value="cream">Cream</option>
                </select></div>
              <div><label htmlFor="bgc">Or any colour (name or #hex)</label>
                <input id="bgc" value={customColour} onChange={(e) => setCustomColour(e.target.value)} placeholder="light blue or #e6f0ff" /></div>
              <div><label htmlFor="bgp">Pick</label><input id="bgp" type="color" value={customColour.startsWith("#") ? customColour : "#e6f0ff"} onChange={(e) => setCustomColour(e.target.value)} style={{ height: 42, padding: 2 }} /></div>
            </div>
          )}
          <p className="muted small">If the notice requires a specific background, that rule wins and a warning is shown.</p>
          <p><label htmlFor="img">Your {kind} (JPG or PNG)</label><input id="img" type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></p>
          <p><label><input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} style={{ width: "auto" }} /> Save the result to my vault</label></p>
          <ErrorText error={error} />
          <button disabled={!file || busy}>{busy ? "Working..." : "Make it match"}</button>
        </form>
      </Card>

      {(orig || outUrl) && (
        <div className="grid">
          <Card title="Original">{orig && <img className="preview" src={orig} alt="Original upload" style={{ maxHeight: 360 }} />}</Card>
          <Card title="Ready to upload">
            {outUrl && result && (
              <>
                <img className="preview" src={outUrl} alt="Processed result" style={{ maxHeight: 360 }} />
                <ul className="plain">
                  {result.report.checks.map((c) => <li key={c.name}><Badge tone={c.ok ? "good" : "bad"}>{c.ok ? "ok" : "check"}</Badge> {c.name}: <span className="muted small">{c.detail}</span></li>)}
                </ul>
                {result.report.warnings.map((w) => <p key={w} className="error small">{w}</p>)}
                <p><a className="btn" href={outUrl} download={result.filename}>Download {result.filename}</a></p>
              </>
            )}
          </Card>
        </div>
      )}
    </>
  );
}

export default function Page() {
  return <AuthGate><Suspense fallback={null}><Studio /></Suspense></AuthGate>;
}
