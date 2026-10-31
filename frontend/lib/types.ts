export type User = { id: number; email: string; full_name: string; role: string };

export type Check = { rule: string; status: "pass" | "fail" | "unknown"; detail: string };
export type Eligibility = { verdict: "eligible" | "not_eligible" | "needs_info"; checks: Check[]; missing_profile_fields: string[]; disclaimer: string };
export type Readiness = { percent: number; have: { kind: string; label: string }[]; missing: { kind: string; label: string }[]; days_left: number | null };
export type ImageSpec = { width: number | null; height: number | null; min_kb: number | null; max_kb: number | null; format: string; background: string };

export type Structured = {
  title: string;
  organisation: string | null;
  last_date: string | null;
  age: { min: number | null; max: number | null; as_of: string | null; relaxations: Record<string, number> };
  qualification: { level: string | null; min_percentage: number | null; text: string };
  fee: { amount: number; currency: string } | null;
  documents: string[];
  photo_spec: ImageSpec | null;
  signature_spec: ImageSpec | null;
  selection_stages: string[];
  needs_review: { field: string; rules: unknown; model: unknown }[];
  method: string;
};

export type ScamReport = { score: number; level: "low" | "medium" | "high"; reasons: string[]; tips: string[]; disclaimer: string };
export type Notice = { id: number; title: string; source_filename: string; structured: Structured; scam_report: ScamReport; created_at: string };
export type NoticeListItem = { id: number; title: string; last_date: string | null; scam_level: string | null; created_at: string };
export type Answer = { answer: string; mode: string; citations: { page: number; text: string; score: number }[] };

export type DocumentRow = { id: number; kind: string; filename: string; mime: string; size: number; created_at: string; is_original: boolean; original_id: number | null; application_id: number | null; notice_id: number | null; app_ref: string };
export type IngestJob = { id: number; status: string; notice_id: number | null; error: string; source: string; timings: Record<string, number>; summary: string[]; title: string | null };
export type Application = { id: number; title: string; notice_id: number | null; status: string; deadline: string | null; notes: string; days_left: number | null };
export type Summary = { total: number; open: number; submitted: number; closed: number; notices: number; documents_ready: number; next_deadline: string | null; next_title: string | null; next_days_left: number | null; time_saved_minutes: number };
export type PhotoResult = {
  filename: string; mime: string; data_base64: string; document_id: number | null;
  report: { ok: boolean; warnings: string[]; checks: { name: string; ok: boolean; detail: string }[] };
  spec: Partial<ImageSpec>;
};
export type Profile = Record<string, string | number | boolean | null | undefined>;

export const DOC_KINDS = ["photo", "signature", "marksheet_10", "marksheet_12", "degree", "caste_certificate", "domicile", "id_proof", "birth_certificate", "other"];
