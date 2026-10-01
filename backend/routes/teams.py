from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select
from typing import Optional
from pydantic import BaseModel
from database import get_session
from models import Team, Session

router = APIRouter(prefix="/api/sessions/{session_id}/teams", tags=["teams"])

class TeamCreate(BaseModel):
    name: str
    color: Optional[str] = None

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None

def validate_team(db: DbSession, session_id: str, team_id: Optional[str]):
    """Raise 400 if team_id is set but doesn't belong to this session."""
    if team_id is None:
        return
    team = db.get(Team, team_id)
    if not team or team.session_id != session_id:
        raise HTTPException(status_code=400, detail="Team not found in this session")

@router.post("/")
@router.post("")
def create_team(session_id: str, team_data: TeamCreate, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    statement = select(Team).where(Team.session_id == session_id).order_by(Team.sort_order.desc())
    results = db.exec(statement).all()
    max_order = results[0].sort_order if results else 0

    team = Team(
        session_id=session_id,
        name=team_data.name,
        color=team_data.color,
        sort_order=max_order + 1
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

@router.get("/")
@router.get("")
def list_teams(session_id: str, db: DbSession = Depends(get_session)):
    statement = select(Team).where(Team.session_id == session_id).order_by(Team.sort_order)
    return db.exec(statement).all()

@router.patch("/{team_id}")
def update_team(session_id: str, team_id: str, team_data: TeamUpdate, db: DbSession = Depends(get_session)):
    team = db.get(Team, team_id)
    if not team or team.session_id != session_id:
        raise HTTPException(status_code=404, detail="Team not found")

    update_data = team_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(team, key, value)

    db.add(team)
    db.commit()
    db.refresh(team)
    return team

@router.delete("/{team_id}")
def delete_team(session_id: str, team_id: str, db: DbSession = Depends(get_session)):
    team = db.get(Team, team_id)
    if not team or team.session_id != session_id:
        raise HTTPException(status_code=404, detail="Team not found")

    # Players and words on this team are unassigned, not deleted
    db.delete(team)
    db.commit()
    return {"ok": True}
