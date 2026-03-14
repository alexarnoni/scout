from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Match, PlayerMatchStats


def _stats_query(player_id: int, competition_id: int):
    return (
        select(PlayerMatchStats, Match)
        .join(Match, Match.id == PlayerMatchStats.match_id)
        .where(
            PlayerMatchStats.player_id == player_id,
            Match.competition_id == competition_id,
            Match.status == "finished",
        )
    )


def _avg(values: list[float | int]) -> float | None:
    return sum(values) / len(values) if values else None


def _to_f(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def get_last_matches(
    db: Session, player_id: int, competition_id: int, window: int
) -> list[int]:
    rows = db.execute(
        _stats_query(player_id, competition_id)
        .order_by(Match.match_date_time.desc())
        .limit(window)
    ).all()
    return [match.id for _, match in rows]


def get_player_averages(
    db: Session, player_id: int, competition_id: int, window: int
):
    rows = db.execute(
        _stats_query(player_id, competition_id)
        .order_by(Match.match_date_time.desc())
        .limit(window)
    ).all()
    stats_rows = [row[0] for row in rows]

    return {
        "minutes_played": _avg([s.minutes for s in stats_rows if s.minutes is not None]),
        "goals": _avg([s.goals for s in stats_rows if s.goals is not None]),
        "assists": _avg([s.assists for s in stats_rows if s.assists is not None]),
        "shots": _avg([s.shots for s in stats_rows if s.shots is not None]),
        "shots_on_target": _avg(
            [s.shots_on_target for s in stats_rows if s.shots_on_target is not None]
        ),
        "key_passes": _avg(
            [s.key_passes for s in stats_rows if s.key_passes is not None]
        ),
        "passes": _avg([s.passes for s in stats_rows if s.passes is not None]),
        "pass_accuracy": _avg(
            [s.pass_accuracy for s in stats_rows if s.pass_accuracy is not None]
        ),
        "tackles": _avg([s.tackles for s in stats_rows if s.tackles is not None]),
        "interceptions": _avg(
            [s.interceptions for s in stats_rows if s.interceptions is not None]
        ),
        "duels_won": _avg([s.duels_won for s in stats_rows if s.duels_won is not None]),
        "fouls_committed": _avg(
            [s.fouls_committed for s in stats_rows if s.fouls_committed is not None]
        ),
        "yellow_cards": _avg(
            [s.yellow_cards for s in stats_rows if s.yellow_cards is not None]
        ),
        "red_cards": _avg(
            [s.red_cards for s in stats_rows if s.red_cards is not None]
        ),
        "rating": _avg([s.rating for s in stats_rows if s.rating is not None]),
        "xg": _avg([s.xg for s in stats_rows if s.xg is not None]),
        "xa": _avg([s.xa for s in stats_rows if s.xa is not None]),
    }


def get_player_radar(
    db: Session,
    player_id: int,
    competition_id: int,
    window: int,
    min_matches: int,
    min_players: int,
):
    averages = get_player_averages(db, player_id, competition_id, window)
    metrics = {
        "minutes_played": averages["minutes_played"],
        "goals": averages["goals"],
        "assists": averages["assists"],
        "shots": averages["shots"],
        "shots_on_target": averages["shots_on_target"],
        "key_passes": averages["key_passes"],
        "passes": averages["passes"],
        "pass_accuracy": averages["pass_accuracy"],
        "tackles": averages["tackles"],
        "interceptions": averages["interceptions"],
        "duels_won": averages["duels_won"],
        "fouls_committed": averages["fouls_committed"],
        "yellow_cards": averages["yellow_cards"],
        "red_cards": averages["red_cards"],
        "rating": averages["rating"],
        "xg": averages["xg"],
        "xa": averages["xa"],
    }

    ranked = (
        select(
            PlayerMatchStats.player_id.label("player_id"),
            PlayerMatchStats.minutes.label("minutes_played"),
            PlayerMatchStats.goals.label("goals"),
            PlayerMatchStats.assists.label("assists"),
            PlayerMatchStats.shots.label("shots"),
            PlayerMatchStats.shots_on_target.label("shots_on_target"),
            PlayerMatchStats.key_passes.label("key_passes"),
            PlayerMatchStats.passes.label("passes"),
            PlayerMatchStats.pass_accuracy.label("pass_accuracy"),
            PlayerMatchStats.tackles.label("tackles"),
            PlayerMatchStats.interceptions.label("interceptions"),
            PlayerMatchStats.duels_won.label("duels_won"),
            PlayerMatchStats.fouls_committed.label("fouls_committed"),
            PlayerMatchStats.yellow_cards.label("yellow_cards"),
            PlayerMatchStats.red_cards.label("red_cards"),
            PlayerMatchStats.rating.label("rating"),
            PlayerMatchStats.xg.label("xg"),
            PlayerMatchStats.xa.label("xa"),
            func.row_number()
            .over(
                partition_by=PlayerMatchStats.player_id,
                order_by=Match.match_date_time.desc(),
            )
            .label("rn"),
        )
        .join(Match, Match.id == PlayerMatchStats.match_id)
        .where(
            Match.competition_id == competition_id,
            Match.status == "finished",
        )
        .subquery()
    )

    per_player = db.execute(
        select(
            ranked.c.player_id,
            func.count().label("matches"),
            func.avg(ranked.c.minutes_played).label("minutes_played"),
            func.avg(ranked.c.goals).label("goals"),
            func.avg(ranked.c.assists).label("assists"),
            func.avg(ranked.c.shots).label("shots"),
            func.avg(ranked.c.shots_on_target).label("shots_on_target"),
            func.avg(ranked.c.key_passes).label("key_passes"),
            func.avg(ranked.c.passes).label("passes"),
            func.avg(ranked.c.pass_accuracy).label("pass_accuracy"),
            func.avg(ranked.c.tackles).label("tackles"),
            func.avg(ranked.c.interceptions).label("interceptions"),
            func.avg(ranked.c.duels_won).label("duels_won"),
            func.avg(ranked.c.fouls_committed).label("fouls_committed"),
            func.avg(ranked.c.yellow_cards).label("yellow_cards"),
            func.avg(ranked.c.red_cards).label("red_cards"),
            func.avg(ranked.c.rating).label("rating"),
            func.avg(ranked.c.xg).label("xg"),
            func.avg(ranked.c.xa).label("xa"),
        )
        .where(ranked.c.rn <= window)
        .group_by(ranked.c.player_id)
    ).all()

    eligible_rows = [row for row in per_player if row.matches >= min_matches]
    eligible_players = len(eligible_rows)
    if eligible_players < min_players:
        return {
            "eligible_players": eligible_players,
            "metrics": {key: None for key in metrics.keys()},
            "note": "insufficient sample",
        }

    ranges = defaultdict(lambda: {"min": None, "max": None})
    for row in eligible_rows:
        for key in metrics.keys():
            value = _to_f(getattr(row, key))
            if value is None:
                continue
            current_min = ranges[key]["min"]
            current_max = ranges[key]["max"]
            ranges[key]["min"] = value if current_min is None else min(current_min, value)
            ranges[key]["max"] = value if current_max is None else max(current_max, value)

    normalized = {}
    for key, value in metrics.items():
        value = _to_f(value)
        if value is None:
            normalized[key] = None
            continue
        min_val = _to_f(ranges[key]["min"])
        max_val = _to_f(ranges[key]["max"])
        if min_val is None or max_val is None:
            normalized[key] = None
            continue
        if max_val == min_val:
            score = 50.0
        else:
            score = (value - min_val) / (max_val - min_val) * 100
            score = max(0.0, min(100.0, score))
        normalized[key] = round(score, 2)

    return {
        "eligible_players": eligible_players,
        "metrics": normalized,
        "note": None,
    }


def get_player_timeseries(db: Session, player_id: int, competition_id: int):
    rows = db.execute(
        _stats_query(player_id, competition_id).order_by(Match.round_number.asc())
    ).all()
    points = []
    for stats, match in rows:
        points.append(
            {
                "match_id": match.id,
                "round_number": match.round_number,
                "match_date_time": match.match_date_time,
                "minutes_played": stats.minutes,
                "rating": stats.rating,
                "goals": stats.goals,
                "assists": stats.assists,
                "shots": stats.shots,
                "shots_on_target": stats.shots_on_target,
                "key_passes": stats.key_passes,
                "passes": stats.passes,
                "pass_accuracy": stats.pass_accuracy,
                "tackles": stats.tackles,
                "interceptions": stats.interceptions,
                "duels_won": stats.duels_won,
                "fouls_committed": stats.fouls_committed,
                "yellow_cards": stats.yellow_cards,
                "red_cards": stats.red_cards,
                "xg": stats.xg,
                "xa": stats.xa,
            }
        )
    return points
