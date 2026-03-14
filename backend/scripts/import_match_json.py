from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)

from app.core.config import DATABASE_URL
from app.models import Competition, Match, Team, TeamMatchStats

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    if "T" not in value and " " not in value:
        value = f"{value}T00:00:00"
    return datetime.fromisoformat(value)


def get_competition(db, name: str) -> Competition:
    competition = db.execute(
        select(Competition).where(Competition.name == name)
    ).scalar_one_or_none()
    if not competition:
        raise ValueError(f"Competition not found: {name}")
    return competition


def get_team(db, competition_id: int, name: str) -> Team:
    team = db.execute(
        select(Team).where(
            Team.competition_id == competition_id,
            Team.name == name,
        )
    ).scalar_one_or_none()
    if not team:
        raise ValueError(f"Team not found: {name}")
    return team


def upsert_match(db, competition_id: int, payload: dict) -> Match:
    match_date_time = parse_datetime(payload["date"])
    home_team = get_team(db, competition_id, payload["home_team"])
    away_team = get_team(db, competition_id, payload["away_team"])
    status = (
        "finished"
        if payload.get("score_home") is not None and payload.get("score_away") is not None
        else "scheduled"
    )

    match = db.execute(
        select(Match).where(
            Match.competition_id == competition_id,
            Match.match_date_time == match_date_time,
            Match.home_team_id == home_team.id,
            Match.away_team_id == away_team.id,
        )
    ).scalar_one_or_none()

    if not match:
        match = Match(
            competition_id=competition_id,
            round_number=payload["round"],
            match_date_time=match_date_time,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=status,
            score_home=payload.get("score_home"),
            score_away=payload.get("score_away"),
        )
        db.add(match)
        db.flush()
    else:
        match.round_number = payload["round"]
        match.status = status
        match.score_home = payload.get("score_home")
        match.score_away = payload.get("score_away")

    return match


def upsert_team_stats(db, match: Match, competition_id: int, stats: dict) -> None:
    team = get_team(db, competition_id, stats["team_name"])
    existing = db.execute(
        select(TeamMatchStats).where(
            TeamMatchStats.match_id == match.id,
            TeamMatchStats.team_id == team.id,
        )
    ).scalar_one_or_none()

    goals = match.score_home if stats["is_home"] else match.score_away
    payload = {
        "match_id": match.id,
        "team_id": team.id,
        "is_home": stats["is_home"],
        "goals": goals if goals is not None else 0,
        "possession": stats.get("possession"),
        "shots": stats.get("shots"),
        "shots_on_target": stats.get("shots_on_target"),
        "passes": stats.get("passes"),
        "pass_accuracy": stats.get("pass_accuracy"),
        "corners": stats.get("corners"),
        "fouls": stats.get("fouls"),
        "yellow_cards": stats.get("yellow_cards"),
        "red_cards": stats.get("red_cards"),
        "xg": stats.get("xg"),
    }

    if not existing:
        db.add(TeamMatchStats(**payload))
        return

    for key, value in payload.items():
        setattr(existing, key, value)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m scripts.import_match_json <path>")

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        raise SystemExit(f"File not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    with SessionLocal() as db:
        competition = get_competition(db, data["competition_name"])
        match = upsert_match(db, competition.id, data["match"])

        for team_stats in data.get("team_stats", []):
            upsert_team_stats(db, match, competition.id, team_stats)

        db.commit()


if __name__ == "__main__":
    main()
