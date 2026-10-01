from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select
from typing import List, Optional
from pydantic import BaseModel
from database import get_session
from models import Session, Player, Word, Turn

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

class SessionCreate(BaseModel):
    name: str
    timer_duration_seconds: int = 120
    elimination_mode: bool = False

class SessionUpdate(BaseModel):
    name: Optional[str] = None
    timer_duration_seconds: Optional[int] = None
    elimination_mode: Optional[bool] = None
    status: Optional[str] = None
    current_round: Optional[int] = None

@router.post("/")
@router.post("")
def create_session(session_data: SessionCreate, db: DbSession = Depends(get_session)):
    session = Session(
        name=session_data.name,
        timer_duration_seconds=session_data.timer_duration_seconds,
        elimination_mode=session_data.elimination_mode
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/")
@router.get("")
def list_sessions(db: DbSession = Depends(get_session)):
    sessions = db.exec(select(Session)).all()
    return sessions

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
        
    session.status = "setup"
    session.current_round = 1
    db.add(session)
    
    db.commit()
    return {"ok": True}
