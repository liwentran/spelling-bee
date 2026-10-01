"""Whole-session export/import, designed for round-tripping through an AI assistant.

Import upserts by name (case-insensitive) and never deletes: anything missing from the
JSON is left alone, and only the fields present in the JSON are changed.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict
from database import get_session
from models import Session, Team, Player, Word

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["roster"])

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
    game_mode: Optional[Literal["individual", "team"]] = None
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


def import_roster(db: DbSession, session: Session, roster: RosterImport) -> dict:
    """Upsert teams, players and words into a session. Caller commits."""
    created = {"teams": 0, "players": 0, "words": 0}
    updated = {"teams": 0, "players": 0, "words": 0}
    warnings = []

    if roster.game_mode and roster.game_mode != session.game_mode:
        if session.turns:
            raise HTTPException(status_code=400, detail="Can't change game mode after turns are recorded; reset the session first")
        session.game_mode = roster.game_mode
        db.add(session)

    teams = {t.name.lower(): t for t in db.exec(select(Team).where(Team.session_id == session.id)).all()}
    players = {p.name.lower(): p for p in db.exec(select(Player).where(Player.session_id == session.id)).all()}
    next_team_order = max([t.sort_order for t in teams.values()], default=0) + 1
    next_player_order = max([p.sort_order for p in players.values()], default=0) + 1

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
        db.flush()  # need team.id for its players
        for rp in rt.players:
            upsert_player(rp, team.id, nested=True)

    for rp in roster.players:
        upsert_player(rp)
    db.flush()  # need player ids for word ownership

    existing_words = {(w.word.lower(), w.player_id, w.team_id): w
                      for w in db.exec(select(Word).where(Word.session_id == session.id)).all()}
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
        data = rw.model_dump(exclude_unset=True)
        word = existing_words.get((rw.word.lower(), player_id, team_id))
        if word is None:
            word = Word(session_id=session.id, player_id=player_id, team_id=team_id, word=rw.word)
            _apply(word, data, WORD_FIELDS)
            existing_words[(rw.word.lower(), player_id, team_id)] = word
            created["words"] += 1
        elif _apply(word, data, WORD_FIELDS[1:]):  # skip "word": it's the match key
            updated["words"] += 1
        db.add(word)

    return {"ok": True, "game_mode": session.game_mode, "created": created, "updated": updated, "warnings": warnings}


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
        "game_mode": session.game_mode,
        "teams": [{"name": t.name, "color": t.color,
                   "players": [player_out(p) for p in players if p.team_id == t.id]} for t in teams],
        "players": [player_out(p) for p in players if not p.team_id],
        "words": word_out,
    }


@router.post("/import")
def import_roster_route(session_id: str, roster: RosterImport, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = import_roster(db, session, roster)
    db.commit()
    return result
