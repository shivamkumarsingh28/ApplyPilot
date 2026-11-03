# ApplyPilot: Tool Calling Inventory

**What this is:** a list of everything in ApplyPilot that can be a plain Python tool the model calls from the chat. No code here. Each tool is a small function that does one job the same way every time.

## 1. The short answer

**About 120 tools, in 11 groups.** Of these:

- **9 already exist** as agent tools today.
- **22 are easy:** the code already exists in the project as a service. You only wrap it as a tool.
- **89 are new** (most are small).
- **110 of 120 need no AI model inside them.** They are pure code. The model only chooses them and explains the result.
- Only 5 always need a model inside (reading scans, translating, explaining a field). 5 can use one optionally.

**Start with the Priority 1 set: 54 tools.** That covers the main chat journey. Priority 2 has 44 tools and Priority 3 has 22.

| Kind of tool | Count | Meaning |
|---|---|---|
| read | 42 | Looks things up. Safe. |
| compute | 20 | Calculates or checks. Safe, always the same result. |
| edit | 27 | Changes a working copy of a file. The original is never touched. |
| write | 23 | Saves or changes the user's data. Needs confirmation when it overwrites. |
| destructive | 3 | Deletes. Needs confirmation and a warning. |
| external | 5 | Uses the network or sends something out. Rate limited. |

## 2. What should be a tool, and what should not

**Make it a tool when** the answer must be exact, the job is the same every time, or the app changes something: dates, ages, fees, image size and colour, file size, PDF merging, saving, deleting, reminders, searching, form matching.

**Leave it to the model when** the job is language: explaining a rule in simple words, summarising, translating, drafting, choosing which tool to use, and asking a friendly question.

**Leave it to the person when** the law, a website or money is involved: submitting the form, solving a captcha, paying a fee, signing. The assistant can prepare and remind, but never do these.

## 3. Rules for good tools

- **One job per tool, with a verb name.** `crop_to_face`, not `edit_photo`.
- **Small, clear inputs.** Use fixed lists (for example category, format, kind) so the model cannot invent values.
- **Return the answer and the working.** Example: age on the date, how it was counted.
- **Never pass image bytes through the model.** Files have ids. The model sends ids; the tool opens the file itself. This is faster, cheaper and private.
- **Never change an original.** Every edit makes a new working copy with its own id, and a history so `undo_last_edit` works.
- **Missing input is a normal answer, not an error.** The tool replies 'needs date of birth, choices: ...'. The agent then calls `ask_user` and tries again.
- **Two steps for changes.** Write and delete tools first return a proposal ('I will delete photo_ready.jpg and keep the original'). The user says yes. Then it runs.
- **Same user only.** The tool gets the signed-in user from the server. It has no 'user' input to fake.
- **Limits and logs.** Size limits, time limits, rate limits, and a log line for every call with its time.
- **Safe to repeat.** Running the same tool twice with the same input must not create a mess.

## 4. The catalog

Status: **Exists** = already an agent tool. **Wrap** = the code exists, make it a tool. **New** = write it. P = priority. 'Model inside' = whether the tool itself must call an AI model.

### 1. Notice reading (12 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `list_notices` | List the user's saved notices | none | read | no | 1 | Exists |
| `get_notice_facts` | Key facts: dates, age, qualification, fee, documents | notice_id | read | no | 1 | Exists |
| `get_key_answers` | The quick answers made at ingest | notice_id | read | no | 1 | Wrap |
| `ask_notice` | Answer one question from the notice, with page | notice_id, question | read | optional | 1 | Exists |
| `find_in_notice` | Return matching passages and pages, no answer writing | notice_id, words | read | no | 2 | Wrap |
| `get_notice_page` | Return the text of one page | notice_id, page | read | no | 2 | New |
| `get_scam_report` | Safety level and reasons | notice_id | read | no | 1 | Exists |
| `add_notice` | Start reading a new notice (file, text or link) as a background job | file or text | write | no | 1 | Wrap |
| `get_ingest_status` | Say if a notice is queued, reading, ready or failed | job_id | read | no | 1 | New |
| `list_notice_versions` | Show the versions of a notice and their dates | notice_id | read | no | 2 | New |
| `compare_notice_versions` | List what changed between two versions | notice_id, v1, v2 | compute | no | 2 | New |
| `hide_or_delete_notice` | Remove a notice from the user's list | notice_id | destructive | no | 3 | New |

