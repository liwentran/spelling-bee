from sqlmodel import Session as DbSession, select
from models import Session, Team, Player, Turn


def _tally(turns) -> dict:
    correct = sum(1 for t in turns if t.result == "correct")
    incorrect = sum(1 for t in turns if t.result == "incorrect")
    timeout = sum(1 for t in turns if t.result == "timeout")
    return {
        "total_correct": correct,
        "total_incorrect": incorrect,
        "total_timeout": timeout,
        "total_attempts": correct + incorrect + timeout,
    }


def compute_scoreboard(db: DbSession, session_id: str) -> dict:
    """Per-player and per-team scores for a session: {"players": [...], "teams": [...], "winner": ...}.

    Team mode: turns carry team_id (player_id is the optional speller), and teams are eliminated.
    Individual mode: turns carry player_id; team totals (if teams exist) sum their members.
    """
    sess = db.get(Session, session_id)
    if not sess:
        return {"players": [], "teams": []}

    teams = db.exec(select(Team).where(Team.session_id == session_id).order_by(Team.sort_order)).all()
    players = db.exec(select(Player).where(Player.session_id == session_id).order_by(Player.sort_order)).all()
    turns = db.exec(select(Turn).where(Turn.session_id == session_id)).all()
    team_map = {t.id: t for t in teams}

    def rounds_survived(entity):
        return entity.elimination_round - 1 if entity.elimination_round else sess.current_round

    player_rows = []
    for player in players:
        team = team_map.get(player.team_id)
        player_rows.append({
            "player_id": player.id,
            "player_name": player.name,
            "team_id": player.team_id,
            "team_name": team.name if team else None,
            "team_color": team.color if team else None,
            "eliminated": player.eliminated,
            "rounds_survived": rounds_survived(player),
            **_tally([t for t in turns if t.player_id == player.id]),
        })

    team_rows = []
    for team in teams:
        member_ids = {p.id for p in players if p.team_id == team.id}
        if sess.game_mode == "team":
            team_turns = [t for t in turns if t.team_id == team.id]
            eliminated = team.eliminated
        else:
            team_turns = [t for t in turns if t.player_id in member_ids]
            eliminated = False
        team_rows.append({
            "team_id": team.id,
            "team_name": team.name,
            "team_color": team.color,
            "players_count": len(member_ids),
            "active_count": sum(1 for p in players if p.id in member_ids and not p.eliminated),
            "eliminated": eliminated,
            "rounds_survived": rounds_survived(team),
            **_tally(team_turns),
        })
    # Team games list teams in turn order (Team.sort_order, set by dragging/shuffling on the controller),
    # so the TV scoreboard matches the controller. Otherwise: standing first, most right, fewest misses.
    rank = lambda r: (r["eliminated"], -r["total_correct"], r["total_attempts"] - r["total_correct"])
    if sess.game_mode != "team":
        team_rows.sort(key=rank)

    # Elimination mode ends when one contestant is left standing (once someone has been knocked out)
    winner = None
    contestants = team_rows if sess.game_mode == "team" else [{**p, "name": p["player_name"]} for p in player_rows]
    standing = [c for c in contestants if not c["eliminated"]]
    if sess.elimination_mode and len(contestants) > 1 and len(standing) == 1:
        w = standing[0]
        winner = {"name": w.get("team_name") if sess.game_mode == "team" else w["name"], "color": w.get("team_color")}

    return {"players": player_rows, "teams": team_rows, "winner": winner}
