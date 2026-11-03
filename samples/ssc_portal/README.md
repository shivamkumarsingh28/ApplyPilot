# SSC-Style Sample Portal (FICTIONAL — for ApplyPilot testing)

A realistic Staff Selection Commission–style application page, built **only** to test
the ApplyPilot browser extension (profile autofill + vault document attach) and to demo it.
It is **not** affiliated with SSC or the Government of India, and **nothing on this page is ever sent anywhere**.

## What's on the page

| Part | Contents |
|---|---|
| I. Personal | Candidate name, father's/mother's name, DOB (DD/MM/YYYY), gender, category (UR/OBC/SC/ST/EWS), nationality, mobile, email, alternate mobile, Ex-Serviceman, PwD, identification mark |
| II. Address | Permanent address, city, state (all States/UTs), district, PIN code, correspondence address |
| III. Qualification | Highest qualification, 10th board / roll no / year / %, graduation % / year |
| IV. Post & Centre | Post preferences 1–2 (CGL-style posts), exam centre preferences 1–2, exam medium |
| V. Uploads | Photograph (JPG 20–50 KB), signature (JPG 10–20 KB), 10th marksheet, 12th marksheet, degree certificate, caste certificate, domicile certificate, photo ID proof, birth certificate (each with size hints) |
| Security | Dummy captcha + password (**extension must skip both**), declaration checkbox (**must stay unticked by the extension**) |

## How to open it

```powershell
cd "E:\Meta AI Hackathon\applypilot\samples\ssc_portal"
python -m http.server 5500
```

Open <http://localhost:5500/> in Chrome. (Use http, not `file://` — extensions behave better.)

## How to test the extension on it

1. Start backend (`:8000`) and website (`:3000`). Complete your **Profile** on the website.
2. Upload matching documents to the **Vault** with these Types:
   `photo`, `signature`, `marksheet_10`, `marksheet_12`, `degree`, `caste_certificate`,
   `domicile`, `id_proof`, `birth_certificate`.
3. Click the ApplyPilot extension → sign in → **Scan this page**.
   Expected: name/parents/DOB/category/mobile/email/address/city/state/PIN/qualification/marks are matched;
   captcha, password, declaration checkbox are **not** fillable; Part-V file fields are detected with their document kinds.
4. **Fill selected fields** → review the blue/yellow highlights → verify manually.
5. **Save as Draft** works locally; **Submit** only shows a demo message (it checks the declaration and empty required fields).

Old tiny test form: [`../sample_form.html`](../sample_form.html) (kept for the automated extension tests).
