.PHONY: setup up down logs test lint dev-backend dev-frontend pull-llama zip

setup:            ## create .env with random secrets
	python3 scripts/setup_env.py

up:               ## run website + API + database in Docker
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

dev-backend:      ## run the API on your machine with auto-reload
	cd backend && pip install -r requirements-dev.txt && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm install && npm run dev

pull-llama:       ## download the local Llama model (needs: docker compose --profile local-llm up)
	docker compose exec ollama ollama pull llama3.2

test:             ## run every test suite
	cd backend && python -m pytest -q
	cd bot && python -m pytest -q
	cd extension && npm install --no-audit --no-fund && npm test
	cd frontend && npm install --no-audit --no-fund && npx tsc --noEmit

lint:
	cd backend && ruff check app tests
