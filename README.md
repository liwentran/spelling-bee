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

1. **Setup** (`/static/setup.html`): Create a session, choose **Individual** or **Team** game, add players (and teams), add custom words with definitions/sentences
2. **Controller** (`/static/control.html`): Pick a player (or a team, plus an optional speller) → pick a word → start timer → reveal info when asked → judge correct/incorrect
3. **Display** (`/static/display.html?session=ID`): Shows the word, player info (or the whole team), timer (traffic light), results, and scoreboard on the TV

### Game types

- **👤 Individual**: each player takes their own turns and is scored and eliminated on their own. No team UI.
- **👥 Team**: the controller picks which **team** goes up, and the TV shows every member of that team. The team owns the turn: its score and elimination are the team's. "Who's spelling?" can optionally highlight one member. Every player needs a team.

You can switch the game type until the first turn is played. After that, Reset the session first.

## How to Play

You need three screens. They don't have to be on the same device, but they must all be able to reach the server.

| Screen | Who uses it | Open |
|---|---|---|
| **Setup** | the organizer, before the game | `/static/setup.html` |
| **Controller** | the judge/pronouncer, on a phone | link from **📱 Copy Controller Link** |
| **TV Display** | everyone, on the big screen | link from **📺 Copy Display Link (TV)** |

### 1. Before the game (Setup page)

1. Click **+ New Session**. Enter a name, set the timer (seconds per word), and tick **Elimination Mode** if a miss knocks you out. Choose **👤 Individual** or **👥 Team**, then click **Create**.
2. Click the session in the list to open it. Setup reopens the last session you used. You can change **⏱ Time per word** at the top at any time.
3. **Team game only:** click **+ Add Team** for each team. Give it a name and pick a color.
4. Click **+ Add Player** for each speller. In a team game, choose their team in the dropdown. Every player is listed with their details; click **✏️ Edit** on one to change them.
5. Add words:
   - **+ Add Word**, one at a time. The last dropdown in the form (it starts at "-- Session Pool --") gives the word to one player, a team's pool, or the shared pool.
   - **Bulk Import**, to paste a JSON list of words.
   - **Copy for AI** → ask ChatGPT/Claude to write players, fun facts and words → paste the reply into **Import JSON**.
6. Click **📺 Copy Display Link (TV)** and open it on the TV. Click **📱 Copy Controller Link** and open it on the judge's phone.

### 2. Start the screens

- **TV:** click anywhere on **"Click anywhere to connect and enable audio"**. Browsers block sound and speech until someone clicks, so if you skip this the TV stays silent.
- **Controller:** the controller link opens the session automatically. If you opened `/static/control.html` directly, pick the session in the top dropdown. The dot in the top-right turns **green** when connected.

### 3. Each turn (Controller)

| Step | Individual game | Team game | What the TV shows |
|---|---|---|---|
| 1. Call someone up | Tap the **player's name** under *Select Player* | Tap the **team** under *Select Team*. Optionally tap a member under *Who's spelling?* (tap again to clear) | "Up Next": the player's bio, or the team with a card for every member |
| 2. Pick a word | Tab **Player's** (their words + their team's pool), **Pool**, or **All** → tap a word | Tab **Team's** (team pool + all members' words), **Pool**, or **All** → tap a word | The spelling screen with the word, the player/team name, and the round |
| 3. Say the word | Tap **🔊 Pronounce Word** (repeat as often as asked) | same | The TV speaks the word aloud |
| 4. Start the clock | Tap **▶**. **⏸** pauses, **↺** resets. Change the length with **−15s / +15s** under *Time per word* (only while the clock is stopped; the change is saved for the session) | same | The timer bar runs along the bottom: green → yellow → red, ticking in the last 10 seconds |
| 5. Answer questions | When the speller asks, tap **📖 Definition**, **📝 Sentence**, **🌍 Origin**, **🔤 Part of Speech** or **🔊 Alt. Pronunciations**. Tap again to hide it | same | The hint appears on screen and is read aloud |
| 6. Judge | Tap **✅ CORRECT** or **❌ INCORRECT**. If the clock hits zero, **⏰ TIMEOUT** happens automatically | same | Green confetti, or red/orange with the correct spelling |

Judging records the turn and marks the word **Used** (greyed out), so it isn't picked twice. With Elimination Mode on, a miss eliminates the player, or in a team game the whole team. They then show crossed out on the controller.

Then go back to step 1 for the next speller.

> **Heads-up:** the spelling screen shows the word in large text for the audience. Seat spellers facing away from the TV.

### 4. Between rounds and at the end

- **Next Round ➡**: bumps the round number shown on the TV.
- **Scoreboard**: shows standings on the TV. In a team game, teams are ranked first.
- **Clear Display**: returns the TV to the idle title screen, between turns or at the end.
- **Reset** (Setup page, in the session list): wipes all turns, scores and eliminations, and marks every word unused, so you can replay. You also need it to switch an already-played session between Individual and Team.

