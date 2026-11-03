# ApplyPilot: UI/UX Design Specification

**What this is:** a complete design document for the website. You give it (or one section of it) to your Meta model and it generates the screens. Section 13 has ready-to-paste prompts.
**Who it is for:** students and young job seekers, mostly on a phone, often on a slow connection, many in a second language.
**Design goal:** a person who has never used the app can finish their first task (read a notice and see if they are eligible) in under 3 minutes, without asking anyone.

---

## 1. Design principles

1. **Phone first.** Design for a 360 px wide screen. The desktop is the phone layout with more room.
2. **One main action per screen.** Every screen has one obvious primary button.
3. **Guide, do not assume.** Every empty screen says what to do next and why. Every step says how long it takes.
4. **Show the proof.** Every answer shows its page. Every eligibility result shows its reasons. This builds trust.
5. **You stay in control.** The app never submits a form, never deletes without asking, and always shows a preview.
6. **Plain words.** Reading level of a 14-year-old. No jargon on screen ("RAG", "embedding", "agent" never appear to users).
7. **Fast and forgiving.** Show progress for slow jobs. Allow undo. Save as the user types.
8. **Chat is a first-class home.** Telegram and WhatsApp are main channels, so the website must teach people to use them.

---

## 2. Users and their jobs

| Person | Main job | What worries them |
|---|---|---|
| Student, 18 to 25, phone only | "Can I apply? What do I need? By when?" | Missing the deadline, wrong photo size, fake notices |
| First-time applicant | "I don't know where to start" | Not understanding the form or the notice |
| Repeat applicant | "I apply to many posts, stop making me retype" | Time wasted on the same data and files |
| Helper (cyber cafe, teacher, sibling) | Applies for several people | Mixing up people's files |
| Admin | Keep the library clean and safe | Fake notices, abuse |

---

## 3. Site map

**Public (no login)**
- Home (landing page)
- How it works
- Features
- Safety and privacy
- Help centre (articles: first steps, connect Telegram, connect WhatsApp, install the extension, photo rules, FAQ)
- Sign up, Log in, Forgot password, Verify email

**App (after login)**
- Home (dashboard with setup checklist)
- Assistant
- Notices (list, add, notice detail)
- Photo studio
- Vault (documents)
- Tracker (applications)
- Chat apps (connect Telegram, connect WhatsApp)
- Browser extension (install and use)
- Profile
- Settings (language, privacy, sign-in methods, delete account)
- Help (always available)
- Admin (admins only)

**Navigation**
- Phone: bottom bar with 5 items: Home, Assistant, Notices, Vault, More. "More" holds Photo studio, Tracker, Chat apps, Extension, Profile, Settings, Help.
- Desktop: left sidebar with the same items plus Photo studio and Tracker as direct links.
- A floating "Help" button on every app screen opens a side drawer with help for this screen.

---

## 4. The first-time journey

```
Landing -> Sign up -> Verify email -> Welcome -> Quick profile (3 steps)
   -> Add first notice -> See result (facts, safety, eligibility)
   -> Fix photo -> Connect Telegram/WhatsApp -> Install extension -> Done
```

### 4.1 The setup checklist (the backbone of onboarding)

It sits at the top of the Home screen until all steps are done, then collapses into a small "Setup complete" badge.

| Step | Time | Why it matters (shown to the user) | Finished when |
|---|---|---|---|
| 1. Add your basics | 1 min | "We need your date of birth and qualification to check if you can apply." | DOB, category, qualification saved |
| 2. Add your first notice | 1 min | "Upload a notice PDF or paste its text. We read it for you." | One notice ready |
| 3. Fix your photo and signature | 2 min | "Get files that match the portal's rules." | One photo copy saved |
| 4. Connect Telegram or WhatsApp | 1 min | "Ask questions and get reminders in your chat app." | Chat linked |
| 5. Install the browser extension | 2 min | "Fill forms in one click. You review everything." | Extension signed in (optional) |

The checklist is skippable but always reachable. Each step opens the right screen with a short "What you will do here" card.

### 4.2 Time to first value
A new user should see their first notice result within 3 minutes of signing up. Offer a **sample notice** button ("Try with a sample notice") so people can see the result before they upload anything.

---

## 5. Design system

### 5.1 Colour tokens

Based on the logo. I tested the contrast of each pair. A ratio of 4.5 or more is needed for normal text (WCAG AA).

| Token | Value | Use | Contrast check |
|---|---|---|---|
| primary | #2f5bea | Buttons, links, active items | White text on it: 5.52 (pass). On white: 5.52 (pass) |
| primary-dark | #1d3fb5 | Button hover, pressed | White on it: 8.64 (pass) |
| primary-soft | #e8eefc | Selected rows, info boxes | |
| ink | #1b1f2a | Main text | On white: 16.46 (pass) |
| muted | #5b6475 | Secondary text | On white: 5.96 (pass) |
| line | #e4e7ee | Borders and dividers | |
| page | #f6f7fb | Page background | |
| surface | #ffffff | Cards | |
| success | #157f4b | Success text and buttons | White on it: 5.04 (pass) |
| success-soft | #e7f6ee | Success background | Success on it: 4.51 (pass, barely) |
| warning | #a15c00 | Warning text | On #fff4e0: 4.76 (pass) |
| warning-soft | #fff4e0 | Warning background | |
| danger | #b42318 | Errors, delete | On white: 6.57 (pass) |
| danger-soft | #fdecea | Error background | Danger on it: 5.75 (pass) |

