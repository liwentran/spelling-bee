"""Whole-session JSON: settings, teams, players and words in one document.

Designed for round-tripping through an AI assistant and for the example files in /examples.
Entries are matched by name (case-insensitive; words by text) and only fields present
in the JSON change. Import into an existing session defaults to *replace*: lists in the JSON are the complete
set, so entries missing from them are deleted (see import_roster).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field
from database import get_session
from models import Session, Team, Player, Word

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["roster"])
create_router = APIRouter(prefix="/api/sessions", tags=["roster"])  # create a new session from JSON

SESSION_FIELDS = ("name", "timer_duration_seconds", "elimination_mode")
PLAYER_FIELDS = ("name", "age", "grade", "school", "fun_fact")
# Fields an import may change on an existing match; names are the match key, so they're never rewritten
PLAYER_UPDATE_FIELDS = ("age", "grade", "school", "fun_fact", "team_id")
WORD_FIELDS = ("word", "definition", "sentence", "part_of_speech", "language_of_origin", "alternate_pronunciations", "difficulty")

class RosterPlayer(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)  # AI often sends "age": 11
    name: str
    age: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    fun_fact: Optional[str] = None
    team_name: Optional[str] = None  # top-level players only; nested players take their team

class RosterTeam(BaseModel):
    name: str
    color: Optional[str] = None
    players: List[RosterPlayer] = []

class RosterWord(BaseModel):
    word: str
    definition: Optional[str] = None
    sentence: Optional[str] = None
    part_of_speech: Optional[str] = None
    language_of_origin: Optional[str] = None
    alternate_pronunciations: Optional[str] = None
    difficulty: Optional[int] = None
    player_name: Optional[str] = None
    team_name: Optional[str] = None

class RosterImport(BaseModel):
    # Session settings (all optional on import; name is required to create a new session)
    name: Optional[str] = None
    game_mode: Optional[Literal["individual", "team"]] = None
    timer_duration_seconds: Optional[int] = Field(default=None, ge=15, le=600)  # time per word
    elimination_mode: Optional[bool] = None
    teams: List[RosterTeam] = []
    players: List[RosterPlayer] = []
    words: List[RosterWord] = []


def _apply(obj, data: dict, fields) -> bool:
    """Set the given fields from data (only keys present). Returns True if anything changed."""
    changed = False
    for key in fields:
        if key in data and getattr(obj, key) != data[key]:
            setattr(obj, key, data[key])
            changed = True
    return changed


def import_roster(db: DbSession, session: Session, roster: RosterImport, replace: bool = False) -> dict:
    """Apply a session JSON definition. Caller commits (or rolls back for a dry run).

    merge (replace=False): add and update only; nothing is deleted.
    replace: the session ends up matching the JSON. Teams/players/words that are missing from a
      list are deleted, but only for lists present in the JSON (no "words" key = words untouched).
    Either way, entries are matched by name (words by text), so kept ones keep their ids,
    turns, used flags and elimination state.
    """
    created = {"teams": 0, "players": 0, "words": 0}
    updated = {"teams": 0, "players": 0, "words": 0}
    removed = {"teams": [], "players": [], "words": []}
    warnings = []
    present = roster.model_fields_set

    if roster.game_mode and roster.game_mode != session.game_mode:
        if session.turns:
            raise HTTPException(status_code=400, detail="Can't change game mode after turns are recorded; reset the session first")
        session.game_mode = roster.game_mode
    settings = roster.model_dump(exclude_unset=True, include={"name", "timer_duration_seconds", "elimination_mode"})
    settings = {k: v for k, v in settings.items() if v is not None}  # null means "leave as is"
    session_updated = _apply(session, settings, SESSION_FIELDS)
    db.add(session)

    teams = {t.name.lower(): t for t in db.exec(select(Team).where(Team.session_id == session.id)).all()}
    players = {p.name.lower(): p for p in db.exec(select(Player).where(Player.session_id == session.id)).all()}
    next_team_order = max([t.sort_order for t in teams.values()], default=0) + 1
    next_player_order = max([p.sort_order for p in players.values()], default=0) + 1
    kept_teams, kept_players, kept_words = set(), set(), set()

    def upsert_player(rp: RosterPlayer, team_id_from_nesting=None, nested=False):
        nonlocal next_player_order
        data = rp.model_dump(exclude_unset=True)
        if nested:
            data["team_id"] = team_id_from_nesting
        elif "team_name" in data:
            if data["team_name"] is None:
                data["team_id"] = None
            elif data["team_name"].lower() in teams:
                data["team_id"] = teams[data["team_name"].lower()].id
            else:
                warnings.append(f"Player '{rp.name}': unknown team '{data['team_name']}', team left unchanged")
        elif replace:
            data["team_id"] = None  # top-level with no team_name = no team, as in the export
        player = players.get(rp.name.lower())
        if player is None:
            player = Player(session_id=session.id, name=rp.name, sort_order=next_player_order)
            next_player_order += 1
            _apply(player, data, PLAYER_FIELDS + ("team_id",))
            players[rp.name.lower()] = player
            created["players"] += 1
        elif _apply(player, data, PLAYER_UPDATE_FIELDS):
            updated["players"] += 1
        db.add(player)
        kept_players.add(rp.name.lower())

    for rt in roster.teams:
        data = rt.model_dump(exclude_unset=True, exclude={"players"})
        team = teams.get(rt.name.lower())
        if team is None:
            team = Team(session_id=session.id, name=rt.name, color=rt.color, sort_order=next_team_order)
            next_team_order += 1
            teams[rt.name.lower()] = team
            created["teams"] += 1
        elif _apply(team, data, ("color",)):
            updated["teams"] += 1
        db.add(team)
        kept_teams.add(rt.name.lower())
        db.flush()  # need team.id for its players
        for rp in rt.players:
            upsert_player(rp, team.id, nested=True)

    for rp in roster.players:
        upsert_player(rp)
    db.flush()  # need player ids for word ownership

    # Words match by text. Prefer an existing copy with the same owner; otherwise take any unclaimed
    # copy and move it, so reassigning a word keeps its used flag and turn history.
    by_text = {}
    for w in db.exec(select(Word).where(Word.session_id == session.id).order_by(Word.created_at)).all():
        by_text.setdefault(w.word.lower(), []).append(w)
    for rw in roster.words:
        player_id = team_id = None
        if rw.player_name:
            player = players.get(rw.player_name.lower())
            if not player:
                warnings.append(f"Word '{rw.word}': unknown player '{rw.player_name}', skipped")
                continue
            player_id = player.id
        elif rw.team_name:
            team = teams.get(rw.team_name.lower())
            if not team:
                warnings.append(f"Word '{rw.word}': unknown team '{rw.team_name}', skipped")
                continue
            team_id = team.id
        data = {**rw.model_dump(exclude_unset=True), "player_id": player_id, "team_id": team_id}
        candidates = [w for w in by_text.get(rw.word.lower(), []) if w.id not in kept_words]
        word = next((w for w in candidates if (w.player_id, w.team_id) == (player_id, team_id)), None) or \
            (candidates[0] if candidates else None)
        if word is None:
            word = Word(session_id=session.id, player_id=player_id, team_id=team_id, word=rw.word)
            _apply(word, data, WORD_FIELDS)
            db.add(word)
            db.flush()
            by_text.setdefault(rw.word.lower(), []).append(word)
            created["words"] += 1
        elif _apply(word, data, WORD_FIELDS[1:] + ("player_id", "team_id")):  # "word" is the match key
            updated["words"] += 1
        db.add(word)
        kept_words.add(word.id)

    turns_removed = 0
    if replace:
        db.flush()
        db.expire_all()  # reload collections so delete cascades see the reassignments above
        doomed_words = [w for ws in by_text.values() for w in ws if w.id not in kept_words] if "words" in present else []
        doomed_players = [p for k, p in players.items() if k not in kept_players] if present & {"teams", "players"} else []
        doomed_teams = [t for k, t in teams.items() if k not in kept_teams] if "teams" in present else []
        doomed_ids = {w.id for w in doomed_words} | {p.id for p in doomed_players} | {t.id for t in doomed_teams}
        turns_removed = sum(1 for t in session.turns if {t.word_id, t.player_id, t.team_id} & doomed_ids)
        # Words owned by a removed player go with them (cascade), so list them too
        doomed_word_ids = {w.id for w in doomed_words}
        for p in doomed_players:
            doomed_words += [w for w in p.words if w.id not in doomed_word_ids and w.id not in kept_words]
        for w in doomed_words:
            db.delete(w)
        for p in doomed_players:
            db.delete(p)
        for t in doomed_teams:
            db.delete(t)
        removed = {"teams": [t.name for t in doomed_teams], "players": [p.name for p in doomed_players],
                   "words": [w.word for w in doomed_words]}

    return {"ok": True, "session_id": session.id, "game_mode": session.game_mode, "session_updated": session_updated,
            "mode": "replace" if replace else "merge", "created": created, "updated": updated,
            "removed": {k: len(v) for k, v in removed.items()}, "removed_names": removed,
            "turns_removed": turns_removed, "warnings": warnings}


def create_session_from_roster(db: DbSession, roster: RosterImport) -> dict:
    """Create a new session from a full JSON definition. Caller commits."""
    if not roster.name or not roster.name.strip():
        raise HTTPException(status_code=400, detail='"name" is required to create a session')
    session = Session(name=roster.name.strip(), game_mode=roster.game_mode or "individual")
    db.add(session)
    db.flush()
    return import_roster(db, session, roster)


@router.get("/export")
def export_roster(session_id: str, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    teams = db.exec(select(Team).where(Team.session_id == session_id).order_by(Team.sort_order)).all()
    players = db.exec(select(Player).where(Player.session_id == session_id).order_by(Player.sort_order)).all()
    words = db.exec(select(Word).where(Word.session_id == session_id).order_by(Word.created_at)).all()
    team_names = {t.id: t.name for t in teams}
    player_names = {p.id: p.name for p in players}

    player_out = lambda p: {k: getattr(p, k) for k in PLAYER_FIELDS}
    word_out = []
    for w in words:
        entry = {k: getattr(w, k) for k in WORD_FIELDS}
        if w.player_id:
            entry["player_name"] = player_names.get(w.player_id)
        elif w.team_id:
            entry["team_name"] = team_names.get(w.team_id)
        word_out.append(entry)

    return {
        "name": session.name,
        "game_mode": session.game_mode,
        "timer_duration_seconds": session.timer_duration_seconds,
        "elimination_mode": session.elimination_mode,
        "teams": [{"name": t.name, "color": t.color,
                   "players": [player_out(p) for p in players if p.team_id == t.id]} for t in teams],
        "players": [player_out(p) for p in players if not p.team_id],
        "words": word_out,
    }


@router.post("/import")
def import_roster_route(session_id: str, roster: RosterImport, mode: Literal["replace", "merge"] = "replace",
                        dry_run: bool = False, db: DbSession = Depends(get_session)):
    """Default: replace, so the session matches the JSON (copy -> edit -> import workflow).
    ?dry_run=true reports what would change (incl. removals) without saving."""
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = import_roster(db, session, roster, replace=(mode == "replace"))
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return {**result, "dry_run": dry_run}


@create_router.post("/import")
def create_session_route(roster: RosterImport, db: DbSession = Depends(get_session)):
    result = create_session_from_roster(db, roster)
    db.commit()
    return result
