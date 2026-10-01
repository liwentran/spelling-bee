# 🐝 Spelling Bee

A two-screen web app for running custom spelling bees. Open the **TV Display** on your big screen and the **Phone Controller** on your phone — they sync in real-time via WebSockets.

## Quick Start

```bash
# 1. Start locally (opens an SSH tunnel to the droplet DB)
make up

# 2. Open in browser
# Setup:      http://localhost:8003/static/setup.html
# Controller: http://localhost:8003/static/control.html  (phone)
# TV Display: http://localhost:8003/static/display.html?session=SESSION_ID  (TV)
```

## How It Works

1. **Setup** (`/static/setup.html`): Create a session, add players, add custom words with definitions/sentences
2. **Controller** (`/static/control.html`): Pick a player → pick a word → start timer → reveal info when asked → judge correct/incorrect
3. **Display** (`/static/display.html?session=ID`): Shows the word, player info, timer (traffic light), results, and scoreboard on the TV

## Features

- 🖥️ **TV-optimized display** with large text, animations, and traffic light timer
- 📱 **Phone-controlled** with touch-friendly buttons
- 🔊 **Sound effects** (bell for incorrect, chime for correct, ticking countdown)
- 📝 **Custom words** per player with definitions, sentences, part of speech, origin
- 🎮 **Full control** over which word to display, when to reveal info, when to judge
- 🔄 **Sessions** — create, reset, and manage multiple games
- 📊 **Scoreboard** with elimination tracking
- 🤖 **AI-friendly setup** — bulk import words via JSON

## Deployment

Deployed at **http://143.244.162.12:8003/** on the shared droplet. Commit and push to `main`, then run `make deploy`.

## Bulk Word Import Format

```json
[
  {
    "word": "ephemeral",
    "definition": "lasting for a very short time",
    "sentence": "The ephemeral beauty of the cherry blossoms drew crowds every spring.",
    "part_of_speech": "adjective",
    "language_of_origin": "Greek",
    "difficulty": 3,
    "player_name": "Alice"
  },
  {
    "word": "apiary",
    "definition": "a place where bees are kept",
    "difficulty": 3,
    "team_name": "Honeybees"
  }
]
```

Use `player_name` to give a word to one player, `team_name` to put it in a team's pool, or neither for the shared session pool.

## Example Data

`make seed` creates two demo sessions (safe to re-run; existing ones are skipped):

- **Example: Team Bee** — Honeybees vs Bumblebees, 4 players with bios, player words, team-pool words, and a shared tiebreaker pool
- **Example: Classroom Elimination Bee** — 3 solo players, elimination mode, 60s timer, 4th-grade word pool

## Tech Stack

- **Backend**: FastAPI + SQLModel + Alembic + PostgreSQL
- **Frontend**: Plain HTML/JS/CSS + Tailwind CSS (CDN)
- **Real-time**: WebSockets
- **Database**: PostgreSQL (`general-db` on `dev-network`)

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` | Open the DB tunnel and run the app locally with reload on :8003 |
| `make down` | Stop the local app |
| `make tunnel` | Open the SSH tunnel to the droplet DB on :5433 |
| `make migrate` | Run database migrations |
| `make seed` | Migrate, then add example sessions (`backend/seed_examples.py`) |
| `make db-shell` | Open a psql shell to the database |
| `make db-status` | List tables in the deployed database |
| `make deploy` | Pull `origin/main` on the droplet and rebuild the container |
| `make logs` | Tail the deployed container's logs |
| `make restart` | Restart the deployed container |