**Fix to know about:** the logo's green (#22a06b) with white text is only 3.33, which fails. Use it only for the logo graphic and large icons. Use `success` (#157f4b) for text and buttons.

Colour is never the only signal. Every status has an icon and a word (for example a check icon plus "Eligible").

**Dark theme (optional, phase 2):** page #0f172a, surface #172036, ink #e8efff, primary #7aa2ff. Re-check contrast before shipping.

### 5.2 Type
- Font: Inter, with system fonts as fallback. For Hindi and other scripts, add Noto Sans for that script.
- Scale (px): 12, 14, 16 (body), 18, 20, 24, 32, 40. Line height 1.5 for body.
- Body text is never below 16 px on phone. Small text (12 to 14) is only for hints and labels.
- Headings: one H1 per page.

### 5.3 Space and shape
- 4 px grid. Common gaps: 8, 12, 16, 24, 32.
- Corner radius: 8 for inputs and buttons, 12 for cards, 999 for chips.
- Touch targets are at least 44 by 44 px.
- Card shadow: very light (0 1 3 rgba(16,24,40,.08)). Do not stack shadows.

### 5.4 Components (each needs: default, hover, focus, disabled, loading, error)

| Component | Notes |
|---|---|
| Button | Primary (blue), secondary (white with border), danger (red), text link. Loading shows a spinner and keeps the width. |
| Input, select, textarea | Label above, hint below, error text below in red with an icon. Never use placeholder as a label. |
| Provider button | "Continue with Google", "Continue with LinkedIn", "Continue with GitHub", "Continue with phone". Same size, brand icon left. |
| Card | Title, body, optional action. |
| Status chip | Eligible, Not eligible, Needs info, Safe, Check carefully, High risk, Verified, Unverified. Icon plus word. |
| Stepper / checklist | Numbered steps with done, current, upcoming. |
| Empty state | Icon, one line of what this is, one line of why it helps, one primary button. |
| Toast | Short confirmation at the bottom. Has an Undo for deletes. |
| Dialog | For confirmations. Names the thing being deleted. Cancel is the default focus. |
| Drawer | Help panel on the right (desktop) or bottom sheet (phone). |
| File drop zone | Click, drag, or camera on phone. Shows allowed types and size. |
| Progress | Bar for known work, spinner with text for unknown. Long jobs show steps ("Reading", "Indexing", "Ready"). |
| Citation chip | "Page 2". Opens the page with the sentence highlighted. |
| Trace panel | Collapsible "How I answered" (see 8.4). |
| Copy field | Shows a code with a Copy button and "Copied". |

**Recommendation for implementation:** keep Next.js and add Tailwind CSS with shadcn/ui (built on Radix). It gives accessible dialogs, drawers, tabs and menus, and AI models write it well. Put the tokens above in one theme file so every screen uses the same values.

---

## 6. Screen specifications

For each screen: **Purpose**, **Layout**, **Key content**, **Primary action**, **States**, **Notes**.

### S1. Home (public landing page)

**Purpose:** in 10 seconds the visitor understands the problem and the promise, and in 30 seconds sees how it works.

**Sections, top to bottom**
1. **Header:** logo, links (How it works, Features, Safety, Help), "Log in", "Get started" (primary).
2. **Hero:** headline, one sentence, two buttons, one picture (a phone showing a notice result).
   - Headline: "Stop losing chances to paperwork."
   - Sub: "ApplyPilot reads job and exam notices, tells you if you can apply, fixes your photo and signature, and fills the form. Right in Telegram, WhatsApp or your browser."
   - Buttons: "Get started free" (primary), "See how it works" (secondary, scrolls down).
   - Under the buttons: "Free and open source. Your files are encrypted."
3. **The problem (3 cards):** "A 40-page notice nobody reads", "A photo rejected by 2 KB", "The same form, typed again and again".
4. **How it works (4 steps with pictures):** 1 Send the notice. 2 Check your eligibility. 3 Fix your photo and signature. 4 Fill the form, you press submit.
5. **Features (6 cards):** Notice reader with page proof, Eligibility with reasons, Fake-notice warning, Photo and signature studio, Browser autofill, Telegram and WhatsApp assistant.
6. **Use it where you are:** three tiles: Website, Telegram, WhatsApp (marked "coming soon" if not live), Browser extension. Each has a one-line "how".
7. **Safety and privacy strip:** "Only you can see your files." "We never submit your form." "We never ask for ID numbers." Link to the Safety page.
8. **FAQ (6 items):** Is it free? Is my data safe? Which countries? Does it work in my language? Does it submit forms? Which model do you use?
9. **Final call to action** and footer (Help, GitHub, Privacy, Terms, Contact).

