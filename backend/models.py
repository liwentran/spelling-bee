import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa

class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    timer_duration_seconds: int = Field(default=120)
    elimination_mode: bool = Field(default=False)
    status: str = Field(default="setup")  # setup, active, completed
    current_round: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    teams: List["Team"] = Relationship(back_populates="session", cascade_delete=True)
    players: List["Player"] = Relationship(back_populates="session", cascade_delete=True)
    words: List["Word"] = Relationship(back_populates="session", cascade_delete=True)
    turns: List["Turn"] = Relationship(back_populates="session", cascade_delete=True)

class Team(SQLModel, table=True):
    __tablename__ = "teams"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id")
    name: str
    color: Optional[str] = None  # hex, e.g. #f59e0b
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    session: Optional[Session] = Relationship(back_populates="teams")
    # No delete cascade: deleting a team unassigns its players/words (team_id -> NULL)
    players: List["Player"] = Relationship(back_populates="team")
    words: List["Word"] = Relationship(back_populates="team")

class Player(SQLModel, table=True):
    __tablename__ = "players"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id")
    team_id: Optional[str] = Field(default=None, foreign_key="teams.id")
    name: str
    age: Optional[str] = None
    grade: Optional[str] = None
    school: Optional[str] = None
    fun_fact: Optional[str] = None
    eliminated: bool = Field(default=False)
    elimination_round: Optional[int] = None
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    session: Optional[Session] = Relationship(back_populates="players")
    team: Optional[Team] = Relationship(back_populates="players")
    words: List["Word"] = Relationship(back_populates="player", cascade_delete=True)
    turns: List["Turn"] = Relationship(back_populates="player", cascade_delete=True)

class Word(SQLModel, table=True):
    __tablename__ = "words"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id")
    player_id: Optional[str] = Field(default=None, foreign_key="players.id")  # null = session pool
    team_id: Optional[str] = Field(default=None, foreign_key="teams.id")  # set with no player = team pool
    word: str
    definition: Optional[str] = None
    sentence: Optional[str] = None
    part_of_speech: Optional[str] = None
    language_of_origin: Optional[str] = None
    alternate_pronunciations: Optional[str] = None
    difficulty: Optional[int] = None  # 1-5
    used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    session: Optional[Session] = Relationship(back_populates="words")
    player: Optional[Player] = Relationship(back_populates="words")
    team: Optional[Team] = Relationship(back_populates="words")
    turns: List["Turn"] = Relationship(back_populates="word", cascade_delete=True)

class Turn(SQLModel, table=True):
    __tablename__ = "turns"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="sessions.id")
    player_id: str = Field(foreign_key="players.id")
    word_id: str = Field(foreign_key="words.id")
    round_number: int
    result: str  # correct, incorrect, timeout
    time_taken_seconds: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    session: Optional[Session] = Relationship(back_populates="turns")
    player: Optional[Player] = Relationship(back_populates="turns")
    word: Optional[Word] = Relationship(back_populates="turns")
