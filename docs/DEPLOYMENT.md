# Deployment

## Option 1: one server with Docker Compose

1. A Linux server with Docker, a domain name, and ports 80 and 443 open.
2. `git clone` the repo, then `python3 scripts/setup_env.py`.
3. Edit `.env`:
   - `APP_ENV=production`
   - `CORS_ORIGINS=https://your-site.example`
   - `PUBLIC_API_URL=https://api.your-site.example/api/v1` (the address the browser uses)
   - `LLM_PROVIDER=meta` and `META_API_KEY=...`
   - `ADMIN_EMAILS=you@example.com`
4. Put a reverse proxy (Caddy is the easiest) in front, giving HTTPS to the website (port 3000) and the API (port 8000).
5. `docker compose up -d --build`
6. Back up the `db-data` and `file-data` volumes **and** your `.env` (especially `ENCRYPTION_KEY`).

## Option 2: separate services

- Frontend: any Node host or Vercel. Set `NEXT_PUBLIC_API_URL` at build time.
- Backend: any container host. Set the environment from `.env.example`.
- Database: managed PostgreSQL. `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`
- Files: replace `services/storage.py` with an object-storage version (same three functions: `save_file`, `load_file`, `delete_file`).

## Before you launch

Go through the checklist in [SECURITY.md](SECURITY.md). The most important items: HTTPS, your own `ENCRYPTION_KEY`, backups, migrations (Alembic), and a privacy policy.

## Database changes

The app creates tables at start (`create_all`). That is fine for the first version. When you change a table later, add Alembic migrations, because `create_all` does not change existing tables.

## Extension for real users

Add your API address to `host_permissions` in `extension/manifest.json`, zip the folder, and publish it in the Chrome Web Store.