### 2. Eligibility and calculators (13 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `calculate_age` | Exact age on a date, in years, months, days | dob, as_on_date | compute | no | 1 | Wrap |
| `calculate_days_left` | Days between two dates, or days to a deadline | date, [from_date] | compute | no | 1 | New |
| `check_eligibility` | Full check against the notice rules, with each reason | notice_id | compute | no | 1 | Exists |
| `explain_eligibility_rule` | Show one rule with its exact sentence and page | notice_id, rule | read | no | 1 | New |
| `apply_age_relaxation` | Upper age after relaxation for a category | base_max, category, rules | compute | no | 1 | Wrap |
| `check_qualification` | Compare the user's level with the required level | have, required | compute | no | 2 | Wrap |
| `check_marks_requirement` | Compare percentage with the minimum | marks, minimum | compute | no | 2 | Wrap |
| `calculate_application_fee` | Fee for this category and gender from the notice table | notice_id, category, gender | compute | no | 2 | New |
| `what_if_eligibility` | Re-run the check with one changed input, without saving | notice_id, change | compute | no | 2 | New |
| `rank_notices_for_me` | Order saved notices by eligibility and deadline | none | compute | no | 2 | New |
| `convert_grade_to_percentage` | Convert CGPA using the formula the notice states | grade, formula | compute | no | 3 | New |
| `parse_date_text` | Turn '10 March 2007' or '10/3/07' into a date | text | compute | no | 1 | New |
| `get_missing_profile_fields` | List profile items the check still needs | notice_id | read | no | 1 | Exists |

### 3. Profile (7 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `get_profile_summary` | Which fields are filled (names only, no sensitive values) | none | read | no | 1 | New |
| `update_profile_field` | Change one profile field after validation and confirmation | field, value | write | no | 1 | New |
| `validate_contact_fields` | Check phone, email and PIN code formats | values | compute | no | 2 | New |
| `propose_profile_from_document` | Read a marksheet and propose profile values for the user to confirm | document_id | read | yes | 2 | New |
| `set_language_preference` | Choose the reply language | language | write | no | 2 | New |
| `export_my_data` | Prepare the user's own data for download | none | external | no | 3 | New |
| `delete_my_account` | Delete the account and all data (confirm twice) | none | destructive | no | 3 | New |

### 4. Photo and signature studio (27 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `get_image_requirements` | Size, KB, format and background rules of a notice | notice_id, kind | read | no | 1 | Exists |
| `inspect_image` | Size in pixels, KB, format, DPI, main colours | image_id | read | no | 1 | New |
| `detect_face` | Find the face, count faces, give position | image_id | read | no | 1 | Wrap |
| `check_photo_quality` | Blur, brightness, face size, tilt, with a list of problems | image_id | read | no | 1 | New |
| `auto_orient` | Fix phone rotation using the picture's own orientation tag | image_id | edit | no | 1 | Wrap |
| `rotate_image` | Rotate by an angle | image_id, degrees | edit | no | 2 | New |
| `crop_to_face` | Crop around the face to a ratio with a chosen margin | image_id, ratio, margin | edit | no | 1 | Wrap |
| `crop_to_box` | Crop an exact box, or to an aspect ratio | image_id, box or ratio | edit | no | 2 | New |
| `remove_background` | Cut out the person (SAM 3.1 or OpenCV) | image_id | edit | no | 1 | Wrap |
| `parse_color_name` | Turn 'light blue' or '#e6f0ff' into a colour value | text | compute | no | 1 | New |
| `set_background_color` | Fill the background with a chosen colour | image_id, color | edit | no | 1 | Wrap |
| `adjust_light` | Brightness, contrast, auto-levels | image_id, amounts | edit | no | 2 | New |
| `sharpen_or_denoise` | Reduce blur or noise a little | image_id, strength | edit | no | 3 | New |
| `resize_exact` | Resize to exact pixels | image_id, width, height | edit | no | 1 | Wrap |
| `compress_to_range` | Reach a KB range by choosing quality | image_id, min_kb, max_kb | edit | no | 1 | Wrap |
| `convert_image_format` | JPG, PNG or WebP | image_id, format | edit | no | 2 | New |
| `clean_signature` | Even out light, find ink, crop tight, white page | image_id | edit | no | 1 | Wrap |
| `make_signature_transparent` | Signature on a see-through background (PNG) | image_id | edit | no | 3 | New |
| `pad_to_canvas` | Place on a canvas of exact size with margins | image_id, width, height | edit | no | 2 | New |
| `verify_image_against_spec` | Pass or fail for each rule | image_id, spec | compute | no | 1 | Wrap |
| `make_preview` | Small preview image for chat | image_id | edit | no | 1 | New |
| `compare_before_after` | Side-by-side picture for the user to judge | image_id_a, image_id_b | edit | no | 3 | New |
| `undo_last_edit` | Go back one step in the working copy history | image_id | edit | no | 1 | New |
| `prepare_photo_for_notice` | Recipe: runs the whole photo pipeline for a notice | image_id, notice_id, options | edit | no | 1 | Wrap |
| `prepare_signature_for_notice` | Recipe: runs the whole signature pipeline for a notice | image_id, notice_id | edit | no | 1 | Wrap |
| `save_image_as_copy` | Save the result to the vault as a copy for an application | image_id, application_id | write | no | 1 | New |
| `send_file_to_user` | Send the file as a document in the chat | file_id | external | no | 1 | New |

