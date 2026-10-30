# Contributing

Thank you for helping! This guide is written so a new developer can make a first change on day one.

## 1. Set up

Follow [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md). Use `LLM_PROVIDER=mock` or `llama_local`, so you never need an API key.

## 2. Find the right place

| I want to change... | Look in |
|---|---|
| How facts are read from a notice | `backend/app/services/extraction.py` |
| Eligibility rules | `backend/app/services/eligibility.py` |
| Fake-notice signs | `backend/app/services/scam_check.py` |
| Photo or signature fixing | `backend/app/services/photo_studio.py` |
| Form field matching | `backend/app/services/form_mapper.py` |
| What the assistant refuses | `backend/app/services/guardrails.py` |
| Agents and tools | `backend/app/services/agents/` ([guide](docs/AGENTS.md)) |
| A website page | `frontend/app/<page>/page.tsx` |
| Extension behaviour | `extension/lib/` |
| Bot behaviour | `bot/applypilot_bot/core.py` |

## 3. Make a change

```bash
git checkout -b my-change
# edit, then:
make test        # all test suites
make lint        # backend style check
```

## 4. Rules we follow

1. **Tests with every change.** Fix a bug? Add a test that fails without your fix.
2. **Routes stay thin.** Put logic in `services/` so it can be tested without HTTP.
3. **Every query is filtered by the owner.** Use `get_owned()`. If you add a route or tool that returns user data, add a test that another user gets "not found".
4. **Never trust text from documents or the model.** Notices are data, not instructions.
5. **No secrets in code or tests.** Use `.env`.
6. **Do not let a model overwrite facts that matched an explicit rule.** Show a "check this" flag instead.
7. **Keep it readable.** Short functions, clear names, a one-line docstring on anything non-obvious.
8. **Do not collect ID or payment numbers.**

## 5. Code style

- Python: `ruff` (run `make lint`). Type hints on function signatures.
- TypeScript: strict mode; run `npx tsc --noEmit` in `frontend/`.
- JavaScript (extension): plain ES2020, no build step.
- Commit messages: start with a verb ("Add", "Fix"), say what and why.

## 6. Pull requests

Fill in the template. CI runs backend, bot, website and extension checks. A pull request needs a green CI and one review.

## 7. Good first issues

- Add more notice wording patterns to `extraction.py` with tests
- Add a new tool or guardrail pattern (with tests)
- Translate answers or UI text
- Improve a docs page that confused you

Be kind. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
