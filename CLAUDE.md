# CLAUDE.md

Guidance for working on this codebase. See README.md for the user-facing overview. Its **How to Play** section is the step-by-step game flow, with exact button labels. Update it whenever you rename, add or move a button, or change what a step does.

## What this is

A two-screen spelling bee app. Three static pages talk to one FastAPI backend:

- **`setup.html`** (laptop): CRUD for sessions, teams, players, and words over REST.
- **`control.html`** (phone, the "judge"): picks the player (or the team, in a team game) and the word, runs the timer, reveals hints, marks results. It sends WebSocket commands.
- **`display.html`** (TV): passive. It renders whatever state the server broadcasts and plays sounds and speech. It needs a click on "Click to start" first, because browsers only allow audio and speech after a user gesture. The spelling view currently shows the word itself, in large text for the audience.

The display and controller both take `?session=ID`, which Setup's copy-link buttons generate. The display needs it. The controller uses it to preselect and open the session, and falls back to its dropdown without it.

## Layout

```
backend/
  main.py            FastAPI app; runs `alembic upgrade head` on startup; serves ../frontend at /static
  models.py          SQLModel tables: Session, Team, Player, Word, Turn
  database.py        lazy engine from DATABASE_URL; get_session() dependency
  ws_manager.py      in-memory GameState per session + WS command handler + broadcast
  scoring.py         compute_scoreboard(): the one scoreboard calculation (REST /turns/scoreboard and WS)
  seed_examples.py   loads /examples/*.json through roster (match by session name)
examples/            example sessions as full JSON definitions (also templates for users/AI)
  routes/            one router per resource, all under /api/sessions/{session_id}/...
    teams.py         also exports validate_team(), used by players.py and words.py
    roster.py        whole-session JSON: GET /{id}/export, POST /{id}/import, POST /api/sessions/import (create);
                     import_roster() upsert + create_session_from_roster(). RosterImport is the format.
  alembic/versions/  hand-written migrations, numbered 001, 002, ... (revision ids are '001', '002')
frontend/
  js/api.js          REST wrappers (one exported function per endpoint)
  js/ws.js           WS connection, auto-reconnect, and command helpers
  js/sounds.js       Web Audio synthesized sounds (no audio files)
  *.html             each page is a single file: Tailwind CDN markup plus one <script type="module">
```

## Running

The DB is Postgres on a remote droplet (`general-db`), reached through an SSH tunnel on port 5433. `backend/.env` holds `DATABASE_URL`.

