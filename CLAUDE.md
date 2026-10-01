# CLAUDE.md

Guidance for working on this codebase. See README.md for the user-facing overview.

## What this is

A two-screen spelling bee app. Three static pages talk to one FastAPI backend:

- **`setup.html`** (laptop): CRUD for sessions, teams, players, and words over REST.
- **`control.html`** (phone, the "judge"): picks the player and word, runs the timer, reveals hints, marks results. It sends WebSocket commands.
- **`display.html`** (TV): passive. It renders whatever state the server broadcasts and plays sounds and speech. It needs a click on "Click to start" first, because browsers only allow audio and speech after a user gesture.

## Layout

```
backend/
  main.py            FastAPI app; runs `alembic upgrade head` on startup; serves ../frontend at /static
  models.py          SQLModel tables: Session, Team, Player, Word, Turn
  database.py        lazy engine from DATABASE_URL; get_session() dependency
  ws_manager.py      in-memory GameState per session + WS command handler + broadcast
  routes/            one router per resource, all under /api/sessions/{session_id}/...
    teams.py         also exports validate_team(), used by players.py and words.py
  alembic/versions/  hand-written migrations, numbered 001, 002, ... (revision ids are '001', '002')
frontend/
  js/api.js          REST wrappers (one exported function per endpoint)
  js/ws.js           WS connection, auto-reconnect, and command helpers
  js/sounds.js       Web Audio synthesized sounds (no audio files)
  *.html             each page is a single file: Tailwind CDN markup plus one <script type="module">
```

## Running

The DB is Postgres on a remote droplet (`general-db`), reached through an SSH tunnel on port 5433. `backend/.env` holds `DATABASE_URL`.

- `make up`: opens the tunnel and runs uvicorn with reload on :8003. The app is at http://localhost:8003/.
- `make migrate`: runs `alembic upgrade head` against the tunneled DB. Migrations also run automatically on app startup.
- `make seed`: migrates, then runs `backend/seed_examples.py`, which adds two example sessions (a team bee and a solo elimination bee). It skips any session whose name already exists. Use these sessions for manual testing, and extend the script when you add features worth demoing.
- `make db-shell` / `make db-status`: psql on the droplet.
- `make deploy` / `make logs` / `make restart`: see "Droplet & deployment" below.

## Droplet & deployment

The app is deployed at **http://143.244.162.12:8003/**, with no domain and no HTTPS. The droplet is shared with other apps, so **never touch their containers, directories, databases, Caddy config, or cron.**

- SSH alias `droplet` (`root@143.244.162.12`, in `~/.ssh/config`). The box is tiny: 458 MB RAM, swap in use, about 2.8 GB disk free. Keep images slim and avoid running builds you don't need.
- Use `docker-compose` (v5, hyphenated). `docker compose` isn't installed.
- All app containers join the external Docker network `dev-network`.

| Port | Container | Source dir on droplet | DB | Deploy style |
|------|-----------|-----------------------|----|--------------|
| 5432 (internal, 172.18.0.3) | `general-db` (postgres:15) | – | cafe, wyomb_cafe, budgetapp, beli_scraper, spellingbee | – |
| 8000 | `cafe-backend` | `~/cafe` | cafe | GitHub Actions → Docker Hub `liwentran/cafe-backend` → ssh restart |
| 8001 | `beli-api` | `~/beli-scraper` | beli_scraper | compose build on box |
| 8002 | `budgeting-backend` | `~/budgeting-app` | budgetapp | git clone + compose build on box |
| 8003 | `spelling-bee-backend` | `~/spelling-bee` | spellingbee | git clone + compose build on box (this repo) |

- Caddy (`/etc/caddy/Caddyfile`) proxies `api.liwentran.com` → :8000 and `eats.liwentran.com` → :8001. Spelling bee isn't behind Caddy. If it ever gets a domain, add a block there; Caddy proxies WebSockets automatically, and `ws.js` switches to `wss:` under https.
- `general-db` doesn't publish 5432. Locally you reach it through the tunnel `ssh -L 5433:172.18.0.3:5432 droplet` (`make tunnel`).
- Backups: root cron runs `/root/cafe/backup_db.sh` at 3:00 AM. It dumps **only the `cafe` DB**, to `/root/cafe/backups` and GCS. `spellingbee` isn't backed up.
- The wyomb-cafe repo (`~/Developer/wyomb-cafe`) is the cafe app: FastAPI + SvelteKit, with its frontend on Vercel at coffee.liwentran.com.

