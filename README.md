# 🐝 Spelling Bee

A two-screen web app for running custom spelling bees. Open the **TV Display** on your big screen and the **Phone Controller** on your phone — they sync in real-time via WebSockets.

## Quick Start

```bash
# 1. Create the database (one-time)
make db-create

# 2. Build and start
make up

# 3. Open in browser
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
  }
]
```

## Tech Stack

- **Backend**: FastAPI + SQLModel + Alembic + PostgreSQL
- **Frontend**: Plain HTML/JS/CSS + Tailwind CSS (CDN)
- **Real-time**: WebSockets
- **Database**: PostgreSQL (`general-db` on `dev-network`)

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` | Build and start the app |
| `make down` | Stop the app |
| `make logs` | View container logs |
| `make restart` | Restart the container |
| `make shell` | Open a shell in the backend container |
| `make db-create` | Create the `spellingbee` database |
| `make db-shell` | Open a psql shell to the database |
| `make migrate` | Run database migrations |
