from __future__ import annotations

from collections import defaultdict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Match, TeamMatchStats
from app.services.normalization import minmax_score, to_float


def _stats_query(team_id: int, competition_id: int):
    return (
        select(TeamMatchStats, Match)
        .join(Match, Match.id == TeamMatchStats.match_id)
        .where(
            TeamMatchStats.team_id == team_id,
            Match.competition_id == competition_id,
            Match.status == "finished",
        )
    )


def get_last_matches(
    db: Session, team_id: int, competition_id: int, window: int
) -> list[int]:
    rows = db.execute(
        _stats_query(team_id, competition_id)
        .order_by(Match.match_date_time.desc())
        .limit(window)
    ).all()
    return [match.id for _, match in rows]


def _slice_stats(
    db: Session, team_id: int, competition_id: int, window: int, offset: int = 0
):
    rows = db.execute(
        _stats_query(team_id, competition_id)
        .order_by(Match.match_date_time.desc())
        .offset(offset)
        .limit(window)
    ).all()
    return rows


def _avg(values: list[float | int]) -> float | None:
    return sum(values) / len(values) if values else None


def _goals_against(match: Match, stats: TeamMatchStats) -> int | None:
    if match.score_home is None or match.score_away is None:
        return None
    return match.score_away if stats.is_home else match.score_home


def get_team_averages(
    db: Session, team_id: int, competition_id: int, window: int
):
    rows = _slice_stats(db, team_id, competition_id, window)
    stats_rows = [row[0] for row in rows]
    match_rows = [row[1] for row in rows]

    goals_against_vals = [
        _goals_against(match, stats)
        for match, stats in zip(match_rows, stats_rows)
        if _goals_against(match, stats) is not None
    ]

    return {
        "possession": _avg([s.possession for s in stats_rows if s.possession is not None]),
        "shots": _avg([s.shots for s in stats_rows if s.shots is not None]),
        "shots_on_target": _avg(
            [s.shots_on_target for s in stats_rows if s.shots_on_target is not None]
        ),
        "passes": _avg([s.passes for s in stats_rows if s.passes is not None]),
        "pass_accuracy": _avg(
            [s.pass_accuracy for s in stats_rows if s.pass_accuracy is not None]
        ),
        "corners": _avg([s.corners for s in stats_rows if s.corners is not None]),
        "fouls": _avg([s.fouls for s in stats_rows if s.fouls is not None]),
        "yellow_cards": _avg(
            [s.yellow_cards for s in stats_rows if s.yellow_cards is not None]
        ),
        "red_cards": _avg(
            [s.red_cards for s in stats_rows if s.red_cards is not None]
        ),
        "xg": _avg([s.xg for s in stats_rows if s.xg is not None]),
        "goals_for": _avg([s.goals for s in stats_rows if s.goals is not None]),
        "goals_against": _avg(goals_against_vals),
    }


def get_team_trend(
    db: Session, team_id: int, competition_id: int, window: int
):
    rows = _slice_stats(db, team_id, competition_id, window * 2)
    if len(rows) < window * 2:
        return None

    current_rows = rows[:window]
    previous_rows = rows[window : window * 2]

    def to_avg(rows_slice):
        stats_rows = [row[0] for row in rows_slice]
        match_rows = [row[1] for row in rows_slice]
        goals_against_vals = [
            _goals_against(match, stats)
            for match, stats in zip(match_rows, stats_rows)
            if _goals_against(match, stats) is not None
        ]
        return {
            "possession": _avg([s.possession for s in stats_rows if s.possession is not None]),
            "shots": _avg([s.shots for s in stats_rows if s.shots is not None]),
            "shots_on_target": _avg(
                [s.shots_on_target for s in stats_rows if s.shots_on_target is not None]
            ),
            "passes": _avg([s.passes for s in stats_rows if s.passes is not None]),
            "pass_accuracy": _avg(
                [s.pass_accuracy for s in stats_rows if s.pass_accuracy is not None]
            ),
            "corners": _avg([s.corners for s in stats_rows if s.corners is not None]),
            "fouls": _avg([s.fouls for s in stats_rows if s.fouls is not None]),
            "yellow_cards": _avg(
                [s.yellow_cards for s in stats_rows if s.yellow_cards is not None]
            ),
            "red_cards": _avg(
                [s.red_cards for s in stats_rows if s.red_cards is not None]
            ),
            "xg": _avg([s.xg for s in stats_rows if s.xg is not None]),
            "goals_for": _avg([s.goals for s in stats_rows if s.goals is not None]),
            "goals_against": _avg(goals_against_vals),
        }

    current = to_avg(current_rows)
    previous = to_avg(previous_rows)

    deltas = {}
    for key, value in current.items():
        prev_value = previous.get(key)
        if value is None or prev_value is None:
            deltas[key] = None
        else:
            deltas[key] = value - prev_value

    return deltas


