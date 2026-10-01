from sqlmodel import create_engine, Session
import os

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set")
        _engine = create_engine(DATABASE_URL, echo=True)
    return _engine

def get_session():
    engine = get_engine()
    with Session(engine) as session:
        yield session
