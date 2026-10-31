"use client";
import { useEffect, useState } from "react";
import AuthGate from "@/components/AuthGate";
import { Card, Empty, ErrorText } from "@/components/ui";
import { api } from "@/lib/api";
import { DOC_KINDS, type DocumentRow } from "@/lib/types";

function Vault() {
  const [docs, setDocs] = useState<DocumentRow[]>([]);
  const [kind, setKind] = useState("other");
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
        await api.del(`/documents/${d.id}?force=true`); load();
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
          <div><label htmlFor="file">File (PDF, JPG, PNG, up to 10 MB)</label><input id="file" type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></div>
          <button disabled={!file}>Upload</button>
        </form>
        <ErrorText error={error} />
      </Card>
      <Card title="Your documents">
        {docs.length === 0 ? <Empty>Nothing stored yet.</Empty> : (
          <table>
            <thead><tr><th>Type</th><th>File</th><th>Copy of / for</th><th>Size</th><th /></tr></thead>
            <tbody>{docs.map((d) => (
              <tr key={d.id}><td>{d.kind.replace(/_/g, " ")}</td><td>{d.filename}</td>
                <td>{d.is_original ? "Original" : `Copy${d.app_ref ? ` · ${d.app_ref}` : ""}`}</td><td>{(d.size / 1024).toFixed(0)} KB</td>
                <td><button className="secondary" onClick={() => download(d)}>Download</button>{" "}
                  {d.is_original && <><button className="secondary" onClick={() => makeCopy(d)}>Make application copy</button>{" "}</>}
                  <button className="danger" onClick={() => remove(d)}>Delete</button></td></tr>
            ))}</tbody>
          </table>
        )}
      </Card>
    </>
  );
}

export default function Page() {
  return <AuthGate><Vault /></AuthGate>;
}
