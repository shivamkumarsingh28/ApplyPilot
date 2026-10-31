"""Printable application checklist + iCalendar deadlines.

Both are built from data the user already owns (notice facts, eligibility,
readiness). No AI is involved: a checklist a user prints before a deadline
must be deterministic and explainable, like the eligibility engine.
"""

from __future__ import annotations

import html
from datetime import date, datetime, time, timedelta

from app.services.eligibility import QUAL_LABEL
from app.services.readiness import LABELS  # noqa: F401  (re-exported for route modules)


def _h(v) -> str:
    return html.escape(str(v)) if v not in (None, "") else "Not found"


def checklist_html(notice_title: str, structured: dict, eligibility: dict,
                   readiness: dict, profile: dict, today: date | None = None) -> str:
    today = today or date.today()
    s = structured or {}
    fee = s.get("fee") or {}
    missing_docs = "".join(
        f"<li>{html.escape(m['label'])} — <strong>missing</strong>, add it in your vault</li>"
        for m in readiness.get("missing", []))
    have_docs = "".join(f"<li>{html.escape(m['label'])} — ready</li>" for m in readiness.get("have", []))
    checks = "".join(
        f"<li><strong>{html.escape(c['rule'])}</strong>: {html.escape(c['status'].upper())} — {html.escape(c['detail'])}</li>"
        for c in eligibility.get("checks", []))
    stages = " &gt; ".join(html.escape(x) for x in s.get("selection_stages") or []) or "Not found"
    age = s.get("age") or {}
    name = html.escape(str(profile.get("full_name") or "Applicant"))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>ApplyPilot checklist — {_h(notice_title)}</title>
<style>body{{font-family:system-ui,Arial,sans-serif;max-width:760px;margin:24px auto;padding:0 16px;line-height:1.5}}
h1{{font-size:22px}} h2{{font-size:16px;margin-top:24px}} table{{border-collapse:collapse}} th,td{{border:1px solid #ccc;padding:6px 10px;text-align:left}}
@media print{{button{{display:none}}}}</style></head><body>
<h1>{_h(notice_title)}</h1>
<p>Checklist for <strong>{name}</strong> · Generated {today.isoformat()} · Readiness: <strong>{readiness.get('percent', 0)}%</strong>
{f" · {readiness.get('days_left')} days left" if readiness.get("days_left") is not None else ""}</p>
<button onclick="window.print()">Print / Save as PDF</button>
<h2>Key facts</h2><table>
<tr><th>Organisation</th><td>{_h(s.get("organisation"))}</td></tr>
<tr><th>Last date</th><td>{_h(s.get("last_date"))}</td></tr>
<tr><th>Age limit</th><td>{_h(age.get("min"))} to {_h(age.get("max"))} years{f" (as on {_h(age.get('as_of'))})" if age.get("as_of") else ""}</td></tr>
<tr><th>Qualification</th><td>{_h(QUAL_LABEL.get((s.get("qualification") or {}).get("level"), (s.get("qualification") or {}).get("level")))}</td></tr>
<tr><th>Fee</th><td>{_h(fee.get("currency"))} {_h(fee.get("amount"))}</td></tr>
<tr><th>Selection stages</th><td>{stages}</td></tr></table>
<h2>Eligibility — {html.escape(eligibility.get("verdict", "unknown").replace("_", " "))}</h2><ul>{checks or "<li>No checks available.</li>"}</ul>
<p><em>{html.escape(eligibility.get("disclaimer", ""))}</em></p>
<h2>Documents ready</h2><ul>{have_docs or "<li>None yet.</li>"}</ul>
<h2>Still missing</h2><ul>{missing_docs or "<li>Nothing — you have every document this notice asks for.</li>"}</ul>
<h2>On submission day</h2><ol>
<li>Open the official portal from the notice itself — never from a forwarded link.</li>
<li>Use the Chrome extension to fill the form, then read every field before you submit.</li>
<li>Upload only the photo/signature files produced by Photo Studio and check their KB size.</li>
<li>Pay only through the official portal. Save the payment receipt and the final application PDF/printout.</li></ol>
</body></html>"""


def ics_calendar(applications: list[dict]) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ApplyPilot//Deadlines//EN"]

    def esc(v: str) -> str:
        return v.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    for a in applications:
        if not a.get("deadline"):
            continue
        d = date.fromisoformat(str(a["deadline"]))
        stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        for days_before, label in ((7, "7 days"), (3, "3 days"), (1, "1 day")):
            day = d - timedelta(days=days_before)
            start = datetime.combine(day, time(9, 0))
            lines += [
                "BEGIN:VEVENT", f"UID:applypilot-{a['id']}-{days_before}@applypilot.local",
                f"DTSTAMP:{stamp}", f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{(start + timedelta(minutes=30)).strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{esc('ApplyPilot reminder: ' + str(a['title']) + ' — deadline in ' + label)}",
                f"DESCRIPTION:{esc('Open ApplyPilot, check readiness, and apply before ' + d.isoformat())}",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