```
+----------------------------------------------------+
| [logo ApplyPilot]   How  Features  Safety  Help  [Log in] [Get started] |
+----------------------------------------------------+
|  Stop losing chances to paperwork.      [phone mock]|
|  Reads notices, checks eligibility,                 |
|  fixes photos, fills forms.                         |
|  [Get started free]  [See how it works]             |
|  Free, open source. Files encrypted.                |
+----------------------------------------------------+
|  The problem:  [40 pages] [photo rejected] [retyping]|
+----------------------------------------------------+
|  How it works: 1 Send  2 Check  3 Fix  4 Fill      |
+----------------------------------------------------+
|  Features (6 cards)                                  |
|  Use it where you are: Web | Telegram | WhatsApp | Extension |
|  Safety strip  |  FAQ  |  Final CTA  |  Footer      |
+----------------------------------------------------+
```

**Notes:** the page must load fast on a slow phone (under 150 KB of images above the fold). No auto-playing video.

### S2. How it works (public page, also a section of S1)
A numbered vertical workflow with a small picture for each step and a "Try it" link:
1. Create an account (30 seconds).
2. Add your basics so we can check eligibility.
3. Send a notice by website, Telegram or WhatsApp.
4. Read the facts, safety result and eligibility.
5. Ask questions and see the page for every answer.
6. Fix your photo and signature to the notice's rules.
7. Connect the chat app for reminders.
8. Install the extension and fill the form. You check and submit.

### S3. Sign up and log in

**Purpose:** get in fast, with the method the person already trusts.

**Layout:** one centred card, same screen for both with a switch ("New here? Create an account" and "Have an account? Log in").

**Order of options**
1. Continue with Google
2. Continue with LinkedIn
3. Continue with GitHub
4. Continue with phone (WhatsApp or SMS code) *(see note)*
5. Divider "or use email"
6. Email, password, "Log in" or "Create account"
7. "Forgot password?"

```
+---------------------------------+
|        [logo]                    |
|  Create your account            |
|  [G] Continue with Google        |
|  [in] Continue with LinkedIn     |
|  [gh] Continue with GitHub       |
|  [phone] Continue with phone     |
|  -------- or use email --------  |
|  Name  [____________]            |
|  Email [____________]            |
|  Password [_________] (show)     |
|   At least 8 characters          |
|  [Create account]                |
|  Already have an account? Log in |
|  By continuing you agree to the  |
|  Terms and Privacy Policy.       |
+---------------------------------+
```

**Notes**
- **"WhatsApp login":** WhatsApp itself does not offer a "Sign in with WhatsApp" button like Google does. The usual way is a **phone number with a one-time code sent on WhatsApp** (or by SMS as a backup). This needs a verified WhatsApp Business account and approved message templates, and costs per message. Plan it for a later phase and confirm Meta's current rules. Telegram also offers an official login widget, which may be an easier "chat app" login to add first.
- Show the password with a "Show" toggle. Show rules as the person types, not after an error.
- Error text is specific: "That email is already registered. Log in instead." with a link.
- After a provider login the person lands on Welcome, not Home.
- If the provider gives no email, ask for one before continuing.
- Rate limit message: "Too many tries. Wait one minute."
- Accessibility: provider buttons are real buttons with text, not only icons.

**Other auth screens**
- **Verify email:** "We sent a link to you@example.com. Open it to continue." Buttons: "Resend email" (with a 60 second timer) and "Change email".
- **Forgot password:** one field, one button, a clear "If this email exists, we sent a link" message.
- **Reset password:** new password, confirm, strength hint.

### S4. Welcome (first time only)
- A full-screen friendly card: "Welcome, [first name]. Let's get you ready in 5 short steps."
- Shows the checklist (4.1) with times.
- Two buttons: "Start" and "Try with a sample notice first".
- A privacy line: "We use your answers only to check eligibility and fill forms."

### S5. Quick profile (3 mini-steps, not one long form)
- **Step 1: About you:** name, date of birth (with a date picker and a typing option DD/MM/YYYY), gender.
- **Step 2: Your category and place:** category, state, city.
- **Step 3: Your studies:** highest qualification, year, percentage.
- Each step has Back, Next, and "Skip for now". A progress bar at the top shows "Step 2 of 3".
- Each field has a "Why we ask" link that opens a one-line reason ("Age and category decide the age limit").
- Save on every Next.
- The full profile page (S14) holds everything else.

### S6. Home (dashboard, after login)

**Purpose:** answer "what should I do next?" in one look.

**Layout (top to bottom)**
1. Greeting and the **setup checklist** (until complete).
2. **Next deadline** card: biggest, shows days left, title, status chip, button "Open".
3. **Quick actions** (4 big buttons): Add a notice, Ask the assistant, Fix a photo, Open vault.
4. **My applications:** up to 5 rows (title, deadline chip, status).
5. **Recent notices.**
6. **Connect chat apps** card (only if not linked).