def get_team_radar(
    db: Session,
    team_id: int,
    competition_id: int,
    window: int,
    min_matches: int,
    min_teams: int,
):
    averages = get_team_averages(db, team_id, competition_id, window)
    metrics = {
        "xg": averages["xg"],
        "possession": averages["possession"],
        "shots": averages["shots"],
        "shots_on_target": averages["shots_on_target"],
        "passes": averages["passes"],
        "pass_accuracy": averages["pass_accuracy"],
        "corners": averages["corners"],
        "fouls": averages["fouls"],
        "yellow_cards": averages["yellow_cards"],
        "red_cards": averages["red_cards"],
    }

    ranked = (
        select(
            TeamMatchStats.team_id.label("team_id"),
            TeamMatchStats.xg.label("xg"),
            TeamMatchStats.possession.label("possession"),
            TeamMatchStats.shots.label("shots"),
            TeamMatchStats.shots_on_target.label("shots_on_target"),
            TeamMatchStats.passes.label("passes"),
            TeamMatchStats.pass_accuracy.label("pass_accuracy"),
            TeamMatchStats.corners.label("corners"),
            TeamMatchStats.fouls.label("fouls"),
            TeamMatchStats.yellow_cards.label("yellow_cards"),
            TeamMatchStats.red_cards.label("red_cards"),
            func.row_number()
            .over(
                partition_by=TeamMatchStats.team_id,
                order_by=Match.match_date_time.desc(),
            )
            .label("rn"),
        )
        .join(Match, Match.id == TeamMatchStats.match_id)
        .where(
            Match.competition_id == competition_id,
            Match.status == "finished",
        )
        .subquery()
    )

    per_team = db.execute(
        select(
            ranked.c.team_id,
            func.count().label("matches"),
            func.avg(ranked.c.xg).label("xg"),
            func.avg(ranked.c.possession).label("possession"),
            func.avg(ranked.c.shots).label("shots"),
            func.avg(ranked.c.shots_on_target).label("shots_on_target"),
            func.avg(ranked.c.passes).label("passes"),
            func.avg(ranked.c.pass_accuracy).label("pass_accuracy"),
            func.avg(ranked.c.corners).label("corners"),
            func.avg(ranked.c.fouls).label("fouls"),
            func.avg(ranked.c.yellow_cards).label("yellow_cards"),
            func.avg(ranked.c.red_cards).label("red_cards"),
        )
        .where(ranked.c.rn <= window)
        .group_by(ranked.c.team_id)
    ).all()

    eligible_rows = [row for row in per_team if row.matches >= min_matches]
    eligible_teams = len(eligible_rows)

    if eligible_teams < min_teams:
        return {
            "eligible_teams": eligible_teams,
            "metrics": {key: None for key in metrics.keys()},
            "note": "insufficient sample",
        }

    ranges = defaultdict(lambda: {"min": None, "max": None})
    for row in eligible_rows:
        for key in metrics.keys():
            value = to_float(getattr(row, key))
            if value is None:
                continue
            current_min = ranges[key]["min"]
            current_max = ranges[key]["max"]
            ranges[key]["min"] = value if current_min is None else min(current_min, value)
            ranges[key]["max"] = value if current_max is None else max(current_max, value)

    normalized = {}
    inverted_metrics = {"fouls", "yellow_cards", "red_cards"}
    for key, value in metrics.items():
        normalized[key] = minmax_score(
            value,
            ranges[key]["min"],
            ranges[key]["max"],
            invert=key in inverted_metrics,
        )

    return {
        "eligible_teams": eligible_teams,
        "metrics": normalized,
        "note": None,
    }


def get_team_timeseries(db: Session, team_id: int, competition_id: int):
    rows = db.execute(
        _stats_query(team_id, competition_id).order_by(Match.round_number.asc())
    ).all()
    points = []
    for stats, match in rows:
        goals_against = _goals_against(match, stats)
        points.append(
            {
                "match_id": match.id,
                "round_number": match.round_number,
                "match_date_time": match.match_date_time,
                "is_home": stats.is_home,
                "goals_for": stats.goals,
                "goals_against": goals_against,
                "possession": stats.possession,
                "xg": stats.xg,
                "shots": stats.shots,
                "passes": stats.passes,
            }
        )
    return points