### 5. PDF and document tools (12 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `get_document_info` | Pages, size, type, whether text is readable | document_id | read | no | 1 | New |
| `compress_pdf` | Reduce a PDF to a size limit | document_id, max_kb | edit | no | 2 | New |
| `merge_pdfs` | Join several files into one | document_ids | edit | no | 2 | New |
| `extract_pdf_pages` | Keep only chosen pages | document_id, pages | edit | no | 2 | New |
| `rotate_pdf_pages` | Rotate chosen pages | document_id, pages, degrees | edit | no | 3 | New |
| `images_to_pdf` | Turn phone pictures into one PDF | image_ids | edit | no | 2 | New |
| `pdf_page_to_image` | Render a page as a picture | document_id, page | edit | no | 3 | Wrap |
| `read_text_from_image` | Read text from a scan or photo | image_id | read | yes | 2 | Wrap |
| `classify_document_type` | Marksheet, caste certificate, ID, notice, other | document_id | read | optional | 2 | New |
| `extract_document_fields` | Read name, date of birth, marks from a certificate | document_id | read | yes | 2 | New |
| `rename_document` | Give a file a clear name | document_id, name | write | no | 3 | New |
| `is_public_notice` | Check a file is a public notice and not personal, before sharing | document_id | read | optional | 1 | New |

### 6. Vault and application copies (8 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `list_documents` | List stored files, with filters | kind, application_id | read | no | 1 | New |
| `get_storage_usage` | Used and free space | none | read | no | 2 | New |
| `make_application_copy` | Make a copy of an original that fits one application's rules | document_id, application_id | edit | no | 1 | New |
| `list_application_documents` | Originals and copies for one application | application_id | read | no | 1 | New |
| `delete_document` | Delete a copy, or an original (warns about its copies) | document_id | destructive | no | 2 | New |
| `find_duplicate_documents` | Spot the same file stored twice | none | read | no | 3 | New |
| `check_document_readiness` | Which required documents are present or missing | notice_id | read | no | 1 | Exists |
| `get_download_link` | Short-lived link to a file | document_id | external | no | 2 | New |

### 7. Tracker and reminders (10 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `upcoming_deadlines` | Open applications due soon | days | read | no | 1 | Exists |
| `list_applications` | All applications with status | status | read | no | 1 | New |
| `create_application` | Start tracking a notice | notice_id | write | no | 1 | New |
| `update_application_status` | Planned, in progress, submitted, closed | application_id, status | write | no | 1 | New |
| `add_application_note` | Add a note to an application | application_id, text | write | no | 3 | New |
| `set_reminder` | Remind some days before the deadline | application_id, days_before | write | no | 1 | New |
| `list_reminders` | Show reminders | none | read | no | 2 | New |
| `cancel_reminder` | Remove a reminder | reminder_id | write | no | 2 | New |
| `create_calendar_file` | Make an .ics file for the deadline | application_id | edit | no | 3 | New |
| `get_application_checklist` | Steps to finish, with done or not done | application_id | compute | no | 2 | New |

### 8. Forms (8 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `map_form_fields` | Match page fields to profile values with confidence | fields | compute | optional | 1 | Wrap |
| `create_form_template` | Start a custom form of a chosen type | name, type | write | no | 2 | New |
| `add_form_field` | Add a field (type, label, options, required) | template_id, field | write | no | 2 | New |
| `change_or_remove_form_field` | Edit or delete a field | template_id, key | write | no | 3 | New |
| `list_form_templates` | Show the user's forms | none | read | no | 2 | New |
| `prefill_form_from_profile` | Fill a custom form from the profile | template_id | compute | no | 2 | New |
| `save_form_answers` | Save a filled custom form | template_id, answers | write | no | 2 | New |
| `explain_form_field` | Explain what a form field is asking, in simple words | field text | read | yes | 2 | New |