```
+---------------------------------------------+
| Hi Asha                                      |
| Setup: 2 of 5 done   [Continue setup]        |
| [x]Basics [x]First notice [ ]Photo [ ]Chat [ ]Extension |
+---------------------------------------------+
| Next deadline: Army post   [5 days left]     |
|                               [Open]         |
+---------------------------------------------+
| [Add notice] [Ask assistant] [Fix photo] [Vault] |
+---------------------------------------------+
| My applications                    [Tracker] |
|  Army post         14 Nov  [In progress]     |
|  Bank PO           02 Nov  [Planned] 1 day   |
+---------------------------------------------+
| Connect Telegram or WhatsApp  [Connect]      |
+---------------------------------------------+
```

**States:** empty (no notices) shows a large card "Add your first notice" with the sample notice button.

### S7. Notices (list)
- Search box, filter chips (All, Open, Closing soon, Closed, Verified).
- Each row: title, organisation, last date chip, safety chip, "Verified" or "User uploaded" label, eligibility chip (if profile complete).
- Primary button "Add notice". Empty state with sample notice.

### S8. Add a notice
- Three tabs: **Upload file**, **Paste text**, **From a link** (later).
- Drop zone with "PDF, photo or text, up to 15 MB". On phone it offers "Take a photo".
- A line under it: "Only public notices. Do not upload personal documents here."
- After submit: a progress screen with named steps and the time: "Reading (about 20 seconds)", "Checking safety", "Finding key facts", "Ready". The user can leave; they will get a chat message when ready.
- If the notice already exists in the library: "Good news, this notice is already read. Opening it now."
- Errors: unreadable scan ("This looks like a scanned page. Try a clearer photo or paste the text."), too big, wrong type.

### S9. Notice detail
**Header:** title, organisation, last date chip, safety chip, version label ("Updated 3 Nov"), "Add to tracker" button.

**Tabs (scrollable on phone):**
1. **Overview:** "Key facts" cards (who can apply, qualification, fee, last date, documents, selection, photo and signature) from the quick answers. Each shows its page chip and a confidence label ("Found in notice" or "Please check").
2. **Eligibility:** the verdict in a large chip, then each check as a row with icon, rule, your value, notice rule, page. If something is missing, a yellow card: "Add your date of birth to continue" with a button that opens just that field.
3. **Ask:** a chat box about this notice (see S10).
4. **Documents:** "What you need" checklist with ready or missing, and buttons "Fix photo", "Upload".
5. **Updates:** versions and what changed.
6. **Safety:** the reasons and tips.

```
+---------------------------------------------+
| < Notices                                    |
| Army Agniveer 2026        [Safe] [Verified]  |
| Last date 14 Nov  | 16 days left             |
| [Add to tracker]                             |
+---------------------------------------------+
| Overview | Eligibility | Ask | Documents | Updates |
+---------------------------------------------+
| Who can apply   Age 17.5-21, Class 10 pass   |
|                 page 1                       |
| Fee             Rs 250 online     page 2     |
| Photo           200x230 px, 20-50 KB page 2  |
| ... (cards)                                  |
+---------------------------------------------+
```

**Rule:** every fact card shows its page chip. Tapping it opens the page view with the sentence highlighted.

### S10. Assistant (chat)

**Purpose:** answer anything about the user's notices and applications.

**Layout:** a chat. Top bar has "About: [notice selector]" so the person can see and change what the chat is about. Under the input are 4 suggestion chips that change by context ("Am I eligible?", "What is the fee?", "Which documents do I need?", "What deadlines are close?").

**Each answer has:**
- the answer text
- citation chips ("Page 2")
- a status line ("Checked answer" or "Please check the notice")
- a small "How I answered" toggle (8.4)
- thumbs up and down

```
+---------------------------------------------+
| About: Army Agniveer 2026  [change]          |
|                                              |
| You: Am I eligible?                          |
| ----------------------------------------    |
| You look eligible.                           |
|  Age: 19 y 6 m on 1 Oct (limit 21, OBC +2)   |
|  Qualification: Class 10 (needed: Class 10)  |
| [Page 1] [Page 2]                            |
| v How I answered                             |
|   Safety check: passed                       |
|   Chose: Eligibility helper                  |
|   Used: age calculator, eligibility rules    |
|   Source: notice version 12 Oct              |
| (thumbs up) (thumbs down)                    |
+---------------------------------------------+
| [Am I eligible?] [Fee?] [Documents?]         |
| [Type your question...             ] [Send]  |
+---------------------------------------------+
```

**States:** typing indicator with the current step ("Checking your profile..."), blocked question (friendly message, no scolding), no answer found ("I could not find this in the notice. Check the official site."), long wait (after 8 seconds show "Still working...").

### S11. Photo studio

