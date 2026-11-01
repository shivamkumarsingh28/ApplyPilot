# ApplyPilot Plan V2: Model, RAG and Tool Calling

**What this is:** a plan only. No code. You build it, one step at a time.
**Goal:** answers that are right, numbers that are right, eligibility that is right, and a chat that shows how the answer was made.

---

## 1. Your problems, and the real cause of each

| What you see | Most likely cause | Main fix (section) |
|---|---|---|
| Answers are not accurate | The model gets the wrong text, or too little of it. Small local models also make more mistakes. | Use the Meta model for everything, read the whole notice when it is short, and check every answer against the page (5, 6) |
| Calculations are wrong | A language model is asked to do arithmetic. It guesses. | All arithmetic moves into plain code tools. The model only calls them (7) |
| Eligibility tool calling is weak | Tool descriptions are vague, inputs are missing, and the rules are stored as loose text | Rebuild eligibility with structured rules, clear tool definitions and a question flow for missing inputs (7) |
| RAG quality is low | Search is simple and the vectors are weak | Hybrid search, a stronger embedding model, reranking (6) |
| No "right question, right answer" store | Every question is answered from scratch | A saved question-and-answer store per notice, with checked answers (8) |
| Chat does not show supervisor, agent, tool steps | The steps run on the server and are never sent to the screen | A step trace sent with every answer (9) |
| Every user uploads the same PDF | Each upload makes a private copy | A shared notice library with one copy per notice (10) |
| Rules change over time | One fixed copy of the facts | Versions of each notice with dates (11) |

---

## 2. Rules for this phase

1. **Facts come from the document. Maths comes from code. The model writes the words.**
2. **No answer without a page.** If the model cannot point to a page, it says "not found".
3. **Measure first.** Build the test set before you change anything (section 4).
4. **One change at a time.** Run the test set after each one and keep a score table.
5. **Keep private data private.** Only public notices are shared. Profiles, documents and chats never are.

---

## 3. Use the Meta API for development too

You have an API key, so use it for both local testing and production. Keep Llama as an optional backup, not the main path.

**What Meta's documentation says (checked today, verify before you rely on it):**
- Models: `muse-spark-1.1` and `muse-spark-1.2`, both on the Standard tier. Context is about 1 million tokens. Input can be text, image and PDF.
- It supports native tool calling (including several calls at once), structured output that follows a JSON schema, a "reasoning effort" setting, prompt caching and token counting.
- Only `auto` and `none` are listed for tool choice. You cannot force a specific tool, so design around it (section 7).
- I did not find an embeddings endpoint in Meta's list of endpoints (Responses, Chat completions, Messages, Files, Models). Plan to use a separate embedding model. Please confirm in Meta's docs or with their support.
- A third-party doc reports prices of about $1.25 per million input tokens, $0.15 per million cached input tokens and $4.25 per million output tokens for Standard. Check Meta's own pricing page.
- There is also a cheaper "Contributor" tier. It appears to let Meta use your prompts. **Do not use it with real user documents** unless Meta's terms say otherwise.

**How to set up development so it does not waste tokens**
- Use three settings: **development** (Meta API, low reasoning effort, small token limits, daily budget cap), **test** (recorded answers, no API calls), **production** (Standard tier, normal limits).
- **Record and replay:** the first time a test runs, save the model's reply to a file. Next time, use the saved reply. Tests then cost nothing and give the same result each time.
- Log tokens and time for every call. Show a daily total.
- Handle "too many requests" with waiting and retrying, and show a friendly message to the user.
- Keep one place that decides which model and which reasoning effort each task uses (section 5.4).

---

## 4. Step zero: build the test set (evaluation)

You cannot improve what you cannot measure. This is the most important step.

**Build it**
- Pick 30 real notices: different organisations, some scanned, some in two languages, some with tables.
- For each notice write 15 questions people really ask (last date, fee, age, qualification, documents, photo size, selection stages, vacancies, salary, how to apply, and some questions whose answer is "not in the notice").
- For each question write the correct short answer and the page number. Do this by hand. This is the "golden set".
- Add 30 eligibility cases: a person's date of birth, category, qualification and marks, and the right answer with reasons.
- Add 20 calculation cases: age on a date, days left, age with relaxation, fee totals.

