"""Load the example sessions in /examples/*.json into the database.

Usage: cd backend && uv run python seed_examples.py  (or `make seed`)

Each file is a complete session definition in the same JSON format as Setup's
"Import JSON" and POST /api/sessions/import. Sessions are matched by name and
upserted, so re-running updates existing example sessions in place (and never
deletes anything added by hand). To add an example, drop another .json file in /examples.
"""
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

import json
from pathlib import Path
from fastapi import HTTPException
from sqlmodel import Session as DbSession, select
from database import get_engine
from models import Session
from routes.roster import RosterImport, import_roster, create_session_from_roster

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def seed(db: DbSession, path: Path):
    roster = RosterImport.model_validate(json.loads(path.read_text()))
    existing = db.exec(select(Session).where(Session.name == roster.name)).first()
    try:
        result = import_roster(db, existing, roster) if existing else create_session_from_roster(db, roster)
    except HTTPException as e:
        db.rollback()
        print(f"skipped {path.name}: {e.detail}")
        return
    db.commit()
    print(f"{'updated' if existing else 'created'}: {roster.name} ({result['session_id']}) from {path.name} "
          f"created={result['created']} updated={result['updated']}")
    for w in result["warnings"]:
        print(f"  warning: {w}")


if __name__ == "__main__":
    engine = get_engine()
    engine.echo = False
    with DbSession(engine) as db:
        for path in sorted(EXAMPLES_DIR.glob("*.json")):
            seed(db, path)
