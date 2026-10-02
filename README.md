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
4. Click **+ Add Player** for each speller. In a team game, choose their team in the dropdown. Every player is listed with their details; click **✏️ Edit** on one to change them, or **Bulk Edit** to edit them all as JSON.
5. Add words:
   - **+ Add Word**, one at a time. The last dropdown in the form (it starts at "-- Session Pool --") gives the word to one player, a team's pool, or the shared pool.
   - **Bulk Edit**, to edit or paste the whole word list as JSON. **📄 Load example** shows the format. Players have a **Bulk Edit** too.
   - **Copy for AI** → ask ChatGPT/Claude to write players, fun facts and words → paste the reply into **Import JSON**.
6. Click **📺 Copy Display Link (TV)** and open it on the TV. Click **📱 Copy Controller Link** and open it on the judge's phone. The **↗** next to each opens it in a new tab on this computer.

### 2. Start the screens

- **TV:** click anywhere on **"Click anywhere to connect and enable audio"**. Browsers block sound and speech until someone clicks, so if you skip this the TV stays silent. You'll hear one test beep when sound is working. If the browser still blocks sound, a red **🔇 Sound is off** button appears in the corner; click it. If there's no beep and no button, check the TV's volume, whether the browser tab is muted, and on an iPhone/iPad the silent switch.
- **Controller:** the controller link opens the session automatically. If you opened `/static/control.html` directly, pick the session in the top dropdown. The dot in the top-right turns **green** when connected.

### 3. Each turn (Controller)

| Step | Individual game | Team game | What the TV shows |
|---|---|---|---|
| 1. Call someone up | Tap **Next up: *name* ➡**, or tap any **player's name** under *Select Player* | Tap **Next up: *team* ➡**, or tap any **team** under *Select Team*. The whole team spells together as a chain, one letter each | "Up Next": the player's bio, or the team with a card for every member |
| 2. Pick a word | Tab **Player's** (their words + their team's pool), **Pool**, or **All** → tap a word, or **🎲 Random** for an unused word from that tab | Tab **Team's** (team pool + all members' words), **Pool**, or **All** → tap a word, or **🎲 Random** | The spelling screen with the word, the player/team name, and the round |
| 3. Say the word | Tap **🔊 Pronounce Word** (repeat as often as asked). **🐢 2× slower** and **🐌 3× slower** say it again, slowly | same | The TV speaks the word aloud |
| 4. Start the clock | Tap **▶**. **⏸** pauses, **↺** resets. Change the length with **−15s / +15s** under *Time per word* (only while the clock is stopped; the change is saved for the session) | same | The timer bar runs along the bottom: green → yellow → red. Every 30 seconds it beeps once per 30 seconds left (3 beeps = 1:30 left, 2 = 1:00, 1 = 0:30), then ticks through the last 10 seconds |
| 5. Answer questions | When the speller asks, tap **📖 Definition**, **📝 Sentence**, **🌍 Origin**, **🔤 Part of Speech** or **🔊 Alt. Pronunciations**. Tap again to hide it | same | The hint appears on screen and is read aloud |
| 6. Judge | Tap **✅ CORRECT** or **❌ INCORRECT**. If the clock hits zero, **⏰ TIMEOUT** happens automatically | same | Who spelled, the whole screen turns green (with confetti), red, or orange for a timeout, with the correct spelling, and their running score |

Judging saves the turn and marks the word **Used** (greyed out), so it isn't picked twice. Each word can be judged only once; the judge buttons grey out until you pick the next word. With Elimination Mode on, a miss eliminates the player, or in a team game the whole team. They then show crossed out on the controller.

**Tapped the wrong result?** Tap **↩ Undo** under the judge buttons. It deletes that turn and gives back the score, any elimination, and the word's Used mark. It also puts that team or player and word back on the TV so you can judge again. This works even after you've moved on to the next team.

Then go back to step 1. Teams or players who have already gone this round get a **✓**, and the line under the list reads e.g. *Round 2 · 1 of 3 teams done*.

**Fixing an older score:** every word that has been judged shows its round, result and who spelled it, e.g. **R1 · ❌ Red**. Tap the **⋯** next to it to move it to another round, change it to ✅ Correct / ❌ Incorrect / ⏰ Timeout, or **Remove score** (the word goes back to unused). Then tap **Save**. Scores, eliminations and round progress update to match.

