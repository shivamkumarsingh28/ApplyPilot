"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Badge, Card, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import type { NoticeListItem, PhotoResult } from "@/lib/types";

type Mode = "photo_resize" | "photo" | "signature" | "document";
const MODES: { id: Mode; title: string; desc: string }[] = [
  { id: "photo_resize", title: "Resize only", desc: "Exact pixels + KB. Colours and background untouched." },
  { id: "photo", title: "Full photo fix", desc: "Face crop + background colour + size, for passport photos." },
  { id: "signature", title: "Signature", desc: "Clean ink, tight crop, centred on white." },
  { id: "document", title: "Document scan", desc: "Certificates/marksheets: light cleanup + size. No face, no background change." },
];
const PRESETS: Record<string, { w: string; h: string; max: string }> = {
  "": { w: "", h: "", max: "" },
  passport_in: { w: "413", h: "531", max: "200" },      // 35x45mm @300dpi
  ssc_upsc: { w: "200", h: "230", max: "50" },
  state_portal: { w: "300", h: "350", max: "100" },
  signature_common: { w: "300", h: "100", max: "30" },
};

function Studio() {
  const params = useSearchParams();
  const [mode, setMode] = useState<Mode>("photo_resize");
  const [notices, setNotices] = useState<NoticeListItem[]>([]);
  const [noticeId, setNoticeId] = useState(params.get("notice") ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [orig, setOrig] = useState<string | null>(null);
  const [preset, setPreset] = useState("");
  const [custom, setCustom] = useState({ width: "", height: "", min_kb: "", max_kb: "" });
  const [unit, setUnit] = useState<"px" | "cm">("px");
  const [resizeMode, setResizeMode] = useState("crop");
  const [format, setFormat] = useState("jpg");
  const [keepBackground, setKeepBackground] = useState(false);
  const [enhance, setEnhance] = useState(true);
  const [background, setBackground] = useState("white");
  const [customColour, setCustomColour] = useState("");
  const [saveName, setSaveName] = useState("");
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

  const toPx = (v: string) => (unit === "cm" && v ? String(Math.round((Number(v) / 2.54) * 300)) : v);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setBusy(true); setError(null); setResult(null);
    const form = new FormData();
    form.append("file", file);
    form.append("kind", mode);
    form.append("save_to_vault", String(save));
    if (saveName.trim()) form.append("save_as", saveName.trim());
    if (noticeId) form.append("notice_id", noticeId);
    form.append("resize_mode", resizeMode);
    form.append("format", format);
    if (mode === "photo") { form.append("change_background", String(!keepBackground)); form.append("background", customColour.trim() || background); }
    if (mode === "document") form.append("enhance", String(enhance));
    const dims = { width: toPx(custom.width), height: toPx(custom.height), min_kb: custom.min_kb, max_kb: custom.max_kb };
    (Object.entries(dims) as [string, string][]).forEach(([k, v]) => v && form.append(k, v));
    try {
      setResult(await api.upload<PhotoResult>("/photo/process", form));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process the image");
    } finally { setBusy(false); }
  }

  const outUrl = result ? `data:${result.mime};base64,${result.data_base64}` : null;
  const active = MODES.find((m) => m.id === mode)!;
  return (
    <>
      <h1>Photo Studio</h1>
      <p className="muted">Fix the exact problems portals reject: wrong pixels, wrong KB, wrong format, wrong background. Your original is never changed — results save to the vault as a copy.</p>

      <div className="grid" role="radiogroup" aria-label="Studio mode">
        {MODES.map((m) => (
          <button key={m.id} type="button" className={mode === m.id ? "" : "secondary"} onClick={() => setMode(m.id)} aria-pressed={mode === m.id} style={{ textAlign: "left" }}>
            <strong>{m.title}</strong><br /><span className="small">{m.desc}</span>
          </button>
        ))}
      </div>

      <Card title={active.title}>
        <form onSubmit={run}>
          <div className="row">
            <div><label htmlFor="n">Use the rules from a notice (optional)</label>
              <select id="n" value={noticeId} onChange={(e) => setNoticeId(e.target.value)}>
                <option value="">Enter rules myself</option>
                {notices.map((n) => <option key={n.id} value={n.id}>{n.title.slice(0, 50)}</option>)}
              </select></div>
            <div><label htmlFor="preset">Common sizes</label>
              <select id="preset" value={preset} onChange={(e) => { setPreset(e.target.value); const p = PRESETS[e.target.value]; if (p) setCustom({ width: p.w, height: p.h, min_kb: "", max_kb: p.max }); }}>
                <option value="">Custom</option>
                <option value="passport_in">Passport 35×45mm (413×531px, ≤200KB)</option>
                <option value="ssc_upsc">SSC/UPSC style (200×230px, ≤50KB)</option>
                <option value="state_portal">State portal (300×350px, ≤100KB)</option>
                <option value="signature_common">Signature (300×100px, ≤30KB)</option>
              </select></div>
            <div><label htmlFor="unit">Size unit</label>
              <select id="unit" value={unit} onChange={(e) => setUnit(e.target.value as "px" | "cm")}>
                <option value="px">Pixels (px)</option><option value="cm">Centimetres @300dpi</option>
              </select></div>
          </div>

          <div className="row" style={{ marginTop: 12 }}>
            {(["width", "height", "min_kb", "max_kb"] as const).map((f) => (
              <div key={f}><label htmlFor={f}>{f === "width" ? `Width (${unit})` : f === "height" ? `Height (${unit})` : f === "min_kb" ? "Min KB" : "Max KB"}</label>
                <input id={f} inputMode="numeric" value={custom[f]} placeholder={noticeId ? "from notice" : ""} onChange={(e) => setCustom({ ...custom, [f]: e.target.value.replace(/[^\d.]/g, "") })} /></div>
            ))}
            {(mode === "photo_resize" || mode === "document") && (
              <div><label htmlFor="rm">When the shape differs</label>
                <select id="rm" value={resizeMode} onChange={(e) => setResizeMode(e.target.value)}>
                  <option value="crop">Crop to shape (fill the box)</option>
                  <option value="fit">Fit inside + white padding (cut nothing)</option>
                  <option value="stretch">Stretch to exact pixels</option>
                </select></div>
            )}
            <div><label htmlFor="fmt">Output format</label>
              <select id="fmt" value={format} onChange={(e) => setFormat(e.target.value)}>
                <option value="jpg">JPG (smallest, most portals)</option>
                <option value="png">PNG</option>
              </select></div>
          </div>

          {mode === "photo" && (
            <>
              <p><label><input type="checkbox" checked={keepBackground} onChange={(e) => setKeepBackground(e.target.checked)} style={{ width: "auto" }} /> Keep my original background (do not change the colour)</label></p>
              {!keepBackground && (
                <div className="row" style={{ marginTop: 8 }}>
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
            </>
          )}
          {mode === "document" && <p><label><input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} style={{ width: "auto" }} /> Gently fix uneven light/shadows on the scan</label></p>}

          <p><label htmlFor="img">Your {mode === "signature" ? "signature" : mode === "document" ? "document photo/scan" : "photo"} (JPG or PNG)</label>
            <input id="img" type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></p>
          {file && <p className="muted small">Selected: {file.name} · {(file.size / 1024).toFixed(0)} KB</p>}
          <div className="row">
            <div><label htmlFor="savename">Save in vault as (optional)</label><input id="savename" value={saveName} onChange={(e) => setSaveName(e.target.value)} placeholder={mode === "signature" ? "signature_ready" : mode === "document" ? "document_ready" : "photo_ready"} /></div>
          </div>
          <p><label><input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} style={{ width: "auto" }} /> Save the result to my vault (as a copy — the original stays untouched)</label></p>
          <ErrorText error={error} />
          <button disabled={!file || busy}>{busy ? "Working..." : mode === "photo_resize" ? "Resize only" : "Process"}</button>
        </form>
      </Card>

      {(orig || outUrl) && (
        <div className="grid">
          <Card title="Original">{orig && <img className="preview" src={orig} alt="Original upload" style={{ maxHeight: 360 }} />}{file && <p className="muted small">{file.name} · {(file.size / 1024).toFixed(1)} KB</p>}</Card>
          <Card title="Ready to upload">
            {outUrl && result && (
              <>
                <img className="preview" src={outUrl} alt="Processed result" style={{ maxHeight: 360 }} />
                <p className="small">{result.filename} · {(result.report.bytes / 1024).toFixed(1)} KB</p>
                <ul className="plain">
                  {result.report.checks.map((c) => <li key={c.name}><Badge tone={c.ok ? "good" : "bad"}>{c.ok ? "ok" : "check"}</Badge> {c.name}: <span className="muted small">{c.detail}</span></li>)}
                </ul>
                {result.report.warnings.map((w) => <p key={w} className="error small">{w}</p>)}
                <p>
                  <a className="btn" href={outUrl} download={result.filename}>Download {result.filename}</a>{" "}
                  {result.document_id ? <span className="muted small">Saved to your vault ✓{result.app_ref ? ` (${result.app_ref})` : ""}</span> : <span className="muted small">Not saved (tick “Save the result” to keep it in the vault)</span>}
                </p>
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