## Features

- 🖥️ **TV-optimized display** with large text, animations, and traffic light timer
- 📱 **Phone-controlled** with touch-friendly buttons
- 🔊 **Sound effects** (bell for incorrect, chime for correct, ticking countdown)
- 📝 **Custom words** per player with definitions, sentences, part of speech, origin
- 🎮 **Full control** over which word to display, when to reveal info, when to judge
- 🔄 **Sessions** — create, reset, and manage multiple games
- 📊 **Scoreboard** with elimination tracking
- 👥 **Individual or team games**: team intros show every member, with team scoring and elimination
- 🗣️ **Text-to-speech**: the TV pronounces the word and reads hints aloud as they're revealed
- 🤖 **AI-friendly setup**: export a whole session for ChatGPT/Claude, then paste the edited JSON back in

## Deployment

Deployed at **http://143.244.162.12:8003/** on a DigitalOcean droplet shared with other apps. It runs in the `spelling-bee-backend` container, built from `~/spelling-bee` on the droplet.

```bash
git push origin main   # make deploy refuses if the tree is dirty or unpushed
make deploy            # git pull on the droplet + rebuild only this container
make logs              # tail the deployed container's logs
```

- **Local edits don't go live by themselves.** Only `make deploy` updates the droplet. If a feature works locally but not at the URL above, it hasn't been deployed.
- **Local and production share one database** (`spellingbee` in `general-db`). `make up` runs migrations on startup, so a new migration hits production as soon as you run it locally, even before the code that uses it is deployed. Keep migrations backward compatible, and deploy soon after.
- **Backups:** a nightly cron at 3:00 AM on the droplet (`/root/cafe/backup_db.sh`) dumps every database to [`gs://liwentran.com/db_backups/`](https://console.cloud.google.com/storage/browser/liwentran.com/db_backups) and keeps 7 days locally. The spelling bee files are `spellingbee_db_<timestamp>.dump`. To restore one: `pg_restore -U postgres -d spellingbee --clean <file>`.

## AI Import / Export

In Setup, **Copy for AI** copies the session's JSON plus instructions. Paste it into ChatGPT or Claude and ask for changes, such as "add a third team with 3 players and 5 hard words each" or "fill in fun facts". Then paste the reply into **Import JSON**. It's the same format as `GET`/`POST /api/sessions/{id}/export|import`:

```json
{
  "game_mode": "team",
  "teams": [
    { "name": "Honeybees", "color": "#f59e0b",
      "players": [{ "name": "Maya Chen", "age": "11", "grade": "6th", "school": "Lincoln Middle", "fun_fact": "..." }] }
  ],
  "players": [],
  "words": [
    { "word": "apiary", "definition": "a place where bees are kept", "difficulty": 3, "team_name": "Honeybees" },
    { "word": "mnemonic", "player_name": "Maya Chen" },
    { "word": "weird" }
  ]
}
```

- Teams and players are **matched by name**, case-insensitively. A matching name updates that entry; a new name creates one.
- Only the fields you include change. **Nothing is ever deleted.**
- Words with an unknown `player_name`/`team_name` are skipped, with a warning.
- `players` at the top level are players with no team. A `"team_name"` on one of them assigns it to a team.

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

`make seed` sets up three demo sessions. It's safe to re-run: it goes through the same import as above, so existing sessions are updated in place and anything added by hand is kept.

- **National Spelling Bee Demo**: an individual elimination bee with a 2-minute timer and finalists working through real past Scripps National Spelling Bee winning words (*stichomythia*, *feuilleton*, *nunatak*, …), plus a 12-word championship pool for tiebreakers.
- **Example: Team Bee**: a team game, Honeybees vs Bumblebees, with 3 players per team. The TV team intro shows all three member cards. Each player has their own words, each team has a pool of bee-themed words, and there's a shared tiebreaker pool.
- **Example: Classroom Elimination Bee**: 3 fourth-graders, elimination mode, 60s timer. Each has 3 words tied to their fun fact, plus an 8-word class pool.

## Tech Stack

- **Backend**: FastAPI + SQLModel + Alembic + PostgreSQL
- **Frontend**: Plain HTML/JS/CSS + Tailwind CSS (CDN)
- **Real-time**: WebSockets
- **Database**: PostgreSQL (`general-db` on `dev-network`)

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` (or `make dev`) | Open the DB tunnel and run the app locally with reload on :8003 |
| `make down` | Stop the local app |
| `make tunnel` | Open the SSH tunnel to the droplet DB on :5433 |
| `make migrate` | Run database migrations |
| `make seed` | Migrate, then add example sessions (`backend/seed_examples.py`) |
| `make db-shell` | Open a psql shell to the database |
| `make db-status` | List tables in the deployed database |
| `make deploy` | Pull `origin/main` on the droplet and rebuild the container |
| `make logs` | Tail the deployed container's logs |
| `make restart` | Restart the deployed container |
