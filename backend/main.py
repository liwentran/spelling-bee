import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager

from engine import run_migrations

from routes import sessions, teams, players, words, turns, ws

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations on startup
    try:
        run_migrations()
    except Exception as e:
        print(f"Error running migrations: {e}")
    yield

app = FastAPI(title="Spelling Bee API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def no_cache_static(request, call_next):
    # No build step / versioned filenames, so make browsers revalidate (ETag keeps it cheap).
    # Otherwise a stale cached js/api.js can break a freshly loaded page.
    response = await call_next(request)
    if request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache"
    return response

app.include_router(sessions.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(words.router)
app.include_router(turns.router)
app.include_router(ws.router)

# Mount static frontend
frontend_dir = "/frontend"
if not os.path.exists(frontend_dir):
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/static/setup.html")

@app.get("/health")
def health_check():
    return {"status": "ok"}