- `make up` (alias `make dev`): opens the tunnel and runs uvicorn with reload on :8003. The app is at http://localhost:8003/. Only this local server picks up edits automatically. The droplet (http://143.244.162.12:8003) changes only after push + `make deploy`, so a missing feature there usually means "not deployed".
- `make migrate`: runs `alembic upgrade head` against the tunneled DB. Migrations also run automatically on app startup.
- `make seed`: migrates, then runs `backend/seed_examples.py`, which loads every `examples/*.json` (matched by session name, upserted through `roster.py`). Rerunning it updates them in place. To change example data, edit the JSON, not Python. Use these sessions for manual testing, and extend the script when you add features worth demoing.
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
- Backups: root cron runs `/root/cafe/backup_db.sh` at 3:00 AM. It dumps **every database** in `general-db` (`<db>_db_<ts>.dump`, plus `globals_<ts>.sql` for roles) to `/root/cafe/backups` (kept 7 days) and `gs://liwentran.com/db_backups/` (console: https://console.cloud.google.com/storage/browser/liwentran.com/db_backups). The script's source copy is `~/Developer/wyomb-cafe/backup_db.sh`, which isn't tracked in git.
- The wyomb-cafe repo (`~/Developer/wyomb-cafe`) is the cafe app: FastAPI + SvelteKit, with its frontend on Vercel at coffee.liwentran.com.

**Deploying this app.** Push to `origin/main` (https://github.com/liwentran/spelling-bee, public), then run `make deploy`. It refuses to run if the tree is dirty or unpushed. Otherwise it runs `git pull --ff-only && docker-compose up -d --build --no-deps spelling-bee-backend` in `~/spelling-bee`.
- The backend is baked into the image, so code changes need the rebuild. `./frontend` is bind-mounted at `/frontend`, so static files go live on `git pull` alone.
- Migrations run on container startup against `general-db:5432/spellingbee`.
- Only ever target the `spelling-bee-backend` service: always `--no-deps`, never `down`, `docker system prune`, or a bare `up` that could touch other projects.
- Run a single uvicorn worker with no `--reload`, because `GameState` is in memory and a restart resets live games.

## Testing

There is no test suite. Verify changes against a throwaway DB, never the real one.

**⚠ The real DB is shared with production.** Local `make up` (via the tunnel) and the droplet container both use `general-db/spellingbee`. `make up` runs with `--reload`, and the app runs `alembic upgrade head` on every startup. So **while `make up` is running, saving a new migration or model change under `backend/` immediately migrates the production DB**, possibly halfway through your edits. Either stop `make up` first, or develop in a copy (`rsync -a --exclude .venv --exclude __pycache__ backend frontend <scratch>/work/`) and copy the files back only once they're tested, migration file first. New migrations must also keep the *currently deployed* code working: add columns with `server_default`, and don't drop or rename anything the old code reads.

1. Start a throwaway Postgres: `initdb` + `pg_ctl -o "-p 5499 -k ''"` (TCP only; macOS limits socket path length).
2. Point `DATABASE_URL` at it and run `alembic upgrade head`. Then `downgrade -1` and `upgrade head` to test the round trip, and check `alembic_version` at each step rather than trusting the log output.
3. Use FastAPI `TestClient` (`PYTHONPATH=. uv run --no-project --with-requirements requirements.txt --with httpx2 python test.py`) for REST and WS.
4. For UI flows, use Playwright (`uv run --with playwright`). Drive setup, controller and display as three pages at once, stub `SpeechSynthesis.prototype.speak` to capture what the TV says, and remember `innerText` applies CSS `uppercase`.
5. After rebuilding the examples with `make seed`, smoke-test http://localhost:8003/.

The shell is **zsh, which doesn't word-split unquoted variables**: `R="uv run ..."; $R alembic ...` runs a command literally named `uv run ...` and fails silently inside pipelines. Use shell functions instead.

## Game modes

`Session.game_mode` is `individual` (the default) or `team`. It's locked once the session has turns: PATCH or import returns 400 until a Reset.

| | Individual | Team |
|---|---|---|
| Turn owner | `Turn.player_id` (required) | `Turn.team_id` (required). `player_id` is the optional speller |
| Elimination (`elimination_mode`) | `Player.eliminated` | `Team.eliminated` (one miss knocks out the whole team) |
| Controller | Select Player → `SET_ACTIVE_PLAYER` + `SHOW_PLAYER_INTRO` | Select Team → `SET_ACTIVE_TEAM` + `SHOW_TEAM_INTRO`, then the optional speller via `SET_ACTIVE_PLAYER` (doesn't change `display_mode`) |
| "Player's"/"Team's" word tab | player's words + their team's pool | team pool + every member's words |
| TV intro | `player_intro` | `team_intro`: team name and a card per member |
| Scoreboard | player rows, plus team cards if teams exist | ranked team rows first, then player rows (speller turns) |
| Setup UI | team UI hidden (existing team data is kept) | Teams card shown; ⚠ on unassigned players |

Both modes share the same frontend pages, which branch on `game_mode`: the controller reads it from the session and from `state.game_mode`. When you add a feature, decide what it does in each mode.

## Data model

- Everything hangs off `Session`. Deleting a session cascades to everything (ORM `cascade_delete=True` plus DB `ON DELETE CASCADE`).
- `Team` is optional. `Player.team_id` and `Word.team_id` are nullable with `ON DELETE SET NULL`, so deleting a team unassigns its players and words.
- Word ownership has three tiers, and the UI keeps them mutually exclusive:
  - `player_id` set: belongs to that player.
  - only `team_id` set: in that team's pool.
  - both null: in the session pool.

  In the controller, the "Player's" tab shows the player's own words plus their team's pool. The "Pool" tab shows only the session pool.
- `Turn` records a judged attempt. `POST /turns` also marks the word `used` and, in elimination mode, eliminates the player (individual) or the team (team) on a non-correct result. Reset clears turns and both kinds of elimination.
- **Session JSON** (`routes/roster.py`, model `RosterImport`) is the full definition: session settings (`name`, `game_mode`, `timer_duration_seconds` 15–600, `elimination_mode`), teams, players and words. Export emits all of it. Import applies only what is present, and `null` settings mean "leave as is". If you add a Session field users should control, add it to `RosterImport`, `SESSION_FIELDS`, the export, `JSON_RULES`/`BLANK_TEMPLATE` in setup.html, and the README field table.
- **Roster import** upserts teams, players and words **by name, case-insensitively**. It never deletes, and never renames teams or players, because their names are the match key (the session `name` setting does rename the session). Only the fields present in the JSON change: `model_dump(exclude_unset=True)` plus `_apply()`. Words match on (text, owner). The Setup "Copy for AI" instructions describe these rules, so keep them in sync if you change the semantics.
- **SQLAlchemy pitfall:** after `db.delete()`-ing children, don't `db.add()` an already-persistent parent whose loaded collection still holds them. A lazy load in between autoflushes the deletes, and the re-add's save-update cascade then raises "Instance … has been deleted". This is why Reset returned a 500 whenever turns existed. Tracked objects don't need `db.add()` at all.
- `Session.status` and `current_round` exist in the DB, but the live round number is `GameState.round_number`, which is in memory.
- Timestamps are timezone-aware UTC (`datetime.now(timezone.utc)`).

## Real-time protocol (`ws_manager.py` ↔ `js/ws.js`)

- `GameState` lives **in process memory**, keyed by session id. It is lost on restart and not shared across workers, so keep to one uvicorn worker.
- The client sends `{type: COMMAND, ...}`. The server mutates state and broadcasts `{type: "STATE_UPDATE", state}` to every socket in the session. In `scoreboard` mode the broadcast also includes `scoreboard` (per player) and `team_scoreboard`.
- `state.player`, `state.team` and `state.word` are dicts that `_fetch_player`/`_fetch_team`/`_fetch_word` cache at selection time. `state.team` includes `members` (each built by `_player_dict`). `state.game_mode` is re-read from the DB on connect and on `CLEAR_DISPLAY`. If you add a field the display needs, add it to these fetchers.
- Fire-and-forget commands broadcast their own message type and skip the state update. `PLAY_SOUND` broadcasts `{type: "PLAY_SOUND", sound}`. `PRONOUNCE_WORD` broadcasts `{type: "PRONOUNCE_WORD", word, rate}`, and the display speaks it with the Web Speech API. The server takes the word text from the current state, not from the client.
- The **controller owns the timer**. It counts down locally and sends `UPDATE_TIMER` every second. The display only renders it.
- **Timer ticks must not redraw views.** Each tick broadcasts the full state, so `display.html` (`lastViewKey`) and `control.html` (`lastListKey`) compare the state minus `timer_*` and skip re-rendering when only the timer changed. `switchView` replays the entrance animation only when the screen actually changes. Without this the TV flashes every second. Keep any new per-tick field out of those keys.
- **Timer length** is `Session.timer_duration_seconds`. It's edited in Setup or with the controller's −15s/+15s, which also sends `RESET_TIMER {duration}`, and that sets `GameState.timer_duration`. `_sync_session_settings` re-reads it, along with `game_mode`, on connect and on `CLEAR_DISPLAY`. The TV's bar colors are percentages of `timer_duration`, so it must match the session.
- `display_mode` is one of `idle | player_intro | team_intro | spelling | result | scoreboard`, and drives which view `display.html` shows.
- When the controller reveals a hint, the display also speaks it. `speakNewHints` diffs `revealed_info` for the same word.

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
- **User-entered colors** (team colors) go into `style=` attributes only through the `teamColor()` hex validator, which is defined in each page. Text from imports or AI can contain anything. New display code escapes it with `esc()`, but older templates in setup/control still interpolate names unescaped.
