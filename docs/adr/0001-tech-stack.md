# ADR 0001: Tech stack

**Status:** accepted

## Decision

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2
- Website: Next.js 14 (App Router), TypeScript
- Extension: Chrome Manifest V3, plain JavaScript
- Bot: Python, `httpx`; FastAPI only for the WhatsApp webhook
- Database: PostgreSQL in production, SQLite for quick local runs
- Models: one provider interface; Ollama (Llama) for development, Meta Model API for production

## Why

- **Python for the backend:** the best libraries for PDFs (`pypdf`), images (`Pillow`, OpenCV) and AI clients are Python-first. FastAPI gives typed requests and free API docs.
- **Next.js:** the team knows React; TypeScript catches mistakes early.
- **Plain JS extension:** contributors can load the folder and edit with no build tools.
- **Provider interface:** the same code runs on a free local model for tests and on the paid API for users. This avoids lock-in and token costs while developing.
- **JSON tool protocol for agents:** works on every model, unlike vendor-specific function calling.
- **Rules for eligibility:** arithmetic must be exact and explainable.

## Costs

- Two languages (Python, JavaScript) to maintain.
- SQLite and PostgreSQL differ in small ways; CI should run PostgreSQL tests in a later phase.
