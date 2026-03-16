from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.player_match_stats import PlayerMatchStats
from app.models.team import Team
from app.models.match import Match
from app.models.team_match_stats import TeamMatchStats

POSITION_GROUPS: dict[str, str | None] = {
    "Goalkeeper": "Goleiro",
    "Defender": "Defensor",
    "Center Defender": "Defensor",
    "Center Left Defender": "Defensor",
    "Center Right Defender": "Defensor",
    "Left Back": "Defensor",
    "Right Back": "Defensor",
    "Midfielder": "Meio-campo",
    "Center Midfielder": "Meio-campo",
    "Center Left Midfielder": "Meio-campo",
    "Center Right Midfielder": "Meio-campo",
    "Left Midfielder": "Meio-campo",
    "Right Midfielder": "Meio-campo",
    "Defensive Midfielder": "Meio-campo",
    "Attacking Midfielder": "Meio-campo",
    "Attacking Midfielder Left": "Meio-campo",
    "Attacking Midfielder Right": "Meio-campo",
    "Forward": "Atacante",
    "Center Left Forward": "Atacante",
    "Center Right Forward": "Atacante",
    "Left Forward": "Atacante",
    "Right Forward": "Atacante",
    "Substitute": None,
}

# Metrics per group: (name, inverted)
GROUP_METRICS: dict[str, list[tuple[str, bool]]] = {
    "Goleiro": [
        ("saves_p90", False),
        ("goals_conceded_p90", True),
        ("clean_sheet_rate", False),
        ("yellow_cards_p90", True),
    ],
    "Defensor": [
        ("goals_p90", False),
        ("assists_p90", False),
        ("shots_p90", False),
        ("fouls_p90", True),
        ("yellow_cards_p90", True),
        ("red_cards_p90", True),
    ],
    "Meio-campo": [
        ("goals_p90", False),
        ("assists_p90", False),
        ("shots_p90", False),
        ("shots_on_target_p90", False),
        ("fouls_p90", True),
        ("yellow_cards_p90", True),
    ],
    "Atacante": [
        ("goals_p90", False),
        ("assists_p90", False),
        ("shots_p90", False),
        ("shots_on_target_p90", False),
        ("conversion_rate", False),
        ("yellow_cards_p90", True),
    ],
}


def _p90(value: float, minutes: float) -> float:
    if minutes <= 0:
        return 0.0
    return value / (minutes / 90)


def _normalize(values: list[float], inverted: bool) -> list[float]:
    """Min-max normalize to 0-100. If all equal, return 50 for all."""
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [50.0] * len(values)
    normalized = [(v - min_v) / (max_v - min_v) * 100 for v in values]
    if inverted:
        normalized = [100 - n for n in normalized]
    return normalized


def _aggregate_player_stats(
    db: Session, competition_id: int, position_group: str, min_minutes: int
) -> list[dict]:
    """Fetch and aggregate raw stats per player."""
    # Resolve ESPN position strings for this group
    espn_positions = [
        pos for pos, grp in POSITION_GROUPS.items() if grp == position_group
    ]
    if not espn_positions:
        return []

    # Base aggregation query
    rows = db.execute(
        select(
            Player.id,
            Player.name,
            Player.position,
            Team.name.label("team_name"),
            func.sum(PlayerMatchStats.minutes).label("total_minutes"),
            func.count(PlayerMatchStats.id).label("matches_played"),
            func.sum(func.coalesce(PlayerMatchStats.goals, 0)).label("goals"),
            func.sum(func.coalesce(PlayerMatchStats.assists, 0)).label("assists"),
            func.sum(func.coalesce(PlayerMatchStats.shots, 0)).label("shots"),
            func.sum(func.coalesce(PlayerMatchStats.shots_on_target, 0)).label("shots_on_target"),
            func.sum(func.coalesce(PlayerMatchStats.fouls_committed, 0)).label("fouls"),
            func.sum(func.coalesce(PlayerMatchStats.yellow_cards, 0)).label("yellow_cards"),
            func.sum(func.coalesce(PlayerMatchStats.red_cards, 0)).label("red_cards"),
            func.sum(func.coalesce(PlayerMatchStats.saves, 0)).label("saves"),
        )
        .join(Team, Team.id == Player.team_id)
        .join(PlayerMatchStats, PlayerMatchStats.player_id == Player.id)
        .join(Match, Match.id == PlayerMatchStats.match_id)
        .where(
            Match.competition_id == competition_id,
            Player.position.in_(espn_positions),
        )
        .group_by(Player.id, Player.name, Player.position, Team.name)
        .having(func.sum(PlayerMatchStats.minutes) >= min_minutes)
    ).mappings().all()

    return [dict(r) for r in rows]


