from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DbSession, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import get_session
from models import Turn, Session, Player, Word, Team
from scoring import compute_scoreboard

router = APIRouter(prefix="/api/sessions/{session_id}/turns", tags=["turns"])

RESULTS = ("correct", "incorrect", "timeout")

class TurnUpdate(BaseModel):
    round_number: Optional[int] = None
    result: Optional[str] = None

class TurnCreate(BaseModel):
    player_id: Optional[str] = None  # required in individual mode; optional speller in team mode
    team_id: Optional[str] = None  # required in team mode
    word_id: str
    round_number: int
    result: str
    time_taken_seconds: Optional[float] = None

def save_turn(db: DbSession, session: Session, turn_data: TurnCreate) -> Turn:
    """Record a judged attempt: mark the word used and, in elimination mode, eliminate the
    team (team mode) or player (individual mode) on a miss. Caller commits."""
    team_mode = session.game_mode == "team"
    if team_mode and not turn_data.team_id:
        raise HTTPException(status_code=400, detail="team_id is required in team mode")
    if not team_mode and not turn_data.player_id:
        raise HTTPException(status_code=400, detail="player_id is required in individual mode")
    team = db.get(Team, turn_data.team_id) if turn_data.team_id else None
    if turn_data.team_id and (not team or team.session_id != session.id):
        raise HTTPException(status_code=400, detail="Team not found in this session")

    turn = Turn(session_id=session.id, **turn_data.model_dump())
    db.add(turn)

    word = db.get(Word, turn_data.word_id)
    if word:
        word.used = True

    if session.elimination_mode and turn_data.result != "correct":
        loser = team if team_mode else db.get(Player, turn_data.player_id)
        if loser and not loser.eliminated:
            loser.eliminated = True
            loser.elimination_round = turn_data.round_number
    return turn


def delete_turn(db: DbSession, turn: Turn):
    """Undo a judged attempt: the word goes back to unused (unless judged elsewhere) and an
    elimination it caused is lifted. Caller commits."""
    session = db.get(Session, turn.session_id)
    db.delete(turn)
    db.flush()
    word = db.get(Word, turn.word_id)
    if word:
        word.used = db.exec(select(Turn).where(Turn.word_id == word.id)).first() is not None
    rederive_elimination(db, session, turn.team_id, turn.player_id)


def edit_turn(db: DbSession, turn: Turn, round_number: Optional[int] = None, result: Optional[str] = None):
    """Correct a judged attempt's round or result after the fact. Caller commits."""
    if result is not None:
        if result not in RESULTS:
            raise HTTPException(status_code=400, detail=f"result must be one of {', '.join(RESULTS)}")
        turn.result = result
    if round_number is not None:
        if round_number < 1:
            raise HTTPException(status_code=400, detail="round_number must be at least 1")
        turn.round_number = round_number
    db.flush()
    rederive_elimination(db, db.get(Session, turn.session_id), turn.team_id, turn.player_id)


def rederive_elimination(db: DbSession, session: Session, team_id: Optional[str], player_id: Optional[str]):
    """Set the turn owner's eliminated status from their remaining misses, so undo/edit never strands anyone."""
    if session.game_mode == "team":
        owner = db.get(Team, team_id) if team_id else None
        owner_turns = db.exec(select(Turn).where(Turn.team_id == team_id)).all() if owner else []
    else:
        owner = db.get(Player, player_id) if player_id else None
        owner_turns = db.exec(select(Turn).where(Turn.player_id == player_id)).all() if owner else []
    if not owner:
        return
    misses = [t for t in owner_turns if t.result != "correct"]
    owner.eliminated = bool(session.elimination_mode and misses)
    owner.elimination_round = min(t.round_number for t in misses) if owner.eliminated else None


@router.post("/")
@router.post("")
def record_turn(session_id: str, turn_data: TurnCreate, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    turn = save_turn(db, session, turn_data)
    db.commit()
    db.refresh(turn)
    return turn


@router.patch("/{turn_id}")
def update_turn(session_id: str, turn_id: str, data: TurnUpdate, db: DbSession = Depends(get_session)):
    turn = db.get(Turn, turn_id)
    if not turn or turn.session_id != session_id:
        raise HTTPException(status_code=404, detail="Turn not found")
    edit_turn(db, turn, data.round_number, data.result)
    db.commit()
    db.refresh(turn)
    return turn


@router.delete("/{turn_id}")
def undo_turn(session_id: str, turn_id: str, db: DbSession = Depends(get_session)):
    turn = db.get(Turn, turn_id)
    if not turn or turn.session_id != session_id:
        raise HTTPException(status_code=404, detail="Turn not found")
    delete_turn(db, turn)
    db.commit()
    return {"ok": True}

@router.get("/")
@router.get("")
def list_turns(
    session_id: str, 
    player_id: Optional[str] = None,
    round_number: Optional[int] = None,
    db: DbSession = Depends(get_session)
):
    statement = select(Turn).where(Turn.session_id == session_id)
    if player_id is not None:
        statement = statement.where(Turn.player_id == player_id)
    if round_number is not None:
        statement = statement.where(Turn.round_number == round_number)
        
    statement = statement.order_by(Turn.created_at)
    turns = db.exec(statement).all()
    return turns

@router.get("/scoreboard")
def get_scoreboard(session_id: str, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return compute_scoreboard(db, session_id)
