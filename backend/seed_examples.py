"""Seed example sessions for demos and manual testing.

Usage: cd backend && uv run python seed_examples.py  (or `make seed`)
Goes through the same upsert as POST /api/sessions/{id}/import, so re-running
updates existing example sessions in place instead of duplicating them.
"""
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import HTTPException
from sqlmodel import Session as DbSession, select
from database import get_engine
from models import Session
from routes.roster import RosterImport, import_roster

# Word tuples: (word, definition, sentence, part_of_speech, language_of_origin, alternate_pronunciations, difficulty)

TEAM_BEE = {
    "name": "Example: Team Bee (Honeybees vs Bumblebees)",
    "timer_duration_seconds": 90,
    "elimination_mode": False,
    "game_mode": "team",
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
                {"name": "Noah Kim", "age": "11", "grade": "6th", "school": "Lincoln Middle", "fun_fact": "Keeps two beehives with his grandpa",
                 "words": [("propolis", "A sticky resin that bees collect from tree buds and use to seal their hives", "The bees sealed every crack in the hive with propolis.", "noun", "Greek", "PROP-uh-lis", 3),
                           ("larvae", "The young, wormlike form of many insects after hatching (plural of larva)", "Worker bees feed the larvae royal jelly.", "noun", "Latin", "LAR-vee", 3)]},
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
                {"name": "Ella Brooks", "age": "12", "grade": "7th", "school": "Roosevelt Elementary", "fun_fact": "Can name every bird that visits her backyard",
                 "words": [("ornithology", "The scientific study of birds", "Her love of ornithology started with a backyard feeder.", "noun", "Greek", None, 4),
                           ("symbiosis", "A close relationship between two different species that benefits both", "Bees and flowers live in symbiosis.", "noun", "Greek", None, 4)]},
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
    "game_mode": "individual",
    "teams": [],
    "players": [
        {"name": "Ava Johnson", "age": "9", "grade": "4th", "school": "Maple Grove", "fun_fact": "Has three pet hamsters",
         "words": [("hamster", "A small furry rodent often kept as a pet", "My hamster runs on his wheel all night.", "noun", "German", None, 1),
                   ("neighbor", "A person who lives next door or nearby", "Our neighbor feeds the hamsters when we travel.", "noun", "Old English", None, 2),
                   ("beautiful", "Pleasing to look at", "The sunset was beautiful tonight.", "adjective", "French", None, 2)]},
        {"name": "Liam Nguyen", "age": "10", "grade": "4th", "school": "Maple Grove", "fun_fact": "Wants to be an astronaut",
         "words": [("planet", "A large round object in space that travels around a star", "Mars is the fourth planet from the sun.", "noun", "Greek", None, 1),
                   ("gravity", "The force that pulls objects toward the earth", "Gravity keeps our feet on the ground.", "noun", "Latin", None, 2),
                   ("astronaut", "A person trained to travel in a spacecraft", "The astronaut floated inside the space station.", "noun", "Greek", None, 2)]},
        {"name": "Zoe Williams", "age": "9", "grade": "4th", "school": "Maple Grove", "fun_fact": "Knows all 50 state capitals",
         "words": [("capital", "The city where a state or country's government is located", "Sacramento is the capital of California.", "noun", "Latin", None, 1),
                   ("geography", "The study of the earth's land, water, and people", "Zoe's favorite subject is geography.", "noun", "Greek", None, 2),
                   ("Mississippi", "A large river and a state in the southern United States", "The Mississippi River flows into the Gulf of Mexico.", "noun", "Ojibwe", None, 2)]},
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


# Upserted by name into the existing "National Spelling Bee Demo" session (which may hold extra
# players added by hand; import never deletes them). Finalists are fictional; their words are
# real past Scripps National Spelling Bee winning words.
NATIONAL_BEE = {
    "name": "National Spelling Bee Demo",
    "timer_duration_seconds": 120,
    "elimination_mode": True,
    "game_mode": "individual",
    "teams": [],
    "players": [
        {"name": "Amara Okafor", "age": "13", "grade": "8th", "school": "Riverside Academy", "fun_fact": "Has memorized the first 200 digits of pi",
         "words": [("stichomythia", "Dialogue in alternating single lines, as in classical Greek drama", "The play's tense stichomythia had the actors trading sharp one-line retorts.", "noun", "Greek", "stik-oh-MITH-ee-uh", 5),
                   ("cymotrichous", "Having wavy hair", "The portrait showed a cymotrichous poet gazing out to sea.", "adjective", "Greek", "sy-MAH-trih-kus", 5),
                   ("appoggiatura", "An ornamental grace note that leans into the main note of a melody", "The violinist added an appoggiatura before the final chord.", "noun", "Italian", "uh-pah-juh-TOOR-uh", 5)]},
        {"name": "Lucas Moreau", "age": "14", "grade": "8th", "school": "Pine Ridge Middle", "fun_fact": "Speaks three languages at home",
         "words": [("feuilleton", "The part of a European newspaper devoted to light fiction, reviews, and essays", "He read the feuilleton before the front-page news.", "noun", "French", "FOY-uh-tawn", 5),
                   ("guetapens", "An ambush, snare, or trap", "The mountain pass was a perfect guetapens for the unwary traveler.", "noun", "French", "GET-uh-pahn", 5),
                   ("Ursprache", "A parent language, especially one reconstructed from its descendants", "Linguists reconstructed the Ursprache from dozens of modern languages.", "noun", "German", "OOR-shprah-kuh", 5)]},
        {"name": "Sofia Ramirez", "age": "12", "grade": "7th", "school": "Lakeview Middle", "fun_fact": "Writes her own fantasy novels",
         "words": [("nunatak", "A mountain peak that sticks up through a glacier or ice sheet", "From the plane they spotted a lone nunatak rising above the ice.", "noun", "Inuit", "NUN-uh-tak", 5),
                   ("scherenschnitte", "The art of cutting intricate designs out of paper", "Her scherenschnitte of a winter forest won first prize.", "noun", "German", "SHARE-en-shnit-uh", 5),
                   ("Laodicean", "Lukewarm or indifferent, especially about religion or politics", "His Laodicean attitude toward the election surprised his friends.", "adjective", "Greek", "lay-ah-duh-SEE-un", 5)]},
    ],
    # Championship pool: more past winning words for tiebreakers
    "pool": [("abseil", "To descend a rock face or wall using a rope", "The climbers abseiled down the cliff before sunset.", "verb", "German", "AB-sayl", 4),
             ("moorhen", "A dark water bird of the rail family with a red bill", "A moorhen paddled through the reeds at the pond's edge.", "noun", "Old English", None, 4),
             ("Murraya", "A genus of tropical trees and shrubs that includes the curry leaf tree", "The Murraya in the greenhouse smelled of citrus blossoms.", "noun", "New Latin", None, 5),
             ("koinonia", "Christian fellowship or communion within a community", "The retreat was meant to build koinonia among the members.", "noun", "Greek", "koy-noh-NEE-uh", 5),
             ("marocain", "A dress fabric of ribbed crepe", "Her gown was sewn from ivory marocain.", "noun", "French", "mar-uh-KAYN", 5),
             ("gesellschaft", "A social relationship based on impersonal ties, as in a modern society", "The sociologist contrasted village life with the gesellschaft of the city.", "noun", "German", "guh-ZEL-shahft", 5),
             ("knaidel", "A small dumpling, especially a matzo ball", "Grandma served one giant knaidel in each bowl of soup.", "noun", "Yiddish", "KNAY-dul", 4),
             ("stromuhr", "An instrument that measures the speed of blood flow", "The researchers used a stromuhr to measure blood flow in the artery.", "noun", "German", "SHTROH-moor", 5),
             ("guerdon", "A reward or recompense", "The knight's only guerdon was the king's gratitude.", "noun", "French", "GUR-dun", 4),
             ("serrefine", "A small spring forceps used to clamp a blood vessel", "The surgeon placed a serrefine on the bleeding vessel.", "noun", "French", "sair-FEEN", 5),
             ("autochthonous", "Native to the place where it is found; indigenous", "The island's autochthonous plants grow nowhere else on earth.", "adjective", "Greek", "aw-TOK-thuh-nus", 5),
             ("éclaircissement", "A clarification or explanation of something obscure", "The letter offered a long-awaited éclaircissement of the mystery.", "noun", "French", "ay-klair-sees-MAHN", 5)],
}


def word_entry(w, **owner):
    keys = ("word", "definition", "sentence", "part_of_speech", "language_of_origin", "alternate_pronunciations", "difficulty")
    return {**dict(zip(keys, w)), **owner}


def to_roster(spec: dict) -> RosterImport:
    """Convert a spec above into the import format (the same JSON an AI would paste)."""
    strip = lambda p: {k: v for k, v in p.items() if k != "words"}
    words = []
    for t in spec["teams"]:
        for p in t["players"]:
            words += [word_entry(w, player_name=p["name"]) for w in p.get("words", [])]
        words += [word_entry(w, team_name=t["name"]) for w in t["pool"]]
    for p in spec.get("players", []):
        words += [word_entry(w, player_name=p["name"]) for w in p.get("words", [])]
    words += [word_entry(w) for w in spec["pool"]]
    return RosterImport.model_validate({
        "game_mode": spec["game_mode"],
        "teams": [{"name": t["name"], "color": t["color"], "players": [strip(p) for p in t["players"]]} for t in spec["teams"]],
        "players": [strip(p) for p in spec.get("players", [])],
        "words": words,
    })


def seed(db: DbSession, spec: dict):
    sess = db.exec(select(Session).where(Session.name == spec["name"])).first()
    is_new = sess is None
    if is_new:
        sess = Session(name=spec["name"], timer_duration_seconds=spec["timer_duration_seconds"], elimination_mode=spec["elimination_mode"])
        db.add(sess)
        db.flush()
    try:
        result = import_roster(db, sess, to_roster(spec))
    except HTTPException as e:
        db.rollback()
        print(f"skipped {spec['name']}: {e.detail}")
        return
    db.commit()
    print(f"{'created' if is_new else 'updated'}: {spec['name']} ({sess.id}) "
          f"game_mode={result['game_mode']} created={result['created']} updated={result['updated']}")


if __name__ == "__main__":
    engine = get_engine()
    engine.echo = False
    with DbSession(engine) as db:
        for spec in (NATIONAL_BEE, TEAM_BEE, SOLO_BEE):
            seed(db, spec)