def _get_goals_conceded(
    db: Session, competition_id: int, player_ids: list[int]
) -> dict[int, dict]:
    """
    For GK: calculate goals conceded and clean sheets per player.
    Uses Match scores + TeamMatchStats.is_home to determine goals against.
    """
    if not player_ids:
        return {}

    rows = db.execute(
        select(
            PlayerMatchStats.player_id,
            Match.score_home,
            Match.score_away,
            TeamMatchStats.is_home,
        )
        .join(Match, Match.id == PlayerMatchStats.match_id)
        .join(
            TeamMatchStats,
            (TeamMatchStats.match_id == Match.id)
            & (TeamMatchStats.team_id == PlayerMatchStats.team_id),
        )
        .where(
            Match.competition_id == competition_id,
            PlayerMatchStats.player_id.in_(player_ids),
            Match.score_home.is_not(None),
            Match.score_away.is_not(None),
        )
    ).all()

    result: dict[int, dict] = {}
    for player_id, score_home, score_away, is_home in rows:
        goals_against = score_away if is_home else score_home
        if player_id not in result:
            result[player_id] = {"goals_conceded": 0, "clean_sheets": 0, "matches": 0}
        result[player_id]["goals_conceded"] += goals_against
        result[player_id]["matches"] += 1
        if goals_against == 0:
            result[player_id]["clean_sheets"] += 1

    return result


def get_scout_ranking(
    db: Session,
    competition_id: int,
    position_group: str,
    min_minutes: int = 180,
) -> list[dict]:
    if position_group not in GROUP_METRICS:
        return []

    players = _aggregate_player_stats(db, competition_id, position_group, min_minutes)
    if not players:
        return []

    # For GK, fetch goals conceded data
    gk_data: dict[int, dict] = {}
    if position_group == "Goleiro":
        gk_data = _get_goals_conceded(
            db, competition_id, [p["id"] for p in players]
        )

    # Build raw metrics per player
    player_metrics: list[dict] = []
    for p in players:
        minutes = float(p["total_minutes"] or 0)
        shots = int(p["shots"] or 0)
        goals = int(p["goals"] or 0)

        metrics: dict[str, float | None] = {}

        if position_group == "Goleiro":
            gk = gk_data.get(p["id"], {})
            goals_conceded = float(gk.get("goals_conceded", 0))
            clean_sheets = int(gk.get("clean_sheets", 0))
            gk_matches = int(gk.get("matches", 0))
            metrics["saves_p90"] = _p90(float(p["saves"] or 0), minutes)
            metrics["goals_conceded_p90"] = _p90(goals_conceded, minutes)
            metrics["clean_sheet_rate"] = (
                clean_sheets / gk_matches if gk_matches > 0 else 0.0
            )
            metrics["yellow_cards_p90"] = _p90(float(p["yellow_cards"] or 0), minutes)

        elif position_group == "Defensor":
            metrics["goals_p90"] = _p90(float(goals), minutes)
            metrics["assists_p90"] = _p90(float(p["assists"] or 0), minutes)
            metrics["shots_p90"] = _p90(float(shots), minutes)
            metrics["fouls_p90"] = _p90(float(p["fouls"] or 0), minutes)
            metrics["yellow_cards_p90"] = _p90(float(p["yellow_cards"] or 0), minutes)
            metrics["red_cards_p90"] = _p90(float(p["red_cards"] or 0), minutes)

        elif position_group == "Meio-campo":
            metrics["goals_p90"] = _p90(float(goals), minutes)
            metrics["assists_p90"] = _p90(float(p["assists"] or 0), minutes)
            metrics["shots_p90"] = _p90(float(shots), minutes)
            metrics["shots_on_target_p90"] = _p90(float(p["shots_on_target"] or 0), minutes)
            metrics["fouls_p90"] = _p90(float(p["fouls"] or 0), minutes)
            metrics["yellow_cards_p90"] = _p90(float(p["yellow_cards"] or 0), minutes)

        elif position_group == "Atacante":
            metrics["goals_p90"] = _p90(float(goals), minutes)
            metrics["assists_p90"] = _p90(float(p["assists"] or 0), minutes)
            metrics["shots_p90"] = _p90(float(shots), minutes)
            metrics["shots_on_target_p90"] = _p90(float(p["shots_on_target"] or 0), minutes)
            metrics["conversion_rate"] = goals / shots if shots > 0 else 0.0
            metrics["yellow_cards_p90"] = _p90(float(p["yellow_cards"] or 0), minutes)

        player_metrics.append({
            "player_id": p["id"],
            "player_name": p["name"],
            "team_name": p["team_name"],
            "position": p["position"],
            "total_minutes": int(minutes),
            "matches_played": int(p["matches_played"] or 0),
            "metrics": metrics,
        })

    # Normalize each metric across all players and compute score
    metric_defs = GROUP_METRICS[position_group]
    metric_names = [m[0] for m in metric_defs]
    inverted_map = {m[0]: m[1] for m in metric_defs}

    # Build column vectors
    columns: dict[str, list[float]] = {
        name: [pm["metrics"].get(name) or 0.0 for pm in player_metrics]
        for name in metric_names
    }

    normalized_columns: dict[str, list[float]] = {
        name: _normalize(columns[name], inverted_map[name])
        for name in metric_names
    }

    # Assign scores
    results = []
    for i, pm in enumerate(player_metrics):
        metric_scores = [normalized_columns[name][i] for name in metric_names]
        score = sum(metric_scores) / len(metric_scores)
        results.append({
            "player_id": pm["player_id"],
            "player_name": pm["player_name"],
            "team_name": pm["team_name"],
            "position": pm["position"],
            "total_minutes": pm["total_minutes"],
            "matches_played": pm["matches_played"],
            "score": round(score, 2),
            "metrics": pm["metrics"],
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