### 9. Internet and shared library (9 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `search_jobs_web` | Search the internet for notices and job posts | query, country | external | no | 2 | New |
| `fetch_page_text` | Download a page safely and return its text | url | external | no | 2 | New |
| `import_notice_from_url` | Read a web page or PDF as a notice | url | write | no | 2 | New |
| `check_url_trust` | Official domain, known site or unknown | url | compute | no | 1 | Wrap |
| `find_in_library` | Look for the same notice already in the shared library | fingerprint or title | read | no | 1 | New |
| `link_library_notice` | Add a library notice to the user's list | notice_id | write | no | 1 | New |
| `report_notice` | Report a wrong or fake notice | notice_id, reason | write | no | 2 | New |
| `follow_notice_updates` | Get a message when a notice changes | notice_id | write | no | 2 | New |
| `unfollow_notice_updates` | Stop those messages | notice_id | write | no | 3 | New |

### 10. Chat helpers (shared by every agent) (8 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `ask_user` | Ask one clear question with choices and wait for the answer | question, options | read | no | 1 | New |
| `set_active_notice` | Choose which notice the chat is about | notice_id | write | no | 1 | New |
| `get_chat_state` | What notice is active, what is pending | none | read | no | 1 | New |
| `translate_text` | Translate a reply into the user's language | text, language | read | yes | 2 | New |
| `open_in_website` | Give a link to the exact page on the website | page | read | no | 2 | New |
| `record_feedback` | Save thumbs up or down with a reason | turn_id, rating | write | no | 1 | New |
| `explain_last_answer` | Show the steps used for the last answer | turn_id | read | no | 2 | New |
| `get_usage_and_limits` | Tokens used today and the limits | none | read | no | 3 | New |

### 11. Admin and safety (a separate admin agent, never for normal users) (6 tools)

| Tool | What it does | Main inputs | Kind | Model inside | P | Status |
|---|---|---|---|---|---|---|
| `admin_list_accounts` | Counts and status of accounts (no personal data) | filters | read | no | 3 | New |
| `admin_set_account_status` | Enable or disable an account | user_id, status | write | no | 3 | New |
| `admin_review_reports` | Show reported notices | none | read | no | 3 | New |
| `admin_verify_or_hide_notice` | Mark a library notice verified or hide it | notice_id, action | write | no | 3 | New |
| `admin_audit_summary` | Summary of the audit log | date range | read | no | 3 | New |
| `admin_run_evaluation` | Run the golden set and show scores | none | compute | optional | 3 | New |

## 5. Photo and signature studio in detail

This group is the largest (27 tools). It works well as tools because every step is plain image code.

**Working copies:** when the user sends a picture, the system stores it and gives it an id. Each edit creates a new id and keeps the history. The original stays in the vault.

**Two levels of tools**

1. **Recipe tools** (`prepare_photo_for_notice`, `prepare_signature_for_notice`). One call does the usual path: orient, find face, crop, remove background, set colour, resize, compress, verify. Use these first. They are fast and predictable.
2. **Single-step tools** (crop, rotate, colour, light, and so on). Use these when the user asks for a change: 'tighter crop', 'a bit brighter', 'light blue background'.

**Why not chain eight single tools every time?** Each model step costs time and money, and the model can pick a wrong order. A recipe is exact. Single tools handle the follow-ups.

**Quality checks before editing.** `check_photo_quality` runs plain code: blur score, brightness, face size, tilt, number of faces. The model only explains the result: 'The photo is a little dark and your face is small. Shall I brighten and crop closer?'

**Colour requests.** The user types any colour in words. `parse_color_name` turns it into a value. If the notice says white, the tool warns when the user picks another colour.

## 6. How the assistant asks for missing input

Every tool can answer in one of three ways: **done** (result), **needs input** (what is missing and the allowed choices), or **cannot** (the reason in simple words). When it needs input, the agent calls `ask_user` with one question and a few buttons. In Telegram these are inline buttons; in WhatsApp they are reply buttons or a list. The answer goes back to the same tool.

Examples of things it asks: which notice, which kind (photo or signature), background colour, date of birth, category, which file to delete, whether to overwrite.

## 7. Which agent sees which tools

A model chooses better from a short list. Keep each agent to about 8 tools in view, plus the shared chat helpers (group 10).

