import json
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
from sqlmodel import Session as DbSession, select
from database import get_engine
from sqlmodel import Session as SQLSession


class GameState:
    def __init__(self):
        self.current_player_id: Optional[str] = None
        self.current_word_id: Optional[str] = None
        self.timer_running: bool = False
        self.timer_seconds_remaining: int = 0
        self.timer_duration: int = 120
        self.revealed_info: set = set()
        self.display_mode: str = 'idle'  # idle, player_intro, spelling, result, scoreboard
        self.result: Optional[str] = None  # correct, incorrect, timeout
        self.round_number: int = 1
        # Cached details for broadcast
        self.player_details: Optional[dict] = None
        self.word_details: Optional[dict] = None

    def to_dict(self):
        return {
            "current_player_id": self.current_player_id,
            "current_word_id": self.current_word_id,
            "timer_running": self.timer_running,
            "timer_seconds_remaining": self.timer_seconds_remaining,
            "timer_duration": self.timer_duration,
            "revealed_info": list(self.revealed_info),
            "display_mode": self.display_mode,
            "result": self.result,
            "round_number": self.round_number,
            "player": self.player_details,
            "word": self.word_details,
        }


def _team_dict(team) -> Optional[dict]:
    if not team:
        return None
    return {"id": team.id, "name": team.name, "color": team.color}


def _fetch_player(player_id: str) -> Optional[dict]:
    """Fetch player details from DB."""
    from models import Player
    engine = get_engine()
    with SQLSession(engine) as session:
        player = session.get(Player, player_id)
        if player:
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
    return None


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


def _fetch_scoreboard(session_id: str) -> tuple[list, list]:
    """Fetch per-player and per-team scoreboard data from DB."""
    from models import Player, Team, Turn, Session as SessionModel
    engine = get_engine()
    with SQLSession(engine) as session:
        sess = session.get(SessionModel, session_id)
        if not sess:
            return [], []

        teams = session.exec(select(Team).where(Team.session_id == session_id).order_by(Team.sort_order)).all()
        team_map = {t.id: t for t in teams}

        players = session.exec(select(Player).where(Player.session_id == session_id).order_by(Player.sort_order)).all()
        turns = session.exec(select(Turn).where(Turn.session_id == session_id)).all()

        scoreboard = []
        for player in players:
            player_turns = [t for t in turns if t.player_id == player.id]
            correct = sum(1 for t in player_turns if t.result == "correct")
            incorrect = sum(1 for t in player_turns if t.result == "incorrect")
            timeout = sum(1 for t in player_turns if t.result == "timeout")
            rounds_survived = player.elimination_round - 1 if player.elimination_round else sess.current_round

            team = team_map.get(player.team_id)
            scoreboard.append({
                "player_id": player.id,
                "player_name": player.name,
                "team_id": player.team_id,
                "team_name": team.name if team else None,
                "team_color": team.color if team else None,
                "eliminated": player.eliminated,
                "total_correct": correct,
                "total_incorrect": incorrect,
                "total_timeout": timeout,
                "rounds_survived": rounds_survived,
            })

        team_scoreboard = []
        for team in teams:
            members = [p for p in scoreboard if p["team_id"] == team.id]
            team_scoreboard.append({
                "team_id": team.id,
                "team_name": team.name,
                "team_color": team.color,
                "players_count": len(members),
                "active_count": sum(1 for p in members if not p["eliminated"]),
                "total_correct": sum(p["total_correct"] for p in members),
                "total_attempts": sum(p["total_correct"] + p["total_incorrect"] + p["total_timeout"] for p in members),
            })
        team_scoreboard.sort(key=lambda t: t["total_correct"], reverse=True)
        return scoreboard, team_scoreboard


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.game_states: Dict[str, GameState] = {}

    def get_state(self, session_id: str) -> GameState:
        if session_id not in self.game_states:
            self.game_states[session_id] = GameState()
        return self.game_states[session_id]

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(ws)
        # Send initial state
        state = self.get_state(session_id)
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

        if cmd_type == "SET_ACTIVE_PLAYER":
            state.current_player_id = command.get("player_id")
            state.player_details = _fetch_player(state.current_player_id) if state.current_player_id else None

        elif cmd_type == "SET_ACTIVE_WORD":
            state.current_word_id = command.get("word_id")
            state.word_details = _fetch_word(state.current_word_id) if state.current_word_id else None
            state.revealed_info.clear()
            state.result = None
            if state.current_player_id and state.current_word_id:
                state.display_mode = "spelling"

        elif cmd_type == "START_TIMER":
            state.timer_running = True

        elif cmd_type == "PAUSE_TIMER":
            state.timer_running = False

        elif cmd_type == "RESET_TIMER":
            state.timer_running = False
            state.timer_seconds_remaining = command.get("duration", state.timer_duration)

        elif cmd_type == "UPDATE_TIMER":
            # Controller sends timer ticks
            state.timer_seconds_remaining = command.get("seconds_remaining", state.timer_seconds_remaining)

        elif cmd_type == "SET_TIMER_DURATION":
            state.timer_duration = command.get("duration", 120)
            state.timer_seconds_remaining = state.timer_duration

        elif cmd_type == "MARK_CORRECT":
            state.result = "correct"
            state.display_mode = "result"
            state.timer_running = False

        elif cmd_type == "MARK_INCORRECT":
            state.result = "incorrect"
            state.display_mode = "result"
            state.timer_running = False

        elif cmd_type == "MARK_TIMEOUT":
            state.result = "timeout"
            state.display_mode = "result"
            state.timer_running = False

        elif cmd_type == "REVEAL_INFO":
            info_type = command.get("info_type")
            if info_type:
                state.revealed_info.add(info_type)

        elif cmd_type == "HIDE_INFO":
            info_type = command.get("info_type")
            if info_type in state.revealed_info:
                state.revealed_info.remove(info_type)

        elif cmd_type == "CLEAR_DISPLAY":
            state.display_mode = "idle"
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

        elif cmd_type == "NEXT_ROUND":
            state.round_number += 1
            state.result = None
            state.revealed_info.clear()

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

        # Include scoreboard data when in scoreboard mode
        if state.display_mode == "scoreboard":
            payload["scoreboard"], payload["team_scoreboard"] = _fetch_scoreboard(session_id)

        await self.broadcast(session_id, payload)


manager = ConnectionManager()
