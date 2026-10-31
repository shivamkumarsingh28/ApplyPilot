# ApplyPilot: Next Phase Plan

**What this document is:** an approach and a plan. It contains no code. You write the code.
**Read it in this order:** 1 Overview, 2 Current state, 3 Problems to fix, 4 Features, 5 Build order.

---

## 1. Overview

The next phase makes WhatsApp and Telegram the main way people use ApplyPilot. The website stays for rare jobs such as building a custom form or reviewing a long document. A user should be able to:

1. Send a notice PDF to the bot.
2. Wait a short time while it is read.
3. Ask any question about that notice and get a sourced answer.
4. Send a photo or signature and get back a file that matches the notice's rules, with the background colour the user chooses.
5. Get an eligibility answer based on the date of birth in their profile.

Everything is also saved to the website, so the user can review it later.

---

## 2. Current state (what already exists)

| Area | Status |
|---|---|
| Notice ingest (PDF/text) | Working. Facts extracted, chunks embedded, key answers made. |
| Question answering | Working, but uses simple word and vector matching. Quality depends on the model. |
| Photo studio | Working for size and KB. Background removal uses OpenCV, which is rough. Background colour is fixed to white or a short list. |
| Eligibility | Working from the profile and extracted rules. Needs a date of birth in the profile. |
| Vault | Stores uploaded files. No link between a file and an application. |
| Login | Email and password only. |
| Extension | Fills text fields from the profile. Cannot attach files. |
| Telegram / WhatsApp | Chat works. Ingesting a PDF is not supported yet. |

---

## 3. Problems to fix first (with the fix for each)

### 3.1 Ingest over chat is slow and can time out
**Why:** reading a PDF, extracting facts, embedding, and answering key questions all happen in one request. On a local model this can take minutes. Telegram and WhatsApp drop long waits.

**Fix:** split the work into a background job.
- The bot replies at once: "Got it, reading your notice. I will message you when ready."
- A worker runs the ingest steps and writes a status: `queued`, `reading`, `indexing`, `ready`, `failed`.
- When the status becomes `ready`, the bot sends the summary and the key answers.
- Use a simple job table in the database first. Move to Redis + RQ or Celery only when there are many users.

### 3.2 Answers are weak on some questions
**Why:** the search is a mix of word overlap and a simple vector. It finds the right page but may miss paraphrases ("cost to apply" vs "application fee").

**Fix, in order of effort:**
1. Keep chunk headings (already done) and search them with extra weight.
2. Add a real embedding model. Options: `nomic-embed-text` through Ollama for local work, or Meta's embedding model through the API if it is offered. Store vectors in **pgvector** on PostgreSQL, not as JSON lists. JSON search reads every row and does not scale.
3. Add a **reranker** step: take the top 12 chunks and let the model pick the best 3. This is the biggest single quality gain for small models.
4. Make the answer prompt strict: answer only from the chunks, quote the page, and say "not found" when unsure.
5. Build a small **evaluation set**: 30 questions with the correct page for each notice. Run it after every change and keep the score. Without this, you cannot tell whether a change helped.

### 3.3 Performance: the model is the slowest part
**Options, from cheap to costly:**
- Use a small local model (Llama 3.2 3B) for routing and short answers.
- Use the larger model (Meta Muse, or Llama 70B on a host) only for the final answer, with the top 3 chunks as input. Short inputs are the cheapest speed-up.
- Cache: store the answer to each (notice, question) pair. The same question twice costs nothing.
- Pre-compute the key answers at ingest, as already done, so common questions are instant.
- Run embedding in batches, not one chunk at a time.
- Measure: log time per step (read, index, retrieve, answer). Improve the slowest one only.

### 3.4 Background removal and colour choice are rough
**Why:** GrabCut needs a good starting box and fails on busy backgrounds. The colour list is fixed.

**Fix:**
- Use SAM 3.1 (or a hosted segmentation model) with a prompt "person". The current code already has an adapter: point `SEGMENTER` at it and test on 20 real photos.
- Keep OpenCV as the fallback and say so in the reply.
- Let the user type any colour in plain words ("light blue", "#e6f0ff"). Convert the name to a hex value in one small table, and accept hex directly. Show a preview and ask "Use this?" before sending the final file.
- Every colour result is checked against the portal rule (for example "white background" must stay white).

### 3.5 Eligibility depends on a date of birth the user may not have entered
**Fix:**
- If the profile has no date of birth, the bot asks once: "Please send your date of birth (DD/MM/YYYY). I keep it private and use it only for age checks." It saves the answer to the profile.
- Never guess an age from a year alone.
- Show the exact age on the notice's "as on" date, and say which rule (general, OBC, SC, ST, ex-serviceman) was applied. If the notice wording on the upper age limit is unclear, show both possibilities.