**Purpose:** make a photo or signature that passes the portal's rules, with confidence.

**Layout:** a 3-step flow on one screen.
1. **Choose rules:** pick a notice (rules are filled in) or enter your own. Shows "Needs: 200 x 230 px, 20 to 50 KB, white background".
2. **Add your picture:** drop zone or camera. A tip card: "Face the camera, even light, plain wall."
3. **Result:** before and after side by side, a checklist (size, KB, background, face found), and buttons "Download", "Save to vault", "Try again".

**Extra controls (collapsed under "Adjust"):** background colour (swatches plus a text box that accepts words like "light blue"), brightness, tighter or looser crop, rotate. If the notice requires white, picking another colour shows a warning.

**Notes:** show a quality check before editing ("Your photo is a bit dark. Brighten it?"). Always keep the original. Download as a file, not a compressed photo. Show "Saved as a copy for: Army post" after saving.

### S12. Vault

**Purpose:** all documents in one place, with originals and per-application copies clearly separate.

- Group by document type (Photo, Signature, Marksheets, Certificates, Other).
- Each original shows its copies indented underneath: "Copy for Army post, 200x230, 38 KB, APP-0007".
- Row actions: Download, Make a copy for an application, Rename, Delete.
- Deleting an original lists the copies that depend on it and asks for confirmation. Deleting a copy never touches the original.
- Storage bar: "12 MB of 50 MB used".
- Empty state: "Add your first document. Keep originals here; we make copies when you apply."
- Banner: "Files are encrypted before they are saved."

### S13. Tracker
- Two views: **List** (default) and **Board** (Planned, In progress, Submitted, Closed). Board is optional.
- Row: title, deadline with days-left chip, status dropdown, reference (APP-0007), linked notice, "Documents" button.
- A "Closing soon" group at the top.
- Application page: checklist (documents ready, form filled, fee paid, submitted), notes, reminders ("Remind me 3 days before"), and "Add to calendar".

### S14. Profile
- Sections as cards: Personal, Category and place, Education, Contact, Sign-in methods.
- A completeness bar ("80% complete") with a list of missing items that matter for eligibility.
- Each field has a hint and a lock icon with "Only you can see this".
- Sign-in methods card: shows which providers are linked, with Link and Unlink (cannot unlink the last method).
- No ID number or payment fields. A note says why.

### S15. Chat apps (connect Telegram and WhatsApp)

**Purpose:** make connecting a 1-minute task with no typing of codes where possible.

**Layout:** two cards side by side (stacked on phone): Telegram, WhatsApp. Each shows a status chip (Not connected, Connected, Coming soon).

