# Dream Studio — Platform Backend

One FastAPI service that serves EVERY game in the portfolio. A Claude Code
instance working in this repo owns backend only — never edit game clients
from here. The Godot clients live in the sibling `game-client/` folder/repo.

## Commands

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # run locally (SQLite)
python seed.py                              # apply game catalog + remote configs
python -m pytest tests/ -q                  # MUST pass before any commit/deploy
```

## Architecture

- `app/main.py` — app assembly, CORS, startup (create tables, optional seed)
- `app/db.py` — SQLite by default; set `DATABASE_URL` for Postgres
- `app/models.py` — players, cloud_saves, scores, remote_configs, events, games.
  Every gameplay table is keyed by `game_id`: the backend is multi-game by design.
- `app/auth.py` — device_id → player + JWT (HS256, 30-day expiry)
- `app/routes.py` — all endpoints under `/v1`
- `seed.py` — **config-as-code**: the game catalog and per-game remote configs.
  Idempotent; re-applies configs (bumping version). With `SEED_ON_START=1` it
  runs on every boot, so a redeploy IS the config release mechanism.

## API contract (v1) — clients in the wild depend on this

`POST /v1/auth/device` · `GET|PUT /v1/players/me` · `GET|PUT /v1/saves/{game_id}`
· `POST /v1/scores/{game_id}` · `GET /v1/leaderboards/{game_id}` ·
`GET /v1/config/{game_id}` · `POST /v1/events` · `GET /v1/crosspromo/{game_id}`
· `GET /v1/health`

**Rules:** additive changes only. Never rename/remove a field or endpoint —
shipped APKs cannot be force-updated. Breaking change ⇒ new `/v2` route.
Auth via `Authorization: Bearer <jwt>`; config/crosspromo/health are unauthenticated.

## Adding a new game (the ONLY backend work a new game needs)

1. Add a `GameEntry` dict to `GAMES` in `seed.py` (game_id, name, store URLs).
2. Add its tuning dict to `CONFIGS` in `seed.py`.
3. Run tests, deploy. Done — all endpoints work for the new game_id automatically.

## Deploying on Coolify

1. Push this folder as its own git repo; in Coolify: new app → this repo →
   build pack **Dockerfile** (auto-detected), port **8000**.
2. Health check path: `/v1/health`.
3. Env vars: `JWT_SECRET` (long random string — REQUIRED in prod),
   `SEED_ON_START=1`, and `DATABASE_URL` pointing at a Coolify Postgres
   resource (`postgresql://user:pass@host:5432/db`). SQLite works for the
   first days but lives inside the container — attach Postgres before real traffic.
4. After deploy, put the public URL into each game's `autoload/Backend.gd` `BASE_URL`.

## Known v0.2 limitations (do not silently "fix" — coordinate)

- Scores are client-trusted (bounded ≤1e9). Anti-cheat (server-side validation /
  signed payloads) is a deliberate later step.
- No admin API: catalog/config changes go through seed.py + redeploy (by design).
- No rate limiting yet — add slowapi/nginx limits before any UA push.
