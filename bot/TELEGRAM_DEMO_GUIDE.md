# Telegram Bot — Step-by-Step Testing & Demo Guide

> **Purpose:** Test / demo **every capability** of the ApplyPilot Telegram bot by hand.
> No code changes needed. Send the messages **exactly as written**, in order,
> and compare what the bot replies with **"You should see"**.
>
> ⏱️ Full run: **15–20 minutes**. The checkboxes are your test report — tick them as you pass each step.

---

## 0. Before you start — start the 2 programs

The bot alone does nothing. It needs the **backend** running too. Open **2 terminals**:

**Terminal 1 — Backend (must start first)**

```powershell
cd "E:\Meta AI Hackathon\applypilot\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

Check: open <http://localhost:8000/docs> in the browser — you should see the API list.

**Terminal 2 — Bot**

First confirm your `.env` (repo root: `E:\Meta AI Hackathon\applypilot\.env`) has:

```ini
BOT_TRANSPORT=telegram
TELEGRAM_BOT_TOKEN=<your token from @BotFather>
BOT_SHARED_SECRET=<same value the backend uses — same .env file, so automatic>
BACKEND_URL=http://localhost:8000
```

Then:

```powershell
cd "E:\Meta AI Hackathon\applypilot\bot"
.\.venv\Scripts\python.exe -m applypilot_bot.main
```

You should see the log line: **`Telegram bot started`**. Leave both terminals running.

> **Changed any code or `.env`?** Restart the bot (`Ctrl+C`, run again). A running bot does **not** re-read `.env`.
> **Restarted the backend?** Also restart the bot — clear state comes from a fresh process.

**On your phone:** open Telegram → search your bot's username (the one you created with @BotFather) → open the chat.

---

## 1. First contact (no account linked yet)

| Step | You send | You should see |
|---|---|---|
| 1.1 | `/start` | "Welcome to ApplyPilot!" + instructions to link your account |
| 1.2 | `What is the last date?` | Same linking instructions — **the bot refuses to answer before linking** (try it, this is a security feature) |
| 1.3 | `/help` | Same linking instructions (help is shorter before linking) |

- [ ] Bot replies to every message within ~2 seconds
- [ ] Bot does **not** answer questions before linking

---

## 2. Link your account 🔗

1. On the **website** (<http://localhost:3000>): log in → **Profile** → **Create link code**. Copy the code (valid **10 minutes** only).
2. In Telegram send:

```
/link YOURCODE
```

| Step | You send | You should see |
|---|---|---|
| 2.1 | `/link WRONGCODE` | "Could not link: …" |
| 2.2 | `/link <real code from website>` | **"Linked! Ask me about your notices, or send /help."** |
| 2.3 | `/help` | The **full** help: PDF instructions, photo instructions, command list |

- [ ] Wrong code is rejected
- [ ] Right code links successfully
- [ ] `/help` now shows the full help text

> ⚠️ Link code expired? Just create a new one on the website. Each code works **once**.

---

## 3. The bot with no notices yet

| Step | You send | You should see |
|---|---|---|
| 3.1 | `/notices` | "You have no notices yet. Send me a notice PDF to start." |
| 3.2 | `/deadlines` | "No open applications are due in the next 14 days." |
| 3.3 | `What is the last date?` | An assistant answer saying you have no notices / nothing found (wording depends on AI mode) |

- [ ] All 3 replies are friendly, no errors, no "something went wrong"

---

## 4. Send a notice PDF — the main event 📄

**Prepare:** have one notice PDF ready on your phone. Good choices:
- Any real government-job / scholarship notice PDF, **or**
- Create one quickly: on the website, upload `samples/sample_notice.txt` once, download/print it as PDF — or simply reuse any PDF notice you already have.

**In Telegram:** attach the PDF (📎 → File) and send it **with no caption** (or caption `notice`).

| Step | What happens | You should see |
|---|---|---|
| 4.1 | Immediately after sending | "Got it, reading your notice. I will message you when it is ready." (+ tip about `save` / `compress` captions) |
| 4.2 | Wait ~10–60 seconds (bot polls the backend) | "Your notice is ready: **\<title\>**" + summary lines + "Ask me anything about it…" |
| 4.3 | `/notices` | Your notice in the list, like `#3 SSC Army Post` — **remember this number**, you need it everywhere below |