### 3.6 Login has only email and password
**Fix:** use a standard login library (`Authlib` for Python). Add providers one at a time: Google first (most users), then GitHub, then LinkedIn. Each provider needs its own developer app and its own client ID and secret.
- Accounts are linked by a row in `oauth_accounts`. One person can use several providers.
- The website redirects to the provider, the backend receives the answer, and then gives the browser a one-time login code.
- "Custom" login means your own email, password, and email verification. It stays as the fallback.
- Warning: LinkedIn's sign-in product has limits on which data you can read. Check its current rules before promising "name and photo".

### 3.7 Internet search for job posts
**Important:** Google's Custom Search JSON API is closed to new customers and stops working on 1 January 2027. Do not build on it.

**Options:**
- **Brave Search API:** its own index, returns JSON, has a free tier. A good default.
- **Tavily:** built for AI apps, returns short text snippets with source links.
- **Self-hosted (YaCy):** free, but results are poorer.

**Design:** the search result is shown in a frame. The user can save a result as a notice. The server downloads the page or PDF, runs the same ingest, and marks the source URL. Only allow downloads from a list of trusted domains (government sites, known job boards) to avoid pulling in bad pages.

---

## 4. Features to add

### 4.1 Chat on notices (Telegram and WhatsApp first)

**Workflow**

```
User sends PDF
   -> bot checks it is a PDF/image, size under limit
   -> API creates an ingest job (returns a job id)
   -> worker: read text -> facts -> chunks -> embeddings -> key answers
   -> bot sends status updates ("reading", "ready")
   -> user asks a question
   -> API: guardrail -> retrieve top 12 -> rerank to 3 -> answer with page
   -> bot replies with answer + "page N" + a note to check the official notice
```

**Rules**
- A notice belongs to one user. The bot's question goes to that notice only.
- If the user has several notices, the bot asks which one, or uses the one they chose last.
- Long answers are split into chunks of about 1,000 characters so chat apps do not cut them.

**Acceptance check:** 30-question test set passes at an agreed level, and the first answer arrives in under 10 seconds with the Meta API (state the measured time, not a guess).

### 4.2 Photo and signature by chat

**Workflow:** photo arrives -> bot asks "which notice?" (or uses the last one) -> asks "background colour? (white, light blue, or type any colour)" -> makes a preview -> user says "yes" -> file sent back as a document, and saved to the vault as a copy for that notice.

**Notes**
- Send as a document, not a compressed photo. Chat apps recompress photos and can break the KB limit.
- The reply shows each rule and whether it passed.

### 4.3 Notices saved to the portal

- Every notice has a page on the website: the PDF, the key answers, the eligibility result, the questions asked so far.
- A notice is created from the website, from the bot, or from a search result, and all three show up in the same list.
- Deleting a notice does not delete the vault documents.

### 4.4 Vault: original plus application copies

**Model**
- **Original** (main document): always kept. Uploaded once. Size limit in the first phase: 5 MB per file, 50 MB total per user (change these in settings later).
- **Application copy**: made when the user applies. It is a copy of an original, resized or cropped to that notice's rules, linked to the application number and notice.
- Copies can be deleted without touching the original. Deleting an original asks first and lists the copies that depend on it.

**Application reference:** each application gets a short reference (for example `APP-0007`). Copies show this reference so the user can match a file to an application.

**Steps in the flow**
1. User picks an original in the vault or sends it in chat.
2. User picks a notice (application).
3. The system makes the copy using that notice's rules.
4. The copy is saved with the reference and shown in the application's page.

### 4.5 Eligibility from profile and form

- The eligibility result uses three sources: profile (date of birth, qualification, percentage, category, gender), notice rules (age limit, relaxations, qualification, gender), and the "as on" date.
- Missing data: say what is missing and ask for it in the bot ("send your date of birth").
- Form extraction must not guess. Each extracted rule keeps the page and the exact sentence it came from. If the value is unclear, mark it "please check" rather than fill a number.
- Add a test set of 20 notices with hand-checked answers. Accept the feature only when the test set passes.

### 4.6 Login options
See 3.6. Also: show which providers are enabled (the list comes from settings), and let a user link more than one provider from the profile page.

### 4.7 Extension: vault documents in the popup

**Workflow**
1. The popup loads the user's vault list (names and kinds only, not the files).
2. When a form field asks for a file (photo, signature, marksheet), the popup marks that field.
3. The user picks a file from the list, or drags a file from the popup onto the field.
4. The file is downloaded from the API only when the user picks it, and attached using the browser's file-input method.
5. The user reviews the form and submits it.