| Agent | Groups | Notes |
|---|---|---|
| Notice agent | 1 | Reading and questions |
| Eligibility agent | 2 | Calculators and the eligibility check |
| Profile agent | 3 | Profile reads and changes |
| Photo studio agent | 4 | Shows the recipe tools and checks by default. Single-step edit tools are loaded only when the user asks for a change (use Meta's tool search, or a small 'photo fixer' sub-agent) |
| Documents agent | 5, 6 | PDF tools, vault, application copies |
| Tracker agent | 7 | Deadlines, reminders, checklist |
| Forms agent | 8 | Custom forms, field help |
| Discover agent | 9 | Internet search and the shared library |
| Admin agent | 11 | Only for admins, in a separate chat or screen |

Meta's documentation lists a tool search feature. If you keep more than about 30 tools, confirm how it works and use it so the model loads only the tools it needs.

## 8. Examples: chat to tools

**A. Background change**
User sends a photo with the words 'make the background light blue for the Army form'.
1. `get_chat_state` (which notice is active?). If unknown, `ask_user` 'Which notice?'
2. `get_image_requirements` (the notice says white). The assistant says: 'This notice asks for a white background. Use light blue anyway?' (`ask_user`)
3. `parse_color_name` then `prepare_photo_for_notice` with the colour.
4. `verify_image_against_spec`, `make_preview`. Shows the preview and the pass or fail list.
5. User says yes. `save_image_as_copy` and `send_file_to_user`.

**B. Eligibility with a missing date of birth**
User: 'Am I eligible?'
1. `check_eligibility` replies: needs date of birth.
2. `ask_user` 'Send your date of birth'. User types '10/3/2007'.
3. `parse_date_text`, then `update_profile_field` (with a confirm: 'Save 10 March 2007?').
4. `check_eligibility` again. The answer includes the age working from `calculate_age`.

**C. Many questions at once**
User: 'How many days are left and what is the fee for OBC?'
1. `calculate_days_left` and `calculate_application_fee` run at the same time.
2. The model writes one short answer.

**D. Delete safely**
User: 'Delete my old photo.' `list_documents` finds two. `ask_user` shows both. User picks one. `delete_document` returns a proposal that says the copies for Army 2026 depend on it. User confirms or cancels.

**E. New notice by chat**
User sends a PDF. `is_public_notice`, `find_in_library`. If found, `link_library_notice` (instant). If not, `add_notice` starts the job, `get_ingest_status` is checked when the user returns, then `get_key_answers` is sent.

## 9. Safety for tools

- Every tool runs with the signed-in user only. Test that user A can never reach user B's files or notices through any tool.
- Each agent has an allow-list. A tool outside it is refused, even if the model asks.
- Write, delete and external tools are logged in the audit log with the tool name and ids, never the contents.
- `fetch_page_text` and `import_notice_from_url` must block private addresses and limit size and redirects.
- `send_file_to_user` sends only files owned by that user, to that user's linked chat.
- Admin tools are never given to a normal user's agent, and an admin tool call needs the admin role checked on the server.
- Text from documents, web pages and tool results is data. It must never be able to change which tool is called or with what input.

## 10. How to test tools

1. **Unit tests per tool:** normal case, missing input, wrong input, another user's id, a very large input.
2. **Photo tests:** 20 real photos and 10 signatures. Check pixels, KB, background and that the original is unchanged.
3. **Tool choice test:** write 100 user messages, each with the expected tool or tools. Score how often the model picks them. Aim to improve the descriptions until the score is high.
4. **Flow tests:** the five examples in section 8, end to end, with a fake chat app.
5. **Speed:** record the time of each tool and each model step.

## 11. Build order

| Step | Work | Done when |
|---|---|---|
| 1 | Tool framework: working copies, `needs input` replies, two-step confirm, `ask_user` | One tool uses all three behaviours |
| 2 | Wrap the 'Wrap' tools in Priority 1 (photo recipes, calculators, key answers) | Each has unit tests |
| 3 | Photo checks and single-step edits, preview, undo | Photo tests pass |
| 4 | Vault tools and application copies | Copy made, listed and deleted safely |
| 5 | Tracker and reminders | Reminder arrives in chat |
| 6 | Native tool calling with agent allow-lists; tool choice test | Score agreed with you |
| 7 | Priority 2 groups: PDF, forms, search, library | Each group tested |
| 8 | Priority 3 and admin tools | Admin tools only reachable by admins |

## 12. Decisions for you

1. Do you want the photo agent to show recipe tools first, with single-step tools loaded on request? (Recommended.)
2. Which tools must always ask for confirmation? (Suggested: delete, update profile, make copy for an application, anything that sends a file out.)
3. Do you accept keeping the original untouched and storing every edit as a separate working copy?
4. Which Priority 2 group matters most after Priority 1: PDF tools, forms, or search?
5. How long to keep working copies before cleaning them up? (Suggested: a few days.)

## 13. Link to the other plans

This list is also what an MCP server would offer later. Only the read and compute tools should be offered first. The shared library, versions and question store from Plan V2 add the tools in groups 1 and 9.