**What to score**

| Measure | Meaning | Proposed starting target (agree and adjust) |
|---|---|---|
| Retrieval hit | The right page is in the top 3 results | 90% or more |
| Answer correct | Matches the golden answer | 90% or more |
| Citation correct | The page cited really holds the answer | 95% or more |
| "Not found" correct | Says not found when it is not in the notice | 95% or more |
| Eligibility correct | Same verdict and same reasons | 100% on the arithmetic cases |
| Calculation correct | Exact number | 100% |
| Speed | Time to first reply, middle and slowest 10% | Set after the first measurement |
| Cost | Tokens per answer | Set after the first measurement |

**Judging answers:** use a script for exact facts (dates, numbers). For free text, use a second model call as a judge, and check 10% by hand to be sure the judge is fair.

**Rule:** a change is only accepted if the score table does not go down.

---

## 5. Better understanding of the document (ingest)

### 5.1 Read the notice better
- Digital PDFs: keep text, but also keep **tables** as rows (a fee table must stay a table).
- Scanned or messy PDFs: send the page to the Meta model as an image or PDF page and ask it to rewrite it as clean text with tables.
- Two languages in one notice (for example Hindi and English): keep both and mark the language of each part.
- Keep the page number and section heading for every piece of text.

### 5.2 Read the whole notice when it is short
Meta's context window is about one million tokens. A normal notice is far smaller. So for **one notice at a time**, give the model the **whole text** instead of a few pieces. This removes "the right piece was not found" errors.
- Use prompt caching: the notice text is the same for every question, so it costs far less after the first question (confirm the cache rules and time limit in Meta's docs).
- Ask the model to quote the sentence and the page that supports each answer, then check that the quote really exists in the text. If it does not, reject the answer.
- Use search (RAG) when you search **across many notices** or when a document is too long.

### 5.3 Extract facts with proof
- Ask for facts in a fixed JSON shape (Meta supports schema-checked output).
- Each fact carries **the quote and the page** it came from.
- Check each fact with simple code: dates are real dates, the last date is after the start date, minimum age is below maximum age, fee is a number.
- Run extraction twice with different wording or settings. If the two runs disagree on a fact, mark it "please check" instead of choosing one.
- Keep the rule-based extractor as a cross-check, not as the only source.

### 5.4 Which model for which job

| Job | Suggested setting |
|---|---|
| Rewrite scanned pages | Strong model, low effort |
| Fact extraction | Strong model, medium effort, schema output, temperature low |
| Choosing the agent (supervisor) | Cheapest suitable setting, short prompt |
| Question answering with the whole notice | Medium effort, cached notice |
| Checking an answer against its quote | Low effort or plain code |
| Judging test answers | Medium effort |

Test each choice on the golden set before you accept it.

---

## 6. Better search (RAG, embeddings, semantic search)

### 6.1 Keep the structure
- Chunk by section and keep the heading with every chunk.
- Keep a short chunk for matching and a larger "parent" block for the answer, so the model sees the rule and its exceptions together.
- Keep each table row as its own chunk, with the column names repeated.

### 6.2 A better embedding model
Today the vectors are made by a simple built-in method. Replace it.
- Choose one embedding model that handles English and Hindi (and other languages you need). Compare two or three on your golden set. Pick by score, not by reputation.
- Candidates to test: a multilingual open model you host yourself, or a hosted embedding service from another provider. Confirm Meta's position on embeddings first (section 3).
- Re-embed everything when you change the model, and store the model name with each vector so you never mix two models.
- Store vectors in **PostgreSQL with pgvector**, not in a JSON column. Add the vector index.

### 6.3 Hybrid search
Run two searches and merge them:
1. **Meaning search** (vectors).
2. **Keyword search** (Postgres full-text search). This is excellent for exact words, numbers and abbreviations such as "OBC" and "Rs".
Merge with a simple "reciprocal rank" rule: items that rank high in both lists win.

### 6.4 Rewrite the question
- Turn a short chat message into a clear search query ("how much" becomes "application fee amount").
- For a hard question, make two or three versions of the query and merge the results.
- Add the section type as a filter when the question is clear (fee, age, documents).

### 6.5 Rerank
Take the top 15 results and score each against the question with a **reranker** (a small model made for this, or one model call). Keep the best 3 to 5. This usually gives the largest quality gain.

### 6.6 Say "not found" correctly
- Set a score cut-off using the golden set, including the "not in notice" questions.
- If the best result is below the cut-off, answer "not found in this notice" and offer to check the official site.

### 6.7 Check the answer
After the answer is written, run a quick check: "Is every claim supported by the quoted text?" Remove or fix any claim that is not.

---

## 7. Calculations and eligibility (tool calling)

### 7.1 Never let the model calculate
Create a small set of calculator tools, each with one job:
- Age on a given date (years, months, days)
- Days between two dates and days left to a deadline
- Age limit with relaxation, using the notice's own rule for stacking
- Fee total
- Percentage and marks checks

Every tool returns the answer **and its working** (for example "born 10 March 2007, as on 1 October 2026 = 19 years 6 months 21 days"). The chat shows the working.

### 7.2 Eligibility as structured rules
- Store each rule as data: what it checks, the allowed values, the date it applies on, which categories it applies to, the page it came from.
- Store relaxations as a table: category, years, whether they can be added to others.
- Store the "as on" date and the exact wording of the age rule.
- If a rule is unclear, mark it "needs a person to confirm". Show both readings (for example "up to 21 years" meaning before the 21st birthday, or on it).
- The eligibility tool reads these rules and the user's profile. It never reads the free text.

### 7.3 Ask for what is missing
When something is missing (date of birth, category, marks), the tool does not guess. It returns a list of what is missing. The assistant then asks the user for each item in the chat, saves the answer to the profile, and runs the check again. This is a short question-and-answer loop.

### 7.4 Clear tool definitions
Meta supports native tool calling, so use it instead of the home-made JSON method.
- Give each tool a clear name, a one-sentence purpose, and a "use this when / do not use this when" note.
- Mark required inputs. Use fixed lists (enums) where a value has only a few choices (category, qualification).
- Keep the number of tools per agent small (under 8).
- Because you cannot force a tool choice, add checks in code: if the question is about eligibility and no eligibility tool was called, send the model back with a reminder, once.
- Return tool errors in plain, teaching words ("date of birth is missing, ask the user for it").
- Limit steps (for example 4 per question) and stop loops.
- Allow several independent tool calls at once (for example age and days left) to save time.

### 7.5 Test it
Run the 30 eligibility cases and 20 calculation cases on every change. All arithmetic cases must pass.

---

## 8. A question-and-answer store ("right question, right answer")

**Idea:** save good answers so common questions are instant, cheap and consistent.

**What it holds (per notice version):** the question, the answer, the page, the date made, who or what checked it, how many times it was used, and the rating.

**How it is filled**
1. The standard key questions made at ingest (fee, last date, age, documents, and so on).
2. Real user questions that were answered well (thumbs up).
3. Answers checked by an admin, marked "verified".

**How it is used**
1. A new question is turned into a vector and compared with the stored questions for that notice version.
2. If the match is very close, return the saved answer with its page, and tell the user it came from the checked store.
3. If not, answer normally with search and save the new pair as "unchecked".

**Keep it honest**
- Thumbs-down or "this is wrong" moves the answer out of the store and adds the question to the golden set.
- When a notice gets a new version (section 11), saved answers for the old version stay, but are not used for the new one until they are re-checked.
- Show a label: "checked", "unchecked", or "made just now".

---

## 9. Show the steps in the chat

**What the user should see** (a small "How I answered" line under each answer, opened with a tap):

1. Safety check: passed (or blocked, with the reason)
2. Supervisor chose: eligibility agent, because the question is about eligibility
3. Agent used: age tool (result with working), eligibility rules tool (result)
4. Sources: notice page 2, version of 12 Oct
5. Time and checked status

**How to build it (approach)**
- The server records every step as an event: step type, name, short result, time taken, tokens used.
- On the website, send events live as they happen (server-sent events) so the user sees "thinking, checking rules, writing".
- In Telegram and WhatsApp, send one short line at the end ("I used the eligibility tool and notice page 2"). Do not send many messages.
- Store the events with the turn so an admin can replay what happened.
- Do not put private values in the trace (for example the full date of birth). Show "date of birth from your profile".
- Add a button "Was this right? Yes / No". This feeds section 8 and the golden set.

---

## 10. A shared notice library

**Why:** a public notice is the same for everyone. One copy should be read, indexed and checked once, then used by all users.

**How it works**
1. A user uploads a PDF or a link.
2. The system computes a **fingerprint** of the file (a hash of the exact file, and a second one of the cleaned text to catch the same notice saved differently).
3. If the fingerprint is already known, the user is **linked** to the existing notice. There is no new reading, chunking or embedding. The user gets the answers at once.
4. If it is new, the full ingest runs, and the notice enters the library.
5. For near-duplicates (a corrected version, a slightly different file), compare meaning and the source address. If it looks like a new version of a known notice, create a **new version** (section 11), not a new notice.

**What is shared and what stays private**

| Shared (same for everyone) | Private (per user) |
|---|---|
| The notice text, pages, chunks, vectors | Profile and date of birth |
| Extracted facts and their quotes | Eligibility result for this person |
| Key answers and the checked question store | Chat history |
| Source address, versions, safety score | Documents and application copies |
| | Which notices the user saved or hid |

**Trust and safety (important, because one bad upload would reach many people)**
- A new notice starts as **"user uploaded, not verified"**. Show this label.
- It becomes **"verified"** when it comes from an official domain, when an admin approves it, or when several independent users uploaded the identical file and the safety check is clean.
- Run the safety check (fake-notice signs, text that tries to command an AI) before anything is shared. If it fails, keep it private to the uploader and flag it for review.
- **Privacy check:** a file that looks personal (a marksheet, an ID, a filled form) must never enter the library. Detect it, keep it private, and explain why.
- Ask for consent in the upload screen: "This looks like a public notice. Share it with other users?"
- Add "report this notice". An admin can hide a notice for everyone and notify the people who used it.
- Keep the uploader's name out of the library. Store only a count.

---

## 11. Notice versions and dates

Rules change: the last date is extended, a corrigendum changes the age limit, a vacancy count is updated.

**Model**
- A **notice** has many **versions**. Each version has a type (original, corrigendum, extension, cancellation), a date it takes effect, its own text, chunks, facts and answers.
- The "current" version is the newest one that has taken effect.
- Eligibility and answers always use the current version, and the reply says which version it used ("based on the notice of 12 October, updated 3 November").
- Old versions are kept so a user can see what changed and what they applied under.

**Keeping versions fresh**
- If the notice has a source address, check it on a schedule (for example once a day while the notice is open, less often after).
- If the file changed, make a new version, compare it with the old one, and list the changes in plain words.
- Tell every user who saved that notice, in Telegram or WhatsApp: "The last date changed from 14 Nov to 21 Nov."
- After the deadline passes, archive the notice. Keep it readable but stop reminders.

---

## 12. Speed and cost

- Cache by (notice version, question). Same question, same answer, no model call.
- Use prompt caching for the notice text.
- Keep prompts short: send only what the task needs.
- Run independent work at the same time (embedding batches, parallel tool calls).
- Use a lower reasoning effort for simple tasks and a higher one only when the test set shows it helps.
- Stream the answer on the website so it feels fast.
- Run ingest as a background job and message the user when it is ready.
- Put a daily token budget per environment and per user, with a clear message when it is reached.

---

## 13. Safety updates for a shared library

- Scan every notice for text that tries to give orders to an AI **before** sharing. A poisoned notice would affect all users.
- Tell the model that notice text and tool results are data, never instructions (already done; keep it).
- Keep the rule that tools only read the current user's data. Add tests that user A cannot see user B's chat, profile, documents or application copies even though they share a notice.
- Rate-limit uploads and searches per user.
- Keep an audit record of who shared, reported or hid a notice.

---

## 14. Data to add (in words)

| New or changed | Holds |
|---|---|
| Notice (shared) | Fingerprints, source address, trust level, who verified, status |
| Notice version | Version type, effective date, text, hash, facts with quotes, change summary |
| Chunk (per version) | Text, page, heading, parent block, vector, embedding model name, search text |
| User-notice link | User, notice, title the user chose, hidden or saved, which version they last saw |
| Question and answer store | Question, vector, answer, page, version, checked status, uses, rating |
| Trace | User, turn, steps, times, tokens, safety result |
| Evaluation | Cases, runs, scores, differences between runs |
| Jobs | Ingest job status, progress, errors |
| Eligibility rules | Structured rules, relaxations, as-on dates, page references |

---

## 15. Build order

| Step | Work | Done when |
|---|---|---|
| 1 | Meta API as the main model, three environments, token log, record and replay | Dev runs on Meta; tests make no API calls |
| 2 | Golden set and scoring script | Baseline score table exists |
| 3 | Whole-notice answering with quotes and quote check | Answer score improves over baseline |
| 4 | Facts with quotes, double run, code checks | Fact accuracy shown on the set |
| 5 | Calculator tools and eligibility rules (structured) | 100% on arithmetic cases |
| 6 | Native tool calling, missing-input questions, code checks | Eligibility cases pass |
| 7 | Step trace on website and chat footer, feedback buttons | Every answer shows its steps |
| 8 | Embedding model comparison, pgvector, hybrid search, rewrite, rerank | Retrieval hit meets target |
| 9 | "Not found" cut-off and answer check | "Not found" cases pass |
| 10 | Question-and-answer store | Repeat questions answered from the store |
| 11 | Shared library with fingerprints, trust levels, privacy check | Same PDF from two users is stored once |
| 12 | Versions, change detection, user messages | A changed last date reaches the user |
| 13 | Speed and cost tuning | Speed and cost targets met |

Record the score table after every step.

---

## 16. Risks

| Risk | Reduce it by |
|---|---|
| Model still gives a wrong fact | Quotes, quote check, double run, "please check" flag |
| One bad shared notice harms many | Trust levels, scans, reports, takedown, notify users |
| Personal documents shared by mistake | Detection before sharing, consent, private by default |
| Embedding change breaks old data | Store model name; re-embed in a planned job |
| API cost grows | Caches, prompt caching, budgets, lower effort where safe |
| Provider limits or outages | Retry, wait, queue, optional backup model |
| Version mix-ups | Always show the version used; keep dates on everything |
| Test set gets old | Add every reported wrong answer to it |

---

## 17. Decisions needed from you

1. **Embedding model:** which to test first. (Confirm whether Meta offers one.)
2. **Contributor tier:** do not use for user documents, agreed?
3. **Library trust:** who may publish to everyone? Suggested: official source or admin approval or repeated identical uploads.
4. **Consent wording** for sharing public notices.
5. **Retention:** how long to keep notice files and traces.
6. **Targets** in section 4: accept or change.
7. **Languages** to support first besides English.

---

## 18. Files to read before each step

| Step | Read first |
|---|---|
| 1 | `backend/app/services/llm/` (provider layer), `backend/app/core/config.py` |
| 3, 4 | `backend/app/services/extraction.py`, `backend/app/services/rag.py`, `backend/app/services/notice_service.py` |
| 5, 6 | `backend/app/services/eligibility.py`, `backend/app/services/agents/tools.py`, `backend/app/services/agents/runner.py` |
| 7 | `backend/app/services/agents/assistant.py`, `backend/app/api/routes/assistant.py`, `frontend/app/assistant/page.tsx` |
| 8, 9 | `backend/app/services/embeddings.py`, `backend/app/services/chunking.py`, `backend/app/db/models.py` |
| 10 | `backend/app/services/key_questions.py` |
| 11, 12 | `backend/app/api/routes/notices.py`, `backend/app/services/scam_check.py`, `backend/app/services/guardrails.py` |

Write the test before the change, run the score table after it.