> **Showing or hiding the word:** under **Show the word** on the controller, pick one of three modes:
> - **👁 Show**: the whole word on the TV and the phone.
> - **📱 Hide on phone** (default): the TV shows the whole word for the audience, but the judge's phone shows only the first letter, so nobody can read it over the judge's shoulder.
> - **🙈 Hide on both**: the TV and the phone show only the first letter (the rest blurred) and the definition, so spellers can face the TV.
>
> Whenever the phone hides words, press and hold **👁 Hold to peek at words** to see them; they hide again when you let go. The phone remembers your choice, and the TV always shows the full word on the result screen.

### 4. Between rounds and at the end

A **round** is one word for each team (or player) still in the game. When everyone has gone, the controller says *Round N complete*.

- **Team order** (team games): on the controller, hold a team and drag it to reorder, or tap **🔀 Shuffle** for a random order. That order is the turn order and is also how the TV scoreboard lists teams.
- **Scoreboard**: shows standings on the TV, ranked by words spelled correctly, then by fewest misses. Eliminated teams/players go to the bottom. Team rows list their players in small text, and the Active/Eliminated labels only appear in elimination games.
- **Next Round ➡**: starts the next round. The TV shows the new round number and the ✓ marks clear. If someone hasn't gone yet, it asks you first.
- **⬅ Prev Round**: goes back one round (e.g. if Next Round was pressed by mistake). Who has already gone that round comes back from the saved turns.
- **Winning:** with Elimination Mode on, once only one team (or player) is left standing, the TV and the controller show **🏆 *name* wins!** Without elimination, play as many rounds as you like; the top of the scoreboard wins.
- Scores and the round number are saved, so refreshing a screen or restarting the server doesn't lose the game.
- **Clear Display**: returns the TV to the idle title screen, between turns or at the end.
- **Reset** (Setup page, in the session list): wipes all turns, scores and eliminations, and marks every word unused, so you can replay. You also need it to switch an already-played session between Individual and Team.

## Features

- 🖥️ **TV-optimized display** with large text, animations, and traffic light timer
- 📱 **Phone-controlled** with touch-friendly buttons
- 🔊 **Sound effects** (bell for incorrect, chime for correct, time-left beeps every 30 seconds, ticking countdown)
- 📝 **Custom words** per player with definitions, sentences, part of speech, origin
- 🎮 **Full control** over which word to display, when to reveal info, when to judge
- 🔄 **Sessions** — create, reset, and manage multiple games
- 📊 **Scoreboard** with elimination tracking
- 🔠 **Words always fit**: long words and names shrink to fit the TV
- 👥 **Individual or team games**: team intros show every member, with team scoring and elimination
- 🗣️ **Text-to-speech**: the TV pronounces the word and reads hints aloud as they're revealed
- 🤖 **Sessions as JSON**: define a whole bee (settings, teams, players, words) in one JSON document. Have ChatGPT/Claude write or edit it, then paste it in

## Deployment

Deployed at **https://bee.liwentran.com/** on a DigitalOcean droplet shared with other apps. Caddy serves the domain over https and proxies it to port 8003; `http://143.244.162.12:8003/` also still works, but share the https link, because some networks block port 8003 and some browsers refuse plain http. It runs in the `spelling-bee-backend` container, built from `~/spelling-bee` on the droplet.

```bash
git push origin main   # make deploy refuses if the tree is dirty or unpushed
make deploy            # git pull on the droplet + rebuild only this container
make logs              # tail the deployed container's logs
```

