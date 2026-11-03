"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Card, Empty, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import { DOC_KINDS, type DocumentRow } from "@/lib/types";

function Vault() {
  const [docs, setDocs] = useState<DocumentRow[]>([]);
  const [kind, setKind] = useState("other");
  const [customKind, setCustomKind] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = () => api.get<DocumentRow[]>("/documents").then(setDocs).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    if (kind === "other" && customKind.trim()) form.append("custom_kind", customKind.trim());
    try { await api.upload("/documents", form); setFile(null); (e.target as HTMLFormElement).reset(); setError(null); load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Upload failed"); }
  }

  async function makeCopy(d: DocumentRow) {
    try { await api.post(`/documents/${d.id}/copy`, {}); load(); } catch (e) { setError(e instanceof Error ? e.message : "Copy failed"); }
  }

  async function remove(d: DocumentRow) {
    try { await api.del(`/documents/${d.id}`); load(); }
    catch (e) {
      if (confirm(`${e instanceof Error ? e.message : "Has copies."} Delete the original and its copies?`)) {
        try { await api.del(`/documents/${d.id}?force=true`); load(); }
        catch (err) { setError(err instanceof Error ? err.message : "Delete failed"); }
      }
    }
  }

  async function download(d: DocumentRow) {
    const blob = await api.blob(`/documents/${d.id}/download`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = d.filename; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <h1>Document vault</h1>
      <p className="muted">Files are encrypted before they are stored.</p>
      <Card title="Add a document">
        <form className="row" onSubmit={upload}>
          <div><label htmlFor="kind">Type</label><select id="kind" value={kind} onChange={(e) => setKind(e.target.value)}>{DOC_KINDS.map((k) => <option key={k} value={k}>{k.replace(/_/g, " ")}</option>)}</select></div>
          {kind === "other" && <div><label htmlFor="custom-kind">Your own type name (optional)</label><input id="custom-kind" value={customKind} onChange={(e) => setCustomKind(e.target.value)} placeholder="e.g. Income Certificate" maxLength={80} /></div>}
          <div><label htmlFor="file">File (PDF, JPG, PNG, up to 10 MB)</label><input id="file" type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></div>
          <button disabled={!file}>Upload</button>
        </form>
        <ErrorText error={error} />
      </Card>
      <Card title="Your documents">
        {docs.length > 0 && (() => {
          const used = docs.reduce((a, d) => a + d.size, 0) / 1048576;
          return <><div className="bar" aria-label={`${used.toFixed(1)} MB used`}><div style={{ width: `${Math.min(100, (used / 50) * 100)}%` }} /></div>
            <p className="muted small">{used.toFixed(1)} MB of 50 MB used · files are encrypted before they are saved</p></>;
        })()}
        {docs.length === 0 ? (
          <Empty>Nothing here yet. Add your photo, signature and certificates once. We make the right copy for each application.</Empty>
        ) : (
          ["photo", "signature", "marksheet_10", "marksheet_12", "degree", "other"].map((group) => {
            const inGroup = docs.filter((d) => (group === "other" ? !["photo", "signature", "marksheet_10", "marksheet_12", "degree"].includes(d.kind) : d.kind === group));
            if (!inGroup.length) return null;
            const originals = inGroup.filter((d) => d.is_original);
            const copiesOf = (oid: number) => inGroup.filter((d) => !d.is_original && d.original_id === oid);
            const orphans = inGroup.filter((d) => !d.is_original && !originals.some((o) => o.id === d.original_id));
            const row = (d: DocumentRow, indent: boolean) => (
              <li key={d.id} style={indent ? { marginLeft: 22 } : undefined}>
                {indent ? "↳ " : ""}<strong>{d.filename}</strong> <span className="muted small">{d.custom_kind || d.kind.replace(/_/g, " ")} · {(d.size / 1024).toFixed(0)} KB{d.is_original ? " · Original" : ` · Copy${d.app_ref ? ` for ${d.app_ref}` : ""}`}</span>
                <div>
                  <button type="button" className="secondary" onClick={() => download(d)}>Download</button>{" "}
                  {d.is_original && <><button type="button" className="secondary" onClick={() => makeCopy(d)}>Make a copy for an application</button>{" "}</>}
                  <button type="button" className="danger" onClick={() => remove(d)}>Delete</button>
                </div>
              </li>
            );
            return (
              <div key={group}>
                <h3 style={{ textTransform: "capitalize" }}>{group === "other" ? "Certificates and other" : group.replace(/_/g, " ")}</h3>
                <ul className="plain">
                  {originals.map((o) => [row(o, false), ...copiesOf(o.id).map((c) => row(c, true))])}
                  {orphans.map((c) => row(c, false))}
                </ul>
              </div>
            );
          })
        )}
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Vault /></AuthGate>;
}
