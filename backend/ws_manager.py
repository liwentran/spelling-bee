import json
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket, HTTPException
from sqlmodel import Session as DbSession, select
from database import get_engine
from sqlmodel import Session as SQLSession


class GameState:
    def __init__(self):
        self.game_mode: str = 'individual'  # individual, team (mirrors Session.game_mode)
        self.elimination_mode: bool = False  # mirrors Session.elimination_mode (TV hides Active/Eliminated without it)
        self.current_team_id: Optional[str] = None  # team mode: the team at the mic
        self.current_player_id: Optional[str] = None  # team mode: optional highlighted speller
        self.current_word_id: Optional[str] = None
        self.timer_running: bool = False
        self.timer_seconds_remaining: int = 0
        self.timer_duration: int = 120
        self.revealed_info: set = set()
        self.hide_word: bool = False  # TV shows only the first letter (+ definition); the controller re-sends its saved choice
        self.display_mode: str = 'idle'  # idle, player_intro, team_intro, spelling, result, scoreboard
        self.result: Optional[str] = None  # correct, incorrect, timeout
        self.round_number: int = 1  # mirrors Session.current_round (saved on NEXT_ROUND)
        self.round_done: list = []  # team ids (team mode) or player ids with a turn this round
        self.last_turn: Optional[dict] = None  # the most recent judged turn, for UNDO_RESULT
        self.data_version: int = 0  # bumped when turns change, so the controller refetches words/teams
        # Cached details for broadcast
        self.player_details: Optional[dict] = None
        self.team_details: Optional[dict] = None
        self.word_details: Optional[dict] = None

    def to_dict(self):
        return {
            "game_mode": self.game_mode,
            "elimination_mode": self.elimination_mode,
            "current_team_id": self.current_team_id,
            "current_player_id": self.current_player_id,
            "current_word_id": self.current_word_id,
            "timer_running": self.timer_running,
            "timer_seconds_remaining": self.timer_seconds_remaining,
            "timer_duration": self.timer_duration,
            "revealed_info": list(self.revealed_info),
            "hide_word": self.hide_word,
            "display_mode": self.display_mode,
            "result": self.result,
            "round_number": self.round_number,
            "round_done": self.round_done,
            "last_turn": self.last_turn,
            "data_version": self.data_version,
            "player": self.player_details,
            "team": self.team_details,
            "word": self.word_details,
        }


def _team_dict(team) -> Optional[dict]:
    if not team:
        return None
    return {"id": team.id, "name": team.name, "color": team.color}


def _player_dict(player) -> dict:
    return {
        "id": player.id,
        "name": player.name,
        "age": player.age,
        "grade": player.grade,
        "school": player.school,
        "fun_fact": player.fun_fact,
        "eliminated": player.eliminated,
        "elimination_round": player.elimination_round,
        "sort_order": player.sort_order,
        "team_id": player.team_id,
        "team": _team_dict(player.team),
    }


def _fetch_player(player_id: str) -> Optional[dict]:
    """Fetch player details from DB."""
    from models import Player
    engine = get_engine()
    with SQLSession(engine) as session:
        player = session.get(Player, player_id)
        if player:
            return _player_dict(player)
    return None


def _fetch_team(team_id: str) -> Optional[dict]:
    """Fetch team details, including every member, from DB."""
    from models import Team
    engine = get_engine()
    with SQLSession(engine) as session:
        team = session.get(Team, team_id)
        if team:
            members = sorted(team.players, key=lambda p: p.sort_order)
            return {
                **_team_dict(team),
                "eliminated": team.eliminated,
                "members": [_player_dict(p) for p in members],
            }
    return None


def _sync_session_settings(state: "GameState", session_id: str):
    """Pull game mode, timer length and round from the DB (edited in Setup / the controller, or
    reset). A running or paused-mid-word timer is left alone; an idle one is reset to the new length."""
    from models import Session as SessionModel
    with SQLSession(get_engine()) as session:
        sess = session.get(SessionModel, session_id)
        if not sess:
            return
        state.game_mode = sess.game_mode
        state.elimination_mode = sess.elimination_mode
        if not state.timer_running and state.timer_seconds_remaining in (0, state.timer_duration):
            state.timer_seconds_remaining = sess.timer_duration_seconds
        state.timer_duration = sess.timer_duration_seconds
        state.round_number = sess.current_round
        _refresh_round_done(state, session, session_id)


def _refresh_round_done(state: "GameState", session, session_id: str):
    """Who has already had a turn this round, derived from saved turns so it survives restarts."""
    from models import Turn
    turns = session.exec(select(Turn).where(Turn.session_id == session_id, Turn.round_number == state.round_number)).all()
    key = "team_id" if state.game_mode == "team" else "player_id"
    state.round_done = list(dict.fromkeys(getattr(t, key) for t in turns if getattr(t, key)))