- [ ] Acknowledgement comes instantly
- [ ] "Notice is ready" message arrives on its own (you don't send anything)
- [ ] `/notices` lists it with a `#number`

> 🐛 **Stuck on "reading your notice"?** Backend terminal 1 must be running. Check it, then re-send the PDF.
> 🐛 **"That file is larger than 5 MB"?** Send it with caption `compress` first (Step 8), or upload it on the website.

---

## 5. Ask questions about the notice 💬

Send these as normal messages, one by one:

| Step | You send | You should see |
|---|---|---|
| 5.1 | `What is the last date?` | The actual last date **from your PDF** |
| 5.2 | `How much is the application fee?` | The fee from the PDF (by category, if the notice has categories) |
| 5.3 | `What documents do I need?` | The document list from the PDF |
| 5.4 | `What photo size do I need?` | Photo pixels/KB from the PDF, if it specifies them |
| 5.5 | `Tell me about quantum physics` | A polite refusal / "not in this notice" — the bot only answers about **your** notices |

- [ ] Answers match the PDF (open the PDF and verify 5.1 and 5.2 yourself)
- [ ] Off-topic question is refused, not answered

> The bot automatically uses your **only** notice. With several notices, first send `/use 3` (Step 7).

---

## 6. Eligibility check ✅

| Step | You send | You should see |
|---|---|---|
| 6.1 | `/eligible` | Either a verdict (below) **or** "Please send your date of birth (DD/MM/YYYY)…" |
| 6.2 | *(only if asked)* `05/08/2004` | "Saved your date of birth as 05/08/2004. Now send /eligible to check." |
| 6.3 | `/eligible` | "Eligibility for notice #\<n\>: **eligible / not eligible / needs info**" + one line per rule, e.g. `- Age: 20 years (needs 18–23)` |

- [ ] If DOB was missing, the bot asked for it, saved it, and the retry works
- [ ] Verdict shows **rule-by-rule reasons**, not just yes/no
- [ ] Change your DOB on the **website Profile** to something outside the age limit → `/eligible` again → verdict flips. (Great judge-demo moment.)

---

## 7. Working with several notices

Send a **second**, different notice PDF (Step 4 again), then:

| Step | You send | You should see |
|---|---|---|
| 7.1 | `/notices` | Both notices listed with `#numbers` |
| 7.2 | `What is the last date?` | The bot may be unsure which notice — that's expected with 2+ notices |
| 7.3 | `/use 3` *(use a real number from 7.1)* | "Okay, I will use notice #3 for your questions." |
| 7.4 | `What is the last date?` | The date from notice **#3 specifically** |
| 7.5 | `/use 99` | An error / not-found style reply (no crash) |

- [ ] `/use` switches the active notice and answers follow it

---

## 8. PDFs — but NOT as notices 🗄️

This tests the caption routing. Same PDF, three different captions = three different behaviours.

| Step | You do | You should see |
|---|---|---|
| 8.1 | Send any PDF with caption `save` | "Saved '\<file\>' to your vault. **I did not read it as a notice**." → check `/notices`: count did **not** increase. On the website **Vault**, the file is there. |
| 8.2 | Send a big photo-scan PDF with caption `compress` | "Compressed: **900 KB → 180 KB** (4 pages, …). Also saved to your vault." + the smaller PDF arrives as a file |
| 8.3 | Send the same PDF with caption `compress 200kb` | Final size ≤ ~200 KB, **or** an honest "I could not reach 200 KB…" with the smallest safe copy |
| 8.4 | Send a certificate **photo as a file** (📎 → File, not Gallery), no caption | Saved to vault (non-PDF files are never read as notices) |

- [ ] `save` never creates a notice
- [ ] `compress` returns a smaller, still-openable PDF (open it and check the pages look right)
- [ ] Compressed copy also appears in the website Vault

> Honest limit: compression shrinks **images inside** PDFs. A pure-text PDF is already tiny and may come back unchanged — the bot says "already optimised".

---

## 9. Photos — resize, compress, backgrounds 🖼️

Send a normal selfie through the **Gallery/Photo** option (not File). Watch the reply carefully — every result is a **preview first**.

| Step | Caption you write | You should see |
|---|---|---|
| 9.1 | *(no caption)* | Preview + report ending with **"Background NOT changed"**. Reply `yes` → final file arrives **as a document** + "Saved to your vault." |
| 9.2 | `resize 200x230` | Report shows size **200x230** ✔. Background unchanged. |
| 9.3 | `compress 50kb` | Report shows file size ≤ 50 KB ✔ |
| 9.4 | `resize 300x400 compress 100kb` | Both checks ✔✔ |
| 9.5 | `photo <N>` *(your notice number)* | Uses the **notice's** photo pixels/KB. Text says "Used notice #N's size/KB rules. **Background NOT changed**…" |
| 9.6 | `photo <N> blue background` | **Now** the background becomes blue. (Compare with 9.5 — this contrast is the whole feature.) |
| 9.7 | On any preview, reply `no` | "Okay, discarded…" — nothing is saved. Reply `yes` on the next one to confirm saving works. |
| 9.8 | Photo of your signature, caption `signature <N>` | Cleaned signature (tight crop, white background, notice size). Reply `yes` to keep. |
| 9.9 | Scanned certificate photo, caption `document` | Cleaned scan (light/shadows flattened), **no** face/background tricks. |

- [ ] 9.1–9.5: background in the returned file is **your original background**
- [ ] 9.6: background actually changed to blue
- [ ] The final file's properties really are the pixels/KB the report claims (check file details on your phone/desktop)
- [ ] `yes`/`no` both work; `yes` file also shows in the website Vault

> 📌 Telegram itself compresses photos sent as "Photo". Bot returns files via **sendDocument** so the exact bytes survive — but the *input* selfie Telegram gives the bot may already be downscaled. For pixel-perfect input, send the photo as **File** with caption `resize 200x230`… it will be saved to the vault instead (Step 8.4) — photo *editing* needs the Gallery path. Test both and see the difference.

---

## 10. Deadlines & reminders ⏰

| Step | You send | You should see |
|---|---|---|
| 10.1 | `/deadlines` | Your tracked applications due in **14 days**: title, last date, days left |
| 10.2 | *(automatic — don't send anything)* | Within an hour of the bot running, **if** an application is due in ≤ 3 days (`REMINDER_DAYS`), you receive: "Reminder: \<title\> closes on \<date\> (N days left)." — **once per day per application**, never repeated the same day |

**To force the reminder demo:** on the website, your tracker deadline must be within 3 days. If no real notice qualifies, demo `/deadlines` (Step 10.1) and explain the reminder rule — do not fake dates in a live notice.

- [ ] `/deadlines` matches the website Tracker
- [ ] (If applicable) reminder arrived once, and not twice in the same day

---

## 11. Unlink & re-link 🔓

| Step | You send | You should see |
|---|---|---|
| 11.1 | `/unlink` | "Your chat is unlinked." |
| 11.2 | `What is the last date?` | Linking instructions again (you're logged out of the bot) |
| 11.3 | `/link <new code from website>` | "Linked!" — everything works again |

- [ ] After unlink, no personal answers are given
- [ ] Re-linking works with a **fresh** code (the old one is already used)

---

## 12. Edge cases worth trying (30 seconds each)

| Try | Expected |
|---|---|
| Send a **sticker** or voice message | Bot ignores it silently (no error, no reply) |
| Send a **6 MB** PDF | "That file is larger than 5 MB…" |
| Send a random big photo with caption `photo 99` (fake notice number) | A clean "something went wrong / not found" style reply, **no crash** — bot keeps working afterwards |
| Ask the same question 15 times very fast | Eventually "You are asking too fast. Please wait a minute." (rate limit) |
| Stop the **backend** terminal, ask a question, restart backend | Error reply while down; bot recovers by itself, no bot restart needed |
| `/eligible` before adding **any** notice | "Which notice? Send /notices, then /use NUMBER." |

- [ ] Bot never crashes, never replies with a raw error/stack trace

---

## 13. The 4-minute judge demo script 🎤

Do it in this order — it's the full story:

1. **`/start` → link live** (have the website Profile tab open). *"The bot only works after you link your own account."*
2. **Send the notice PDF** (no caption). Wait for "ready". *"It read the whole notice — I read zero pages."*
3. Ask **`What is the last date?`** then **`/eligible`**. *"Not general AI answers — checked against the notice and **my** profile, rule by rule."*
4. Send a selfie with caption **`photo <N>`** → point at **"Background NOT changed"** → re-send with **`photo <N> blue background`** → show the change. *"It only does what I asked. Nothing silent."*
5. **`/deadlines`**. *"And it reminds me before I can miss the date."*

Keep a **recorded screen video** of Steps 4–9 as backup. If the hall Wi-Fi dies, the video saves you.

---

## 14. Troubleshooting

| Symptom | Fix |
|---|---|
| Bot never replies at all | Terminal 2 must show `Telegram bot started`. Check `TELEGRAM_BOT_TOKEN` in `.env`. Message the **correct** bot username. |
| "Could not link: …" | Code expired (10 min) or already used → create a fresh code. If it persists, `BOT_SHARED_SECRET` differs between bot and backend — they share the repo-root `.env`, so keep it that way and restart **both**. |
| Every question → "something went wrong" | Backend (Terminal 1) is down or crashed. Restart it; bot recovers automatically. |
| Notice stuck "reading…" | Backend down during ingest → restart backend, re-send the PDF. |
| Photo KB/pixels wrong in the final file | You replied `yes` to the *preview* message but downloaded the preview from the chat photo view — download the **document** the bot sends after `yes`. |
| Reminder never came | Deadline must be ≤ `REMINDER_DAYS` (default 3) away **and** the bot must be running; it checks hourly, once per day per application. |
| Bot answers about the wrong notice | Send `/use <N>` (Step 7). |
| "session ended" | Token expired/was reset → `/link` again with a fresh code. |

---

## 15. Full capability checklist (your test report)

- [ ] Start / help (linked vs unlinked)
- [ ] Link with code, wrong-code rejection, unlink + re-link
- [ ] Notice PDF ingest + "ready" notification
- [ ] Q&A about the notice (dates, fees, documents) + off-topic refusal
- [ ] Eligibility: DOB prompt → save → verdict with reasons
- [ ] `/notices`, `/use`, `/deadlines`
- [ ] PDF `save` (vault only) and `compress [Nkb]`
- [ ] Photo: bare resize, `resize WxH`, `compress Nkb`, notice rules
- [ ] Background changes **only** on explicit ask; preview `yes`/`no`
- [ ] Signature and document-scan captions
- [ ] Deadline reminder (if a deadline is within 3 days)
- [ ] Edge cases: oversize file, sticker, backend-down recovery

**All ticked = the Telegram bot is demo-ready.** 🎉

See also: [`docs/BOT.md`](../docs/BOT.md) (setup reference) and [`DOCUMENT.md`](./DOCUMENT.md) (how the bot code works).
