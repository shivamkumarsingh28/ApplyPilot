/**
 * Matches vault documents to a page's file fields.
 *
 * Design rule (real-user problem): a student filling a form often does not know
 * which file goes where, and time is short. So this matcher NEVER forces a
 * guess: an exact kind+type match is pre-selected ("exact"); anything else is
 * "possible" and the user must choose explicitly. Type-incompatible documents
 * are excluded entirely — a PDF is never offered for an image-only field.
 *
 * Pure logic (no DOM, no chrome APIs) so it runs in the popup and in node tests.
 */
(function (root) {
  "use strict";

  const KIND_MATCH = {
    photo: ["photo"], signature: ["signature"],
    marksheet_10: ["marksheet_10", "marksheet"], marksheet_12: ["marksheet_12", "marksheet"],
    marksheet: ["marksheet_10", "marksheet_12"], degree: ["degree"],
    caste_certificate: ["caste_certificate"], domicile: ["domicile"],
    id_proof: ["id_proof"], birth_certificate: ["birth_certificate"],
    certificate: ["degree", "marksheet_10", "marksheet_12", "caste_certificate", "domicile", "id_proof", "birth_certificate", "other"],
    other: ["other", "photo", "signature", "degree"],
  };
  const GENERIC_KINDS = new Set(["certificate", "other"]);
  const IMAGE_MIMES = ["image/jpeg", "image/png", "image/webp"];

  function acceptAllows(field, doc) {
    const accept = (field.accept || "").trim().toLowerCase();
    if (!accept) return true;
    const mime = (doc.mime || "").toLowerCase();
    const ext = "." + ((doc.filename || "").split(".").pop() || "").toLowerCase();
    return accept.split(",").some((raw) => {
      const a = raw.trim();
      if (!a) return false;
      if (a === "*/*" || a === "*") return true;
      if (a.endsWith("/*")) return mime.startsWith(a.slice(0, -1));
      if (a.startsWith(".")) return ext === a || mime === a;
      return mime === a;
    });
  }

  /** Score one document for one field; -1 = cannot be used in this field. Also returns WHY. */
  function scoreDoc(field, doc, noticeId) {
    if (!acceptAllows(field, doc)) return { score: -1, reasons: ["wrong file type for this field"] };
    const kinds = KIND_MATCH[field.kind] || [field.kind];
    const reasons = [];
    let score = -1;
    if (doc.kind === field.kind) { score = 50; reasons.push("vault tag matches: " + doc.kind.replace(/_/g, " ")); }
    else if (kinds.includes(doc.kind)) { score = 30; reasons.push("related document: " + String(doc.kind).replace(/_/g, " ")); }
    else if (field.kind === "other") { score = 10; reasons.push("any document (field is generic)"); }
    if (score < 0) return { score: -1, reasons: ["different document kind"] };
    reasons.push("type OK: " + (doc.mime || "file"));
    if (noticeId && doc.notice_id === noticeId && !doc.is_original) { score += 40; reasons.push("application copy made for this notice (form-ready size)"); }
    else if (!doc.is_original) { score += 15; reasons.push("application copy (form-ready)"); }
    if ((field.kind === "photo" || field.kind === "signature") && !IMAGE_MIMES.includes((doc.mime || "").toLowerCase())) score -= 10;
    return { score, reasons };
  }

  /** Parse "max 50 KB" / "20 KB to 50 KB" / "below 200KB" out of a field hint. */
  function parseSizeLimitKb(text) {
    const t = String(text || "").toLowerCase();
    let m = t.match(/(\d+(?:\.\d+)?)\s*kb\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*kb/);
    if (m) return { minKb: parseFloat(m[1]), maxKb: parseFloat(m[2]) };
    m = t.match(/(?:max(?:imum)?|up to|below|under|not more than)\s*(\d+(?:\.\d+)?)\s*(kb|mb)/);
    if (m) return { minKb: null, maxKb: m[2] === "mb" ? parseFloat(m[1]) * 1024 : parseFloat(m[1]) };
    m = t.match(/(\d+(?:\.\d+)?)\s*(kb|mb)\s*(?:max|limit)/);
    if (m) return { minKb: null, maxKb: m[2] === "mb" ? parseFloat(m[1]) * 1024 : parseFloat(m[1]) };
    return { minKb: null, maxKb: null };
  }

  /** Human warning when the chosen file breaks the field's size rule. Never blocks — the user decides. */
  function sizeWarning(field, doc) {
    if (!doc || !doc.size) return "";
    const { minKb, maxKb } = parseSizeLimitKb(field.hint);
    const kb = doc.size / 1024;
    if (maxKb && kb > maxKb) return "This file is " + Math.round(kb) + " KB but this field allows max " + maxKb + " KB. Use Photo Studio / an application copy, or choose another file.";
    if (minKb && kb < minKb) return "This file is " + Math.round(kb) + " KB but this field asks for at least " + minKb + " KB.";
    return "";
  }

  /**
   * @returns [{field, suggested, choices, confidence, reason}]
   * confidence "exact"  -> one clear winner, pre-selected.
   * confidence "possible" -> tie, generic field, or no exact tag: suggested is null, user MUST choose.
   * choices are vault docs annotated {_score, _reasons} best-first; incompatible docs removed.
   */
  function matchFields(fileFields, docs, noticeId) {
    return (fileFields || []).map((field) => {
      const scored = (docs || [])
        .map((doc) => ({ doc, ...scoreDoc(field, doc, noticeId) }))
        .filter((c) => c.score >= 0)
        .sort((a, b) => b.score - a.score);
      const choices = scored.map((c) => Object.assign({}, c.doc, { _score: c.score, _reasons: c.reasons }));
      const top = scored[0];
      const tied = scored.length > 1 && scored[1].score === (top && top.score);
      const exactTag = top && top.doc.kind === field.kind;
      const exact = !!top && !tied && exactTag && !GENERIC_KINDS.has(field.kind);
      return {
        field,
        suggested: exact ? choices[0] : null,
        choices,
        confidence: !top ? "none" : exact ? "exact" : "possible",
        reason: top ? top.reasons.join("; ") : "no compatible file in your vault",
        needsChoice: !!top && !exact,
      };
    });
  }

  /** Stable memory key: same website + same field wording -> same choice next time. */
  function choiceKey(host, field) {
    return "choice:" + host + ":" + String((field && (field.name || field.label)) || "file").toLowerCase().trim();
  }

  const api = { matchFields, scoreDoc, acceptAllows, parseSizeLimitKb, sizeWarning, choiceKey, KIND_MATCH };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ApplyPilotVault = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