- **Local edits don't go live by themselves.** Only `make deploy` updates the droplet. If a feature works locally but not at the URL above, it hasn't been deployed.
- **Local and production share one database** (`spellingbee` in `general-db`). `make up` runs migrations on startup, so a new migration hits production as soon as you run it locally, even before the code that uses it is deployed. Keep migrations backward compatible, and deploy soon after.
- **Backups:** a nightly cron at 3:00 AM on the droplet (`/root/cafe/backup_db.sh`) dumps every database to [`gs://liwentran.com/db_backups/`](https://console.cloud.google.com/storage/browser/liwentran.com/db_backups) and keeps 7 days locally. The spelling bee files are `spellingbee_db_<timestamp>.dump`. To restore one: `pg_restore -U postgres -d spellingbee --clean <file>`.

## Defining a Session in JSON

A whole session can be one JSON document: its name, game type, time per word, elimination setting, teams, players and words. The same format is used everywhere:

| Where | What it does |
|---|---|
| Setup → **+ New Session** → **From JSON** | Create a brand-new session from JSON (`POST /api/sessions/import`). **Copy blank template for AI** gives ChatGPT/Claude the format and rules to write one for you. |
| Setup → **Copy for AI** / **Import JSON** | Copy the open session's complete JSON as a starting point, have an AI edit it, and paste it back. The session is **replaced** to match (`GET`/`POST /api/sessions/{id}/export\|import`). |
| [`examples/*.json`](examples/) | The demo sessions, loaded by `make seed`. Copy one as a starting point. |

```json
{
  "name": "Spring Team Bee",
  "game_mode": "team",
  "timer_duration_seconds": 90,
  "elimination_mode": true,
  "teams": [
    { "name": "Honeybees", "color": "#f59e0b",
      "players": [{ "name": "Maya Chen", "age": "11", "grade": "6th", "school": "Lincoln Middle", "fun_fact": "..." }] }
  ],
  "players": [],
  "words": [
    { "word": "apiary", "definition": "a place where bees are kept", "sentence": "...", "part_of_speech": "noun",
      "language_of_origin": "Latin", "alternate_pronunciations": "AY-pee-air-ee", "difficulty": 3, "team_name": "Honeybees" },
    { "word": "mnemonic", "player_name": "Maya Chen" },
    { "word": "weird" }
  ]
}
```

| Field | Meaning |
|---|---|
| `name` | Session name. Required when creating; on import into an open session it renames it. |
| `game_mode` | `"individual"` or `"team"`. Can't change after the first turn until you Reset. |
| `timer_duration_seconds` | Time per word, 15–600. |
| `elimination_mode` | `true` if a miss knocks out the speller, or the whole team in a team game. |
| `teams[].players` | Team members, in a team game. |
| `players` | Players with no team, in an individual game. A `"team_name"` on one of them assigns them to a team. |
| `words[]` | `player_name` gives a word to one player, `team_name` puts it in a team's pool, neither puts it in the shared pool. `difficulty` is 1–5. |

Import rules (into an existing session):
- **The JSON replaces the session.** The `teams`, `players` and `words` lists are the complete set: anything in the session that's missing from them is **removed**. That's what makes copy → edit → import work, including deletions.
- **You're asked first.** Before removing anything, Setup lists exactly what will go, plus any recorded turns that go with it. Cancel and nothing changes.
- **Matching keeps history.** Teams and players are matched by name (case-insensitively), and words by their text. A matched entry is updated in place, so it keeps its scores, turns and "used" status, even if a word moves to a different player.
- **Omitted sections are left alone.** A JSON with no `"words"` key leaves words untouched, so `{"timer_duration_seconds": 60}` only changes the timer. `null` settings are ignored.
- Words with an unknown `player_name`/`team_name` are skipped, with a warning.
- API: `?dry_run=true` previews the changes without saving, and `?mode=merge` only adds and updates, never removing. `make seed` uses merge, so it never deletes anything added by hand.

## Bulk Editing Players and Words

The **Players** and **Words** sections each have a **Bulk Edit** button. It opens a JSON box already filled with the current list, with these buttons:

- **⤓ Load current**: refill the box with what's in the session now. This is your starting point.
- **📄 Load example**: a ready template using your session's real team and player names.
- **📋 Copy**: copy the box, for example to paste into ChatGPT/Claude.
- **Save (replace)**: the list becomes exactly what's in the box. You're asked to confirm anything that would be removed.
- **Add only**: add new entries and update matching ones; nothing is removed.

Players are one flat list. In a team game, give each player a `team_name`:

```json
[
  { "name": "Maya Chen", "age": "11", "grade": "6th", "school": "Lincoln Middle", "fun_fact": "...", "team_name": "Honeybees" },
  { "name": "Priya Patel", "grade": "6th", "team_name": "Bumblebees" }
]
```

Each word goes to exactly one place: a player (`player_name`), a team's pool (`team_name`), or, with neither, the shared session pool.

```json
[
  { "word": "ephemeral", "definition": "lasting for a very short time", "sentence": "...", "part_of_speech": "adjective",
    "language_of_origin": "Greek", "difficulty": 3, "player_name": "Maya Chen" },
  { "word": "apiary", "definition": "a place where bees are kept", "difficulty": 3, "team_name": "Honeybees" },
  { "word": "pneumonia", "definition": "a lung infection", "difficulty": 4 }
]
```

Every JSON box in Setup has a **📄 Load example** button: Bulk Edit (players and words), **Import JSON** (whole session) and **New Session → From JSON**.

## Example Data

`make seed` loads every file in [`examples/`](examples/) (`national-bee.json`, `team-bee.json`, `classroom-bee.json`). It's safe to re-run: sessions are matched by name and updated in place, and anything added by hand is kept. To add an example, drop another JSON file there.

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