def _judge(state: "GameState", session_id: str, result: str) -> bool:
    """Save the turn for the word on screen. Each word is judged once; UNDO_RESULT reopens it."""
    from models import Session as SessionModel
    from routes.turns import TurnCreate, save_turn
    owner = state.current_team_id if state.game_mode == "team" else state.current_player_id
    if not owner or not state.current_word_id or state.result:
        return False
    with SQLSession(get_engine()) as session:
        sess = session.get(SessionModel, session_id)
        turn = save_turn(session, sess, TurnCreate(
            team_id=state.current_team_id if state.game_mode == "team" else None,
            player_id=state.current_player_id,
            word_id=state.current_word_id,
            round_number=state.round_number,
            result=result,
            time_taken_seconds=max(0, state.timer_duration - state.timer_seconds_remaining),
        ))
        session.commit()
        owner_details = (state.team_details if state.game_mode == "team" else state.player_details) or {}
        state.last_turn = {"id": turn.id, "result": result,
                           "word": (state.word_details or {}).get("word"), "name": owner_details.get("name")}
        _refresh_round_done(state, session, session_id)
    state.data_version += 1
    return True


def _undo_last_turn(state: "GameState", session_id: str):
    """Delete the last judged turn and put its team/player and word back on screen to re-judge."""
    from models import Turn
    from routes.turns import delete_turn
    with SQLSession(get_engine()) as session:
        turn = session.get(Turn, state.last_turn["id"])
        if turn:
            team_id, player_id, word_id = turn.team_id, turn.player_id, turn.word_id
            delete_turn(session, turn)
            session.commit()
            if state.current_team_id != team_id:
                state.current_team_id = team_id
                state.team_details = _fetch_team(team_id) if team_id else None
            if state.current_player_id != player_id:
                state.current_player_id = player_id
                state.player_details = _fetch_player(player_id) if player_id else None
            if state.current_word_id != word_id:
                state.current_word_id = word_id
                state.revealed_info.clear()
            state.word_details = _fetch_word(word_id)
            state.display_mode = "spelling"
        _refresh_round_done(state, session, session_id)
    state.last_turn = None
    state.result = None
    state.timer_running = False
    state.data_version += 1


def _change_turn(state: "GameState", session_id: str, command: dict):
    """EDIT_TURN (new round/result) or DELETE_TURN on any past turn, from the controller's word menu."""
    from models import Turn
    from routes.turns import edit_turn, delete_turn
    with SQLSession(get_engine()) as session:
        turn = session.get(Turn, command.get("turn_id"))
        if not turn or turn.session_id != session_id:
            return
        is_last = bool(state.last_turn and state.last_turn["id"] == turn.id)
        if command["type"] == "DELETE_TURN":
            delete_turn(session, turn)
            if is_last:
                state.last_turn = None
        else:
            edit_turn(session, turn, command.get("round_number"), command.get("result"))
            if is_last:
                state.last_turn = {**state.last_turn, "result": turn.result}
                if state.result and state.current_word_id == turn.word_id:
                    state.result = turn.result  # the TV's result screen shows the correction
        session.commit()
        _refresh_round_done(state, session, session_id)
    state.data_version += 1


def _save_round(session_id: str, round_number: int):
    from models import Session as SessionModel
    with SQLSession(get_engine()) as session:
        sess = session.get(SessionModel, session_id)
        if sess:
            sess.current_round = round_number
            session.commit()


def _fetch_word(word_id: str) -> Optional[dict]:
    """Fetch word details from DB."""
    from models import Word
    engine = get_engine()
    with SQLSession(engine) as session:
        word = session.get(Word, word_id)
        if word:
            return {
                "id": word.id,
                "word": word.word,
                "definition": word.definition,
                "sentence": word.sentence,
                "part_of_speech": word.part_of_speech,
                "language_of_origin": word.language_of_origin,
                "alternate_pronunciations": word.alternate_pronunciations,
                "difficulty": word.difficulty,
                "used": word.used,
                "player_id": word.player_id,
                "team_id": word.team_id,
                "team": _team_dict(word.team),
            }
    return None