**Telegram flow (4 numbered steps on one screen)**
1. Tap **Open Telegram** (a link that opens the bot with the code already included, using Telegram's start link feature). The person only presses "Start" in Telegram.
2. Fallback: "Or send this message to @YourBot": a copy field with `/link ABC123` and a Copy button. Countdown "Code expires in 9:41".
3. The page watches for the link and turns green: "Connected as @username".
4. A next-step card: "Try it: send a notice PDF to the bot."

**WhatsApp flow:** same pattern with a WhatsApp link that opens a chat with a prefilled message (a "click to chat" link). Label "Experimental" until it is tested live.

**"What can I do in chat?" panel (always visible):**
- Send a PDF, I read it.
- Ask any question about it.
- Send a photo with the caption "photo 3", I fix it.
- Type /deadlines for what is due soon.
- You get a reminder 3 days before a deadline.

**Safety line:** "Chat apps are not end-to-end private for bots. Never send passwords or ID numbers."
**Connected state:** shows the account name, "Send a test message", "Disconnect", and reminder settings.

### S16. Browser extension page
- A short video or 4 pictures: Install, Sign in, Scan, Review and fill.
- Steps: 1 Add to Chrome. 2 Pin it. 3 Open the form page. 4 Click ApplyPilot, then "Scan this page". 5 Check the yellow rows. 6 Fill, then submit yourself.
- A "What it never does" box: never submits, never fills passwords, captcha or ID fields.
- A "Try it" button that opens the sample form.
- Status: "Extension signed in" detected when it connects.

### S17. Settings and privacy
- Language (with a preview).
- Notifications (reminder days, chat or email).
- Sign-in methods.
- Privacy: what we keep, "Download my data", "Delete my account" (type your email to confirm, explains what is deleted).
- Sharing: "Share public notices with other users" toggle (default asks every time).

### S18. Help centre and contextual help
See section 8.1. Includes a search box and 6 starter articles.

### S19. Search jobs (later phase)
Search box, results list with a trust label (Official, Known site, Unknown), a preview pane (or "Open in a new tab" when a site blocks previews), and a button "Add as a notice". Show a short warning for unknown sites.

### S20. Admin (admins only)
Tabs: Accounts, Reported notices, Library (verify, hide), Audit log, Usage. Tables with filters, bulk actions with confirmation. Never shows user documents or profiles.

### S21. System screens
- **404:** "We could not find that page." Buttons: Home, Help.
- **Offline:** "You are offline. Your changes will be saved when you reconnect."
- **Error:** "Something went wrong on our side. Try again. If it keeps happening, tell us" with a reference code.
- **Session expired:** friendly sign-in prompt that returns to the same page.
- **Maintenance:** a clear message with a time.

---

## 7. Flows to design as sequences

1. **Sign up, verify, welcome, profile, first notice** (4.1)
2. **Add a notice from chat, then see it on the website** (a "New from Telegram" badge)
3. **Eligibility with a missing date of birth:** click "Add date of birth" from the Eligibility tab, edit only that field in a dialog, return to the result and re-run it. No leaving the page.
4. **Make a copy for an application:** Vault, "Make a copy", pick application, preview, confirm, appears under the original.
5. **Delete an original with copies:** dialog lists the copies, "Delete original only" and "Delete original and copies", default is Cancel.
6. **Link an extra sign-in method.**
7. **Connect Telegram** (S15).

---

## 8. Cross-cutting patterns

### 8.1 Help: where instructions live (nothing hidden, nothing everywhere)

| Place | What it holds |
|---|---|
| Landing page and How it works | The story and the full workflow |
| Setup checklist | The next 5 steps with times |
| Screen intro card (first visit only, dismissible, "Show again" in Help) | "What you will do here" in 2 lines |
| Inline hint under a field | Why we ask, format, example |
| "Why we ask" link | A one-line reason |
| Empty state | What this is, why it helps, the first action |
| Help button (every app screen) | A drawer with help for this exact screen, plus search |
| Tooltips | Short meanings of chips and icons (works on tap, not only hover) |
| Guided tour (optional) | 4 highlight steps on first login, skippable |
| Help centre | Full articles with pictures and short videos |
| Error messages | What happened, what to do, a link to the fix |
| Chat apps page | The command list and examples |

Rules: help text is short, written for the screen, and kept in one content file so it can be edited without code.

### 8.2 Waiting and long jobs
- Under 1 second: no indicator. 1 to 10 seconds: spinner with text. Over 10 seconds: a progress screen with steps and "You can leave; we will message you".
- Optimistic updates for small things (checking a box, changing a status).

### 8.3 Confirmations and undo
- Destructive actions use a dialog that names the item and the effect.
- Small deletes use a toast with Undo for 8 seconds.
- Never delete on a single tap without one of these.

### 8.4 The "How I answered" trace
A collapsed line under each assistant answer. When opened it shows, in plain words and in order: safety check, which helper was chosen and why, which tools ran with their results (for example the age working), which pages and version were used, time taken. Never show private values in full ("date of birth from your profile"). On chat apps it is one short footer line. Admins can open the full trace.

### 8.5 Trust and safety signals
- Chips: Verified, User uploaded, Safe, Check carefully, High risk.
- Every answer: page chips and a "Check the official notice" link.
- Never claim certainty the system does not have ("You look eligible", not "You are eligible").
- Privacy reminders sit where data is entered, not only in a policy page.

### 8.6 Language
- Language switch in the header and in Settings, saved to the profile.
- All screen text lives in translation files. Start with English, then Hindi, then others.
- Dates are shown as "14 Nov 2026" (month in words) to avoid DD/MM confusion.
- Allow longer text: buttons must grow, not clip.

### 8.7 Forms
- One column. Label above. Hints below.
- Validate on leaving a field, not on every key.
- Keep the typed value when there is an error.
- Mobile keyboards: number keyboard for phone and percentage, email keyboard for email.

### 8.8 Notifications
- In app: a bell with a count; list of "Notice updated", "Deadline close", "Your file is ready".
- Chat: reminders at 3 days and 1 day, one message per application per day.

---

## 9. Accessibility and responsive rules

- Target **WCAG 2.2 level AA**.
- Contrast: use only the tested pairs in 5.1.
- Everything works with the keyboard. Visible focus ring (2 px, primary colour, 2 px offset).
- Every image has alt text; decorative images are hidden from screen readers.
- Form fields have real labels. Errors are announced (`role="alert"`).
- Dialogs trap focus and return it on close. Escape closes them.
- Do not rely on colour alone. Do not rely on hover alone.
- Respect "reduce motion". Keep animations under 200 ms.
- Text can zoom to 200% with no loss.
- Breakpoints: 360 (phone), 768 (tablet), 1024 (desktop), 1280 (wide). Layouts are fluid between them.
- Test with a screen reader (TalkBack on Android, VoiceOver on iPhone) on the 3 main flows.

---

## 10. Performance on slow phones

- Aim for first useful screen in under 3 seconds on a mid-range phone on 4G. Measure it; do not assume.
- Compress images; use modern formats; set sizes.
- Load the heavy screens (photo studio, PDF view) only when opened.
- Keep the landing page free of large scripts.
- Cache the notice list and profile for quick return visits.
- Allow uploading a photo from the camera at a reduced size before sending.

---

## 11. Content and tone

- Friendly, direct, calm. Short sentences. Active voice.
- No blame: "That code did not work" not "You entered a wrong code".
- Numbers and dates are specific. Say "5 days left", not "soon".
- Examples of microcopy:

| Moment | Text |
|---|---|
| Empty vault | "Nothing here yet. Add your photo, signature and certificates once. We make the right copy for each application." |
| Missing date of birth | "To check your age, we need your date of birth. It stays private." |
| Not eligible | "You may not be eligible. Age on 1 Oct 2026: 21 years 2 months. The limit is 21 years. Please check the official notice." |
| Blocked question | "I can help with your notices, eligibility, documents and deadlines. Ask me about one of those." |
| File ready | "Your file is ready: 200 x 230 px, 38 KB, white background." |
| Delete original | "This photo has 2 copies for applications. Delete only the original, or the original and its copies?" |
| Connect success | "Connected. Send me a notice PDF to try it." |

---

## 12. Metrics for the interface

Collect events without personal data (page, action, time). Check these after launch and set targets once you have a baseline:

- Time from sign-up to first notice ready
- Percentage who finish each checklist step
- Percentage who connect Telegram or WhatsApp
- Questions asked per notice, thumbs up and down ratio
- Where people stop in sign-up
- Photo studio: first-try pass rate
- Help drawer opens per screen (a screen with many opens needs better text)

Run a test with 5 real students on a phone before launch. Give them tasks without help: "Find out if you can apply to this notice", "Fix this photo", "Connect Telegram". Note where they hesitate.

---

## 13. How to build it with your Meta model

### 13.1 Order of work

| Step | Work | Done when |
|---|---|---|
| 1 | Theme file: tokens, fonts, base components (5.1 to 5.4) | A sample page uses only tokens |
| 2 | App shell: header, bottom bar, sidebar, help drawer | Navigation works on phone and desktop |
| 3 | Public pages: S1, S2, plus Safety and Help centre shell | Landing page loads fast |
| 4 | Auth screens: S3 and its email screens, provider buttons wired later | All states designed |
| 5 | Welcome, checklist, quick profile: S4, S5, S6 | A new user reaches Home with a checklist |
| 6 | Notices: S7, S8, S9 | A notice shows facts, safety, eligibility |
| 7 | Assistant with the trace: S10 | Every answer shows its steps |
| 8 | Photo studio, Vault, Tracker: S11 to S13 | Copies appear under originals |
| 9 | Profile, Chat apps, Extension, Settings: S14 to S17 | Connect Telegram in under 1 minute |
| 10 | System screens, accessibility pass, speed pass | Checks in section 9 and 10 pass |

### 13.2 Master prompt (paste first, then add one screen prompt)

```
You are a senior product designer and front-end engineer. Build screens for ApplyPilot, an app that helps young people apply for jobs, exams and admissions.

Stack: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui. Use the existing API client in frontend/lib/api.ts and the types in frontend/lib/types.ts. Do not change the API.

Design rules:
- Phone first (360 px), then tablet and desktop.
- Colours only from these tokens: primary #2f5bea, primary-dark #1d3fb5, primary-soft #e8eefc, ink #1b1f2a, muted #5b6475, line #e4e7ee, page #f6f7fb, surface #ffffff, success #157f4b, success-soft #e7f6ee, warning #a15c00, warning-soft #fff4e0, danger #b42318, danger-soft #fdecea.
- Font: Inter. Body text 16 px. Touch targets at least 44 px. Radius 8 for inputs and buttons, 12 for cards.
- One primary button per screen. Plain English; never show technical words such as RAG, embedding, agent.
- Every list needs an empty state (what this is, why it helps, one button), a loading state and an error state.
- Status chips always have an icon and a word, never colour alone.
- Accessibility: WCAG 2.2 AA, labels on all fields, visible focus ring, keyboard support, role="alert" on errors.
- Every screen gets a Help button that opens a drawer with short help for that screen.
- Never show private values in full in traces or toasts.

Return: the page file, any new components, and a short list of the states you handled.
```

### 13.3 Screen prompts (use with the master prompt)

**Landing page (S1)**
```
Build the public landing page at app/(public)/page.tsx with these sections: header with logo and links, hero ("Stop losing chances to paperwork."), the problem (3 cards), how it works (4 steps), features (6 cards), "use it where you are" (website, Telegram, WhatsApp marked coming soon, extension), safety strip, FAQ (6 items as an accordion), final call to action, footer. Two hero buttons: "Get started free" (primary) and "See how it works" (scrolls). Keep above-the-fold images small. Use the copy from the design spec section S1.
```

**Sign up and log in (S3)**
```
Build app/login/page.tsx as one card with a Log in and Create account switch. Order: Continue with Google, Continue with LinkedIn, Continue with GitHub, Continue with phone, a divider "or use email", then the email form. Password has a Show toggle and live rule hints. Add loading and error states, a rate-limit message, and links to Terms and Privacy. The provider buttons call a function I will wire later; build them as real buttons with text. Also build the Verify email, Forgot password and Reset password screens.
```

**Welcome, checklist, quick profile (S4 to S6)**
```
Build a Welcome screen with the 5-step setup checklist and times, a "Start" button and a "Try with a sample notice" button. Build a 3-step profile wizard (About you, Category and place, Your studies) with a progress bar, Back, Next and Skip for now, "Why we ask" links, and save on every Next. Build the Home dashboard with: greeting, collapsible setup checklist, Next deadline card, 4 quick actions, My applications list, Recent notices, and a Connect chat apps card. Include empty states.
```

**Notices and notice detail (S7 to S9)**
```
Build the Notices list with search, filter chips and rows showing title, last date chip, safety chip, verified label and eligibility chip. Build the Add notice page (upload, paste text) with a progress screen of named steps. Build the Notice detail page with tabs: Overview (fact cards each with a page chip and a "Found" or "Please check" label), Eligibility (large verdict chip, one row per check, a yellow card for missing inputs with an inline fix), Ask, Documents (ready and missing checklist with buttons), Updates, Safety. Tapping a page chip opens a page view with the sentence highlighted.
```

**Assistant (S10)**
```
Build the Assistant chat page. Top: "About: [notice selector]". Messages with page chips, a status line, thumbs up and down, and a collapsible "How I answered" panel listing: safety check, which helper was chosen and why, tools used with short results, sources and version, time. Context-based suggestion chips above the input. Handle typing steps ("Checking your profile..."), blocked questions, "not found" answers, and a "Still working..." message after 8 seconds. Stream the answer if the API supports it.
```

**Photo studio (S11)**
```
Build the Photo studio as a 3-step flow on one page: choose rules (from a notice or custom), add a picture (drop zone, camera on phone, tips card), result (before and after, checklist of size, KB, background, face found, buttons Download, Save to vault, Try again). Add an "Adjust" section with background colour swatches plus a text box, brightness, crop tightness and rotate. Warn when the chosen colour breaks the notice's rule. Show a quality warning before editing when the image is dark or blurry. Always keep the original.
```

**Vault and Tracker (S12, S13)**
```
Build the Vault grouped by document type, with each original showing its application copies indented ("Copy for Army post, 200x230, 38 KB, APP-0007"). Actions: Download, Make a copy for an application, Rename, Delete. Deleting an original opens a dialog listing its copies with "Delete original only", "Delete original and copies", and Cancel as the default. Add a storage bar. Build the Tracker with a list view, a Closing soon group, status dropdowns, reference numbers, and an application page with a checklist, notes, reminders and "Add to calendar".
```

**Chat apps (S15)**
```
Build the Chat apps page with Telegram and WhatsApp cards. Telegram: 4 numbered steps, an "Open Telegram" button (link with the code included), a fallback copy field with "/link CODE" and a countdown, live status that turns to "Connected as @username", then a "Try it" card. WhatsApp: same pattern with a "click to chat" link and an Experimental label. Add a permanent "What can I do in chat?" panel and a privacy line. Include connected and error states.
```

**Profile, Extension, Settings (S14, S16, S17)**
```
Build the Profile page as cards (Personal, Category and place, Education, Contact, Sign-in methods) with a completeness bar listing missing items that matter for eligibility, a "Only you can see this" note, and link and unlink buttons for providers (cannot unlink the last one). Build the Extension page with 5 install and use steps, a "What it never does" box and a "Try the sample form" button. Build Settings with language, notifications, privacy, sharing toggle and Delete my account (type your email to confirm).
```

**Help system**
```
Build a Help drawer component used on every app page. It takes a screen id, shows 3 to 5 short help items from a content file (src/content/help.ts), has a search box that searches all help items, and links to the full Help centre. Build the Help centre with 6 starter articles: first steps, connect Telegram, connect WhatsApp, install the extension, photo rules, FAQ.
```

### 13.4 Review checklist for each generated screen

- [ ] Uses only the colour tokens
- [ ] 360 px layout works with no sideways scrolling
- [ ] One clear primary button
- [ ] Empty, loading, error and success states exist
- [ ] Every field has a label and a hint
- [ ] Keyboard only: can you finish the task?
- [ ] No technical words on screen
- [ ] Help button opens the right help
- [ ] Destructive actions ask first
- [ ] Contrast pairs match section 5.1

---

## 14. Decisions for you

1. **Component library:** Tailwind with shadcn/ui (recommended), or keep plain CSS.
2. **First login options to launch:** email, Google and LinkedIn first? GitHub is useful for developers but not for most students.
3. **WhatsApp login:** postpone until the WhatsApp business setup is done? A Telegram login button may be easier first.
4. **Languages:** English and Hindi first?
5. **Dark theme:** include now or later? (Recommended: later.)
6. **Sample notice:** keep the fictional sample as the "try it" demo?
7. **Brand:** keep the current logo and colours, or change them? (If you change them, run the contrast check again.)
