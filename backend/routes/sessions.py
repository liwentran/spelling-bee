from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select
from typing import List, Optional, Literal
from pydantic import BaseModel
from database import get_session
from models import Session, Player, Word, Turn

GameMode = Literal["individual", "team"]

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class SessionCreate(BaseModel):
    name: str
    timer_duration_seconds: int = 120
    elimination_mode: bool = False
    game_mode: GameMode = "individual"

class SessionUpdate(BaseModel):
    name: Optional[str] = None
    timer_duration_seconds: Optional[int] = None
    elimination_mode: Optional[bool] = None
    game_mode: Optional[GameMode] = None
    status: Optional[str] = None
    current_round: Optional[int] = None

@router.post("/")
@router.post("")
def create_session(session_data: SessionCreate, db: DbSession = Depends(get_session)):
    session = Session(
        name=session_data.name,
        timer_duration_seconds=session_data.timer_duration_seconds,
        elimination_mode=session_data.elimination_mode,
        game_mode=session_data.game_mode
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/")
@router.get("")
def list_sessions(db: DbSession = Depends(get_session)):
    sessions = db.exec(select(Session)).all()
    return [
        {
            **s.dict(),
            "players_count": len(s.players),
            "words_count": len(s.words),
            "turns_count": len(s.turns)
        }
        for s in sessions
    ]

@router.get("/{session_id}")
def get_session_details(session_id: str, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    players_count = len(session.players)
    words_count = len(session.words)
    turns_count = len(session.turns)
    
    return {
        **session.dict(),
        "players_count": players_count,
        "words_count": words_count,
        "turns_count": turns_count
    }

@router.patch("/{session_id}")
def update_session(session_id: str, session_data: SessionUpdate, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    update_data = session_data.dict(exclude_unset=True)
    if "game_mode" in update_data and update_data["game_mode"] != session.game_mode and session.turns:
        raise HTTPException(status_code=400, detail="Can't change game mode after turns are recorded; reset the session first")
    for key, value in update_data.items():
        setattr(session, key, value)
        
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.delete("/{session_id}")
def delete_session(session_id: str, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}

@router.post("/{session_id}/reset")
def reset_session(session_id: str, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    for turn in session.turns:
        db.delete(turn)
        
    for word in session.words:
        word.used = False
        db.add(word)
        
    for player in session.players:
        player.eliminated = False
        player.elimination_round = None
        db.add(player)

    for team in session.teams:
        team.eliminated = False
        team.elimination_round = None
        db.add(team)
        
    session.status = "setup"
    session.current_round = 1
    # No db.add(session): it's already tracked, and re-adding cascades to the deleted turns (500)
    
    db.commit()
    return {"ok": True}
