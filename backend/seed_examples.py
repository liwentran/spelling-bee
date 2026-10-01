"""Seed example sessions for demos and manual testing.

Usage: cd backend && uv run python seed_examples.py
Idempotent: a session whose name already exists is skipped.
"""
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from sqlmodel import Session as DbSession, select
from database import get_engine
from models import Session, Team, Player, Word

# Word tuples: (word, definition, sentence, part_of_speech, language_of_origin, alternate_pronunciations, difficulty)

TEAM_BEE = {
    "name": "Example: Team Bee (Honeybees vs Bumblebees)",
    "timer_duration_seconds": 90,
    "elimination_mode": False,
    "teams": [
        {
            "name": "Honeybees",
            "color": "#f59e0b",
            "players": [
                {"name": "Maya Chen", "age": "11", "grade": "6th", "school": "Lincoln Middle", "fun_fact": "Has read every Percy Jackson book twice",
                 "words": [("rhythm", "A strong, regular repeated pattern of movement or sound", "The drummer kept a steady rhythm all night.", "noun", "Greek", None, 2),
                           ("mnemonic", "A device such as a pattern of letters that helps you remember something", "She used a mnemonic to memorize the planets.", "noun", "Greek", "nih-MON-ik", 4)]},
                {"name": "Diego Alvarez", "age": "12", "grade": "7th", "school": "Lincoln Middle", "fun_fact": "Can solve a Rubik's cube in under a minute",
                 "words": [("silhouette", "The dark shape and outline of someone or something against a brighter background", "The cat's silhouette appeared in the window.", "noun", "French", None, 3),
                           ("onomatopoeia", "The formation of a word from a sound associated with what is named", "\"Buzz\" is a classic example of onomatopoeia.", "noun", "Greek", None, 5)]},
            ],
            "pool": [("apiary", "A place where bees are kept; a collection of beehives", "The farm's apiary held twenty hives.", "noun", "Latin", None, 3),
                     ("nectar", "A sugary fluid produced by flowers to attract pollinators", "Bees collect nectar to make honey.", "noun", "Greek", None, 1)],
        },
        {
            "name": "Bumblebees",
            "color": "#3b82f6",
            "players": [
                {"name": "Priya Patel", "age": "11", "grade": "6th", "school": "Roosevelt Elementary", "fun_fact": "Plays the violin in the youth orchestra",
                 "words": [("pharaoh", "A ruler in ancient Egypt", "The pharaoh's tomb was filled with treasure.", "noun", "Egyptian", None, 3),
                           ("bureaucracy", "A system of government with many complicated rules and processes", "The new permit got stuck in the bureaucracy.", "noun", "French", None, 4)]},
                {"name": "Sam O'Brien", "age": "12", "grade": "7th", "school": "Roosevelt Elementary", "fun_fact": "Raised a monarch butterfly from a caterpillar",
                 "words": [("conscience", "An inner feeling or voice viewed as a guide to right or wrong behavior", "His conscience told him to return the wallet.", "noun", "Latin", None, 3),
                           ("chrysanthemum", "A plant of the daisy family with brightly colored flowers", "Grandma grew a chrysanthemum by the porch.", "noun", "Greek", None, 5)]},
            ],
            "pool": [("pollinate", "To carry pollen to a flower so it can produce seeds", "Bumblebees pollinate tomato plants.", "verb", "Latin", None, 2),
                     ("colony", "A community of animals or plants of one kind living close together", "The colony had thousands of worker bees.", "noun", "Latin", None, 1)],
        },
    ],
    # Shared session pool, e.g. for tiebreakers
    "pool": [("pneumonia", "Lung inflammation caused by a bacterial or viral infection", "He missed a week of school with pneumonia.", "noun", "Greek", "noo-MOHN-yuh", 4),
             ("entrepreneur", "A person who sets up a business, taking on financial risks", "The young entrepreneur sold lemonade and honey.", "noun", "French", "ahn-truh-pruh-NUR", 4),
             ("weird", "Suggesting something supernatural; unusual or strange", "There was a weird noise coming from the hive.", "adjective", "Old English", None, 2)],
}

SOLO_BEE = {
    "name": "Example: Classroom Elimination Bee",
    "timer_duration_seconds": 60,
    "elimination_mode": True,
    "teams": [],
    "players": [
        {"name": "Ava Johnson", "age": "9", "grade": "4th", "school": "Maple Grove", "fun_fact": "Has three pet hamsters"},
        {"name": "Liam Nguyen", "age": "10", "grade": "4th", "school": "Maple Grove", "fun_fact": "Wants to be an astronaut"},
        {"name": "Zoe Williams", "age": "9", "grade": "4th", "school": "Maple Grove", "fun_fact": "Knows all 50 state capitals"},
    ],
    "pool": [("because", "For the reason that", "We stayed inside because it was raining.", "conjunction", "Middle English", None, 1),
             ("friend", "A person you know well and like", "My friend shared her lunch with me.", "noun", "Old English", None, 1),
             ("necessary", "Needed to be done or achieved; essential", "Water is necessary for plants to grow.", "adjective", "Latin", None, 2),
             ("separate", "To move or keep apart", "Please separate the red blocks from the blue ones.", "verb", "Latin", None, 2),
             ("library", "A building or room containing books to read or borrow", "We visit the library every Friday.", "noun", "Latin", None, 1),
             ("February", "The second month of the year", "My birthday is in February.", "noun", "Latin", "FEB-yoo-air-ee", 2),
             ("Wednesday", "The day of the week after Tuesday", "We have art class on Wednesday.", "noun", "Old English", None, 2),
             ("caterpillar", "The larva of a butterfly or moth", "The caterpillar munched on a leaf.", "noun", "French", None, 2)],
}


def make_word(session_id, w, player_id=None, team_id=None):
    word, definition, sentence, pos, origin, alt, difficulty = w
    return Word(session_id=session_id, player_id=player_id, team_id=team_id, word=word, definition=definition,
                sentence=sentence, part_of_speech=pos, language_of_origin=origin,
                alternate_pronunciations=alt, difficulty=difficulty)


def seed(db: DbSession, spec: dict):
    if db.exec(select(Session).where(Session.name == spec["name"])).first():
        print(f"skip (exists): {spec['name']}")
        return
    sess = Session(name=spec["name"], timer_duration_seconds=spec["timer_duration_seconds"], elimination_mode=spec["elimination_mode"])
    db.add(sess)
    db.flush()

    order = 0
    def add_player(p, team_id=None):
        nonlocal order
        order += 1
        player = Player(session_id=sess.id, team_id=team_id, sort_order=order,
                        **{k: v for k, v in p.items() if k != "words"})
        db.add(player)
        db.flush()
        for w in p.get("words", []):
            db.add(make_word(sess.id, w, player_id=player.id))

    for t_order, t in enumerate(spec["teams"], start=1):
        team = Team(session_id=sess.id, name=t["name"], color=t["color"], sort_order=t_order)
        db.add(team)
        db.flush()
        for p in t["players"]:
            add_player(p, team.id)
        for w in t["pool"]:
            db.add(make_word(sess.id, w, team_id=team.id))

    for p in spec.get("players", []):
        add_player(p)
    for w in spec["pool"]:
        db.add(make_word(sess.id, w))

    db.commit()
    print(f"created: {spec['name']} ({sess.id})")


if __name__ == "__main__":
    with DbSession(get_engine()) as db:
        for spec in (TEAM_BEE, SOLO_BEE):
            seed(db, spec)
