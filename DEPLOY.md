# Deploying the Dream Studio backend on Coolify

The backend is a single FastAPI service. It runs on SQLite out of the box and
switches to Postgres via `DATABASE_URL`. Two supported deploy paths:

## Path A — Docker Compose (app + Postgres together) — recommended

Everything comes up as one stack from `docker-compose.yml`.

1. Push this `backend/` folder as its own git repo (already done: `ds-back`).
2. In Coolify: **New Resource → Docker Compose** → connect the `ds-back` repo.
   Coolify auto-detects `docker-compose.yml`.
3. Set environment variables (Coolify → the resource → Environment):
   - `JWT_SECRET` — a long random string (`openssl rand -hex 32`).
   - `POSTGRES_PASSWORD` — any strong password (used by the bundled Postgres).
   - `SEED_ON_START` is already `1` in the compose file.
4. Deploy. Coolify builds the image from the `Dockerfile` and starts `api` + `db`.
5. Health check path: **`/v1/health`** (returns `{"ok": true}`). Port **8000**.
6. Coolify gives the service a public URL. That URL + `/v1` is your API base.

## Path B — Dockerfile only + a Coolify-managed Postgres

1. In Coolify: **New Resource → Application → from the `ds-back` repo**;
   build pack = **Dockerfile** (auto-detected). Port **8000**, health `/v1/health`.
2. Add a **Postgres** database resource in Coolify; copy its connection string.
3. Set env vars: `JWT_SECRET`, `SEED_ON_START=1`, and
   `DATABASE_URL=postgresql://user:pass@host:5432/dbname` (from step 2).
4. Deploy.

## After it's live

- Verify: `curl https://<your-url>/v1/health` → `{"ok": true, ...}`.
- Point every game at it: set `BASE_URL` in each game's
  `autoload/Backend.gd` to `https://<your-url>/v1`, then rebuild/redeploy the
  game client (or tell the game-client Claude Code instance to do it).
- Updating the live game config (difficulty, juice_level, enabled_demos,
  catalog) = edit `seed.py`, push to `ds-back`, and redeploy — `SEED_ON_START`
  re-applies it. Config-as-code; no separate admin panel.

## Notes

- SQLite works for the very first smoke test but lives inside the container and
  is wiped on redeploy — attach Postgres (Path A or B) before any real traffic.
- The Dockerfile runs as a non-root user and includes a container HEALTHCHECK.
- `--workers 2` in the Dockerfile CMD needs Postgres (multiple SQLite writers
  conflict). Raise workers as traffic grows.