**Deploying this app.** Push to `origin/main` (https://github.com/liwentran/spelling-bee, public), then run `make deploy`. It refuses to run if the tree is dirty or unpushed. Otherwise it runs `git pull --ff-only && docker-compose up -d --build --no-deps spelling-bee-backend` in `~/spelling-bee`.
- The backend is baked into the image, so code changes need the rebuild. `./frontend` is bind-mounted at `/frontend`, so static files go live on `git pull` alone.
- Migrations run on container startup against `general-db:5432/spellingbee`.
- Only ever target the `spelling-bee-backend` service: always `--no-deps`, never `down`, `docker system prune`, or a bare `up` that could touch other projects.
- Run a single uvicorn worker with no `--reload`, because `GameState` is in memory and a restart resets live games.

There is no test suite. To verify a change without touching the real DB:
1. Start a throwaway Postgres: `initdb` + `pg_ctl -o "-p 5499 -k ''"` (TCP only; macOS limits socket path length).
2. Point `DATABASE_URL` at it and run `alembic upgrade head`.
3. Use FastAPI `TestClient` (needs `uv run --with httpx2`) for REST and WS. For UI flows, use Playwright (`uv run --with playwright`).

## Data model

- Everything hangs off `Session`. Deleting a session cascades to everything (ORM `cascade_delete=True` plus DB `ON DELETE CASCADE`).
- `Team` is optional. `Player.team_id` and `Word.team_id` are nullable with `ON DELETE SET NULL`, so deleting a team unassigns its players and words.
- Word ownership has three tiers, and the UI keeps them mutually exclusive:
  - `player_id` set: belongs to that player.
  - only `team_id` set: in that team's pool.
  - both null: in the session pool.

  In the controller, the "Player's" tab shows the player's own words plus their team's pool. The "Pool" tab shows only the session pool.
- `Turn` records a judged attempt. `POST /turns` also marks the word `used` and, in elimination mode, eliminates the player on a non-correct result.
- `Session.status` and `current_round` exist in the DB, but the live round number is `GameState.round_number`, which is in memory.
- Timestamps are timezone-aware UTC (`datetime.now(timezone.utc)`).

## Real-time protocol (`ws_manager.py` ↔ `js/ws.js`)

- `GameState` lives **in process memory**, keyed by session id. It is lost on restart and not shared across workers, so keep to one uvicorn worker.
- The client sends `{type: COMMAND, ...}`. The server mutates state and broadcasts `{type: "STATE_UPDATE", state}` to every socket in the session. In `scoreboard` mode the broadcast also includes `scoreboard` (per player) and `team_scoreboard`.
- `state.player` and `state.word` are dicts that `_fetch_player`/`_fetch_word` cache at selection time. They include a nested `team: {id, name, color}`. If you add a field the display needs, add it to these fetchers.
- Fire-and-forget commands broadcast their own message type and skip the state update. `PLAY_SOUND` broadcasts `{type: "PLAY_SOUND", sound}`. `PRONOUNCE_WORD` broadcasts `{type: "PRONOUNCE_WORD", word, rate}`, and the display speaks it with the Web Speech API. The server takes the word text from the current state, not from the client.
- The **controller owns the timer**. It counts down locally and sends `UPDATE_TIMER` every second. The display only renders it.
- `display_mode` is one of `idle | player_intro | spelling | result | scoreboard`, and drives which view `display.html` shows.

To add a command:
1. Add an `elif cmd_type == ...` branch in `handle_command`.
2. Add a helper export at the bottom of `js/ws.js`. Command names must match exactly.
3. If it's a new broadcast type, add an `onX` callback in `ws.js`'s `onmessage`.

## Conventions

- **Routes**: register both `@router.get("/")` and `@router.get("")` so trailing-slash and bare URLs both work. Use pydantic `XCreate`/`XUpdate` models. PATCH applies `dict(exclude_unset=True)`, so an explicit `null` clears a field. Check that a child's `session_id` matches the path, and return 404 if not.
- **New router**: import it and call `include_router` in `main.py`.
- **Static caching**: `main.py` sends `Cache-Control: no-cache` on `/static` so browsers re-check files on every load. Without it, a stale cached `js/api.js` paired with a newer page breaks that page silently. Keep this header unless you add versioned filenames.
- **Migrations**: write them by hand in the style of `001`/`002`: explicit `sa.Column`s, `server_default` for non-null columns, named FK constraints so `downgrade()` can drop them. Bump the revision number sequentially. Always test upgrade → downgrade → upgrade.
- **Frontend**: no build step and no framework. Pages render with template-literal `innerHTML` and inline `onclick="window.fn(...)"` handlers exposed on `window`, because module scope isn't global. After any mutation, re-fetch and re-render (`loadSessionData()` in setup). Keep using that pattern instead of introducing local state syncing.
- **Styling**: Tailwind utility classes via CDN. The TV display uses large `clamp()`/`text-9xl` type and a dark navy/cream palette. The controller is dark, phone-sized, with big touch targets.
- **User-entered colors** (team colors) go into `style=` attributes only through the `teamColor()` hex validator, which is defined in each page. Names are interpolated unescaped, as in the existing code. Keep that in mind if this ever faces untrusted users.
