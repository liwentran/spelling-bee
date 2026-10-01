from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DbSession, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import get_session
from models import Turn, Session, Player, Word, Team
from scoring import compute_scoreboard

router = APIRouter(prefix="/api/sessions/{session_id}/turns", tags=["turns"])

class TurnCreate(BaseModel):
    player_id: Optional[str] = None  # required in individual mode; optional speller in team mode
    team_id: Optional[str] = None  # required in team mode
    word_id: str
    round_number: int
    result: str
    time_taken_seconds: Optional[float] = None

@router.post("/")
@router.post("")
def record_turn(session_id: str, turn_data: TurnCreate, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    team_mode = session.game_mode == "team"
    if team_mode and not turn_data.team_id:
        raise HTTPException(status_code=400, detail="team_id is required in team mode")
    if not team_mode and not turn_data.player_id:
        raise HTTPException(status_code=400, detail="player_id is required in individual mode")
    team = db.get(Team, turn_data.team_id) if turn_data.team_id else None
    if turn_data.team_id and (not team or team.session_id != session_id):
        raise HTTPException(status_code=400, detail="Team not found in this session")
        
    turn = Turn(
        session_id=session_id,
        **turn_data.dict()
    )
    db.add(turn)
    
    # Update word used status
    word = db.get(Word, turn_data.word_id)
    if word:
        word.used = True
        db.add(word)
        
    # Process elimination: the team in team mode, otherwise the player
    if session.elimination_mode and turn_data.result != "correct" and team_mode:
        team.eliminated = True
        team.elimination_round = turn_data.round_number
        db.add(team)
    elif session.elimination_mode and turn_data.result != "correct":
        player = db.get(Player, turn_data.player_id)
        if player:
            player.eliminated = True
            player.elimination_round = turn_data.round_number
            db.add(player)
            
    db.commit()
    db.refresh(turn)
    return turn

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
