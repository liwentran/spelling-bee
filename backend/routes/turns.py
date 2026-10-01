from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DbSession, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from database import get_session
from models import Turn, Session, Player, Word

router = APIRouter(prefix="/api/sessions/{session_id}/turns", tags=["turns"])

class TurnCreate(BaseModel):
    player_id: str
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
        
    # Process elimination
    if session.elimination_mode and turn_data.result != "correct":
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
        
    statement = select(Player).where(Player.session_id == session_id)
    players = db.exec(statement).all()
    
    turn_statement = select(Turn).where(Turn.session_id == session_id)
    turns = db.exec(turn_statement).all()
    
    scoreboard = []
    for player in players:
        player_turns = [t for t in turns if t.player_id == player.id]
        
        correct = sum(1 for t in player_turns if t.result == "correct")
        incorrect = sum(1 for t in player_turns if t.result == "incorrect")
        timeout = sum(1 for t in player_turns if t.result == "timeout")
        
        rounds_survived = player.elimination_round - 1 if player.elimination_round else session.current_round
        
        scoreboard.append({
            "player_id": player.id,
            "player_name": player.name,
            "eliminated": player.eliminated,
            "total_correct": correct,
            "total_incorrect": incorrect,
            "total_timeout": timeout,
            "rounds_survived": rounds_survived
        })
        
    return scoreboard