def _fetch_scoreboard(session_id: str) -> dict:
    """Fetch per-player and per-team scoreboard data from DB."""
    from scoring import compute_scoreboard
    with SQLSession(get_engine()) as session:
        return compute_scoreboard(session, session_id)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.game_states: Dict[str, GameState] = {}

    def get_state(self, session_id: str) -> GameState:
        if session_id not in self.game_states:
            state = self.game_states[session_id] = GameState()
            _sync_session_settings(state, session_id)
        return self.game_states[session_id]

    def drop_state(self, session_id: str):
        """Forget the live game (after a Reset); the next connection rebuilds it from the DB."""
        self.game_states.pop(session_id, None)

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(ws)
        # Send initial state; re-read game mode / timer length in case they changed in Setup
        state = self.get_state(session_id)
        _sync_session_settings(state, session_id)
        await ws.send_json({"type": "STATE_UPDATE", "state": state.to_dict()})

    def disconnect(self, session_id: str, ws: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(ws)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(data)
                except Exception:
                    dead_connections.add(connection)
            for c in dead_connections:
                self.disconnect(session_id, c)

    async def handle_command(self, session_id: str, command: dict):
        state = self.get_state(session_id)
        cmd_type = command.get("type")

        if cmd_type == "SET_ACTIVE_TEAM":
            state.current_team_id = command.get("team_id")
            state.team_details = _fetch_team(state.current_team_id) if state.current_team_id else None
            # A new team clears the previous speller
            state.current_player_id = None
            state.player_details = None

        elif cmd_type == "SHOW_TEAM_INTRO":
            state.display_mode = "team_intro"

        elif cmd_type == "SET_ACTIVE_PLAYER":
            state.current_player_id = command.get("player_id")
            state.player_details = _fetch_player(state.current_player_id) if state.current_player_id else None

        elif cmd_type == "SET_ACTIVE_WORD":
            state.current_word_id = command.get("word_id")
            state.word_details = _fetch_word(state.current_word_id) if state.current_word_id else None
            state.revealed_info.clear()
            state.result = None
            if state.current_word_id and (state.current_player_id or state.current_team_id):
                state.display_mode = "spelling"

        elif cmd_type == "START_TIMER":
            state.timer_running = True

        elif cmd_type == "PAUSE_TIMER":
            state.timer_running = False

        elif cmd_type == "RESET_TIMER":
            state.timer_running = False
            # Keep timer_duration in step so the TV's bar percentage and colors are right
            state.timer_duration = command.get("duration", state.timer_duration)
            state.timer_seconds_remaining = state.timer_duration

        elif cmd_type == "UPDATE_TIMER":
            # Controller sends timer ticks
            state.timer_seconds_remaining = command.get("seconds_remaining", state.timer_seconds_remaining)

        elif cmd_type == "SET_TIMER_DURATION":
            state.timer_duration = command.get("duration", 120)
            state.timer_seconds_remaining = state.timer_duration

        elif cmd_type in ("MARK_CORRECT", "MARK_INCORRECT", "MARK_TIMEOUT"):
            # The server records the turn, so a double tap or a late timeout can't count twice
            result = cmd_type.removeprefix("MARK_").lower()
            if not _judge(state, session_id, result):
                return
            state.result = result
            state.display_mode = "result"
            state.timer_running = False

        elif cmd_type == "UNDO_RESULT":
            if not state.last_turn:
                return
            _undo_last_turn(state, session_id)

        elif cmd_type == "REVEAL_INFO":
            info_type = command.get("info_type")
            if info_type:
                state.revealed_info.add(info_type)

        elif cmd_type == "SET_HIDE_WORD":
            state.hide_word = bool(command.get("hide"))

        elif cmd_type == "HIDE_INFO":
            info_type = command.get("info_type")
            if info_type in state.revealed_info:
                state.revealed_info.remove(info_type)

        elif cmd_type == "CLEAR_DISPLAY":
            state.display_mode = "idle"
            _sync_session_settings(state, session_id)
            state.current_team_id = None
            state.team_details = None
            state.current_player_id = None
            state.current_word_id = None
            state.player_details = None
            state.word_details = None
            state.result = None
            state.revealed_info.clear()
            state.timer_running = False

        elif cmd_type == "SHOW_SCOREBOARD":
            state.display_mode = "scoreboard"

        elif cmd_type == "SHOW_PLAYER_INTRO":
            state.display_mode = "player_intro"

        elif cmd_type in ("EDIT_TURN", "DELETE_TURN"):
            try:
                _change_turn(state, session_id, command)
            except HTTPException:
                return  # invalid round/result: ignore

        elif cmd_type == "NEXT_ROUND":
            # Saved to the session so a restart or redeploy keeps the round; the TV shows the new round
            state.round_number += 1
            _save_round(session_id, state.round_number)
            state.round_done = []
            state.last_turn = None
            state.display_mode = "idle"
            state.current_team_id = state.team_details = None
            state.current_player_id = state.player_details = None
            state.current_word_id = state.word_details = None
            state.result = None
            state.revealed_info.clear()
            state.timer_running = False
            state.timer_seconds_remaining = state.timer_duration

        elif cmd_type == "PLAY_SOUND":
            # Just broadcast sound command, don't change state
            await self.broadcast(session_id, {"type": "PLAY_SOUND", "sound": command.get("sound")})
            return  # Don't send state update for sound-only

        elif cmd_type == "PRONOUNCE_WORD":
            # Display speaks the current word via Web Speech API; no state change
            if state.word_details:
                await self.broadcast(session_id, {
                    "type": "PRONOUNCE_WORD",
                    "word": state.word_details["word"],
                    "rate": command.get("rate", 0.8),
                })
            return

        # Build broadcast payload
        payload = {"type": "STATE_UPDATE", "state": state.to_dict()}

        # Scores ride along on the scoreboard and on result screens (which show the new total)
        if state.display_mode in ("scoreboard", "result"):
            scores = _fetch_scoreboard(session_id)
            payload["scoreboard"] = scores["players"]
            payload["team_scoreboard"] = scores["teams"]
            payload["winner"] = scores["winner"]

        await self.broadcast(session_id, payload)


manager = ConnectionManager()