**Rules**
- The extension never submits the form.
- Files are fetched with the user's token, held in memory, and dropped after use. They are not stored in extension storage.
- Drag and drop onto a page field needs the file to be attached through the input's `files` property, and a `change` event fired. Test this on a sample form first.
- Sites can block file attachment from scripts. Show a message: "Please attach this file yourself: it is in your downloads now" as a fallback (the file is saved to the downloads folder on request).

---

## 5. Build order (smallest safe steps)

| Step | What | Why first | Done when |
|---|---|---|---|
| 1 | Background job for ingest, plus status messages | Everything else depends on it | A 10-page PDF ingests without a timeout |
| 2 | Evaluation set and timing log | Lets you measure every later change | Score and timings are printed |
| 3 | Better retrieval: pgvector, reranker | Biggest quality gain | Score improves on the evaluation set |
| 4 | Telegram PDF ingest and question chat | Main user path | Works end to end on Telegram |
| 5 | Date-of-birth prompt and eligibility in chat | Users expect it immediately | Eligibility matches the test set |
| 6 | Vault originals, application copies, references | Needed before photo output is saved properly | A copy can be made, listed and deleted |
| 7 | Photo and signature by chat, colour choice, preview | Main visible feature | Colour and size checks pass on 20 photos |
| 8 | WhatsApp: same flow as Telegram | Copies the work in step 4 | Same test steps pass |
| 9 | Notices page on the website | Shows the saved work | Notices from chat appear on the site |
| 10 | Google login, then GitHub, then LinkedIn | Login is the last priority for real use | Each provider logs in and links to the same account |
| 11 | Internet search frame and "save result as notice" | Needs the safe-domain list | Search, save, ingest work |
| 12 | Extension: vault list, file pick, drag | Needs steps 6 and 7 | Attaches a file on the sample form |

---

## 6. Risks and how to reduce them

| Risk | Reduce it by |
|---|---|
| Model gives a wrong date or age | Facts come from rules first; show the page; "please check" flags |
| User sends a very large PDF | Size limit (5 MB), page limit, clear message |
| Chat apps block or rate-limit the bot | Queue replies; keep messages short; respect limits |
| Personal data in chat history | Tell users not to send ID numbers; delete chat files after ingest if not needed |
| Background removal fails on a photo | Show the preview; keep the original; let the user try again |
| Login provider changes its rules | Keep one module per provider so one change is one file |
| Extension cannot attach a file on some sites | Fallback message and save-to-downloads option |
| Costs grow with model use | Caching, short prompts, small model for routine steps |

---

## 7. What to measure (so you know it is better)

- Ingest time per page, split into read, index, key answers
- Answer time from question to reply
- Answer score on the 30-question set
- Photo check pass rate on 20 test photos
- Eligibility match rate on 20 hand-checked cases
- Number of failed jobs and why

Keep these in a simple table after each change.

---

## 8. Decisions you need to make

1. **Embedding and answer model:** Llama locally for development, and Meta Muse for production. Confirm the Meta API offers embeddings before you rely on them.
2. **Database for vectors:** move to PostgreSQL with pgvector now, or after step 3? (Recommended: at step 3.)
3. **File size limits:** the 5 MB per file and 50 MB per user figures above are a starting point.
4. **Search provider:** Brave or Tavily.
5. **Login:** which providers to launch with. Recommended: Google and email first.
6. **Retention:** how long to keep uploaded notice PDFs and chat images.

---

## 9. Reference files in this project

When you start a step, read these files first:

| Step | Read first |
|---|---|
| 1 Background ingest | `backend/app/services/notice_service.py`, `backend/app/api/routes/notices.py` |
| 3 Retrieval | `backend/app/services/rag.py`, `backend/app/services/embeddings.py`, `backend/app/db/models.py` |
| 4 Telegram chat | `bot/applypilot_bot/core.py`, `bot/applypilot_bot/transports/telegram.py` |
| 5 Eligibility | `backend/app/services/eligibility.py`, `backend/app/services/profile_store.py` |
| 6 Vault | `backend/app/api/routes/documents.py`, `backend/app/services/storage.py` |
| 7 Photo | `backend/app/services/photo_studio.py`, `backend/app/services/segmenter.py` |
| 10 Login | `backend/app/api/routes/auth.py`, `backend/app/core/security.py` |
| 12 Extension | `extension/popup.js`, `extension/lib/filler.js` |

Start each step with its acceptance check written down, then write the test before the code.
