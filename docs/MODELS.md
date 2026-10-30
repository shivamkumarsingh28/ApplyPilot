# AI models

ApplyPilot talks to AI models through **one small interface** (`backend/app/services/llm/base.py`). Switching models is a settings change.

## The four providers

| `LLM_PROVIDER` | Class | Where the model runs | Cost |
|---|---|---|---|
| `mock` | `MockProvider` | Nowhere. Returns nothing; services use their rule-based paths. | Free |
| `llama_local` | `OllamaProvider` | Your computer, through Ollama | Free (your hardware) |
| `meta` | `MetaProvider` | Meta Model API, default model `muse-spark-1.3` | Pay per token |
| `openai_compat` | `OpenAICompatProvider` | Any server with an OpenAI-style `/chat/completions` | Depends on host |

`llama_local`, `meta` and `openai_compat` all use the same HTTP client. They differ only in the address, key and model name. That is why one code path serves all of them (and why OpenAI itself works with `openai_compat`).

## Why two main choices?

- **Development:** use `llama_local` so you never run out of API tokens while building and testing.
- **Production:** use `meta` for better quality, speed and image reading.

## Setting up Llama locally

```bash
# 1. Install Ollama: https://ollama.com
ollama pull llama3.2            # small, good for laptops
ollama pull llama3.2-vision     # optional: reads images (scanned notices)
ollama pull nomic-embed-text    # optional: better search vectors
```

`.env`:

```
LLM_PROVIDER=llama_local
OLLAMA_MODEL=llama3.2
OLLAMA_VISION_MODEL=llama3.2-vision
EMBEDDING_PROVIDER=api
EMBEDDING_MODEL=nomic-embed-text
```

With Docker: `docker compose --profile local-llm up --build`, then `make pull-llama`.

## Using the Meta Model API

```
LLM_PROVIDER=meta
META_API_KEY=your-key
META_MODEL=muse-spark-1.3
META_API_BASE=https://api.meta.ai/v1
```

The client sends `POST {META_API_BASE}/chat/completions` with `Authorization: Bearer <key>`. Images are sent as `image_url` data URLs. This matches Meta's public description of the API, but **we have not run it against a live key yet**. Check Meta's current documentation if a call fails.

## What each model is used for

| Task | File | Without a model |
|---|---|---|
| Read scanned notices | `pdf_text.py` | Clear error asking you to set a vision model |
| Extract facts | `extraction.py` | Rules only |
| Answer questions | `rag.py` | Copies the best sentences from the notice |
| Choose an agent | `agents/supervisor.py` | Keyword router |
| Choose a tool | `agents/runner.py` | Fixed rules per agent |
| Suggest form fields the rules missed | `form_mapper.py` | Skipped |

Small local models make more mistakes than big ones. That is why facts from rules are never silently replaced by the model (`extraction.merge`), and eligibility never uses a model.

## Add another provider

1. Subclass `LLMProvider` (or `OpenAICompatProvider` if it speaks the OpenAI format).
2. Add settings to `core/config.py`.
3. Add a branch in `llm/factory.py`.
4. Add a test using `httpx.MockTransport` (see `tests/test_llm_providers.py`).

## Embeddings and SAM

- Search vectors: default is a built-in offline method (`EMBEDDING_PROVIDER=hash`). Set `api` to use your model server's `/embeddings`.
- Background removal: default is OpenCV GrabCut. `SEGMENTER=meta_sam` calls SAM 3.1 at `SAM_ENDPOINT`. The adapter expects `POST {image: base64, prompt}` and `{mask: base64 PNG}`. Meta's real SAM 3.1 request format may differ, so you may need a small proxy. If the call fails, the app falls back to OpenCV automatically.
