from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DbSession, select
from typing import List, Optional
from pydantic import BaseModel
from database import get_session
from models import Word, Session, Player

router = APIRouter(prefix="/api/sessions/{session_id}/words", tags=["words"])

class WordCreate(BaseModel):
    player_id: Optional[str] = None
    word: str
    definition: Optional[str] = None
    sentence: Optional[str] = None
    part_of_speech: Optional[str] = None
    language_of_origin: Optional[str] = None
    alternate_pronunciations: Optional[str] = None
    difficulty: Optional[int] = None

class WordUpdate(BaseModel):
    player_id: Optional[str] = None
    word: Optional[str] = None
    definition: Optional[str] = None
    sentence: Optional[str] = None
    part_of_speech: Optional[str] = None
    language_of_origin: Optional[str] = None
    alternate_pronunciations: Optional[str] = None
    difficulty: Optional[int] = None
    used: Optional[bool] = None

class BulkWordImport(BaseModel):
    player_name: Optional[str] = None
    word: str
    definition: Optional[str] = None
    sentence: Optional[str] = None
    part_of_speech: Optional[str] = None
    language_of_origin: Optional[str] = None
    alternate_pronunciations: Optional[str] = None
    difficulty: Optional[int] = None

@router.post("/")
@router.post("")
def create_word(session_id: str, word_data: WordCreate, db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    word = Word(
        session_id=session_id,
        **word_data.dict()
    )
    db.add(word)
    db.commit()
    db.refresh(word)
    return word

@router.post("/bulk")
def bulk_import_words(session_id: str, words_data: List[BulkWordImport], db: DbSession = Depends(get_session)):
    session = db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Get all players to map names to ids
    statement = select(Player).where(Player.session_id == session_id)
    players = db.exec(statement).all()
    player_map = {p.name.lower(): p.id for p in players}
    
    created_words = []
    for wd in words_data:
        player_id = None
        if wd.player_name and wd.player_name.lower() in player_map:
            player_id = player_map[wd.player_name.lower()]
            
        word = Word(
            session_id=session_id,
            player_id=player_id,
            word=wd.word,
            definition=wd.definition,
            sentence=wd.sentence,
            part_of_speech=wd.part_of_speech,
            language_of_origin=wd.language_of_origin,
            alternate_pronunciations=wd.alternate_pronunciations,
            difficulty=wd.difficulty
        )
        db.add(word)
        created_words.append(word)
        
    db.commit()
    return {"ok": True, "count": len(created_words)}

@router.get("/")
@router.get("")
def list_words(
    session_id: str, 
    player_id: Optional[str] = None, 
    used: Optional[bool] = None,
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    db: DbSession = Depends(get_session)
):
    statement = select(Word).where(Word.session_id == session_id)
    if player_id is not None:
        statement = statement.where(Word.player_id == player_id)
    if used is not None:
        statement = statement.where(Word.used == used)
        
    if sort_by and hasattr(Word, sort_by):
        statement = statement.order_by(getattr(Word, sort_by))
        
    words = db.exec(statement).all()
    return words

@router.get("/{word_id}")
def get_word(session_id: str, word_id: str, db: DbSession = Depends(get_session)):
    word = db.get(Word, word_id)
    if not word or word.session_id != session_id:
        raise HTTPException(status_code=404, detail="Word not found")
    return word

@router.patch("/{word_id}")
def update_word(session_id: str, word_id: str, word_data: WordUpdate, db: DbSession = Depends(get_session)):
    word = db.get(Word, word_id)
    if not word or word.session_id != session_id:
        raise HTTPException(status_code=404, detail="Word not found")
        
    update_data = word_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(word, key, value)
        
    db.add(word)
    db.commit()
    db.refresh(word)
    return word

@router.delete("/{word_id}")
def delete_word(session_id: str, word_id: str, db: DbSession = Depends(get_session)):
    word = db.get(Word, word_id)
    if not word or word.session_id != session_id:
        raise HTTPException(status_code=404, detail="Word not found")
        
    db.delete(word)
    db.commit()
    return {"ok": True}
