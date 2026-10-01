from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select
from typing import List, Optional
from pydantic import BaseModel
from database import get_session
from models import Player, Session
from routes.teams import validate_team

router = APIRouter(prefix="/api/sessions/{session_id}/players", tags=["players"])

class PlayerCreate(BaseModel):
    name: str
    team_id: Optional[str] = None
    age: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    fun_fact: Optional[str] = None

class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    team_id: Optional[str] = None
    age: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    fun_fact: Optional[str] = None
    eliminated: Optional[bool] = None
    elimination_round: Optional[int] = None

@router.post("/")
@router.post("")
def create_player(session_id: str, player_data: PlayerCreate, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    validate_team(db, session_id, player_data.team_id)
        
    # Get max sort_order
    statement = select(Player).where(Player.session_id == session_id).order_by(Player.sort_order.desc())
    results = db.exec(statement).all()
    max_order = results[0].sort_order if results else 0
    
    player = Player(
        session_id=session_id,
        team_id=player_data.team_id,
        name=player_data.name,
        age=player_data.age,
        grade=player_data.grade,
        school=player_data.school,
        fun_fact=player_data.fun_fact,
        sort_order=max_order + 1
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player

@router.get("/")
@router.get("")
def list_players(session_id: str, db: DbSession = Depends(get_session)):
    statement = select(Player).where(Player.session_id == session_id).order_by(Player.sort_order)
    players = db.exec(statement).all()
    return players

@router.patch("/{player_id}")
def update_player(session_id: str, player_id: str, player_data: PlayerUpdate, db: DbSession = Depends(get_session)):
    player = db.get(Player, player_id)
    if not player or player.session_id != session_id:
        raise HTTPException(status_code=404, detail="Player not found")
        
    update_data = player_data.dict(exclude_unset=True)
    if "team_id" in update_data:
        validate_team(db, session_id, update_data["team_id"])
    for key, value in update_data.items():
        setattr(player, key, value)
        
    db.add(player)
    db.commit()
    db.refresh(player)
    return player

@router.delete("/{player_id}")
def delete_player(session_id: str, player_id: str, db: DbSession = Depends(get_session)):
    player = db.get(Player, player_id)
    if not player or player.session_id != session_id:
        raise HTTPException(status_code=404, detail="Player not found")
    
    db.delete(player)
    db.commit()
    return {"ok": True}

@router.put("/reorder")
def reorder_players(session_id: str, player_ids: List[str], db: DbSession = Depends(get_session)):
    statement = select(Player).where(Player.session_id == session_id)
    players = db.exec(statement).all()
    player_map = {p.id: p for p in players}
    
    for idx, pid in enumerate(player_ids):
        if pid in player_map:
            player_map[pid].sort_order = idx
            db.add(player_map[pid])
            
    db.commit()
    return {"ok": True}
