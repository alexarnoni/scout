from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)

from app.core.config import DATABASE_URL
from app.models import Competition, Player, Roster, Staff, Team
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def normalize_role(value: str | None) -> str | None:
    if not value:
        return None
    return " ".join(value.strip().lower().split())


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def upsert_competition(db, payload: dict) -> Competition:
    external_id = (payload.get("external_ids") or {}).get("fpf")
    season = payload.get("season")

    competition = None
    if external_id:
        competition = db.execute(
            select(Competition).where(
                Competition.source_ids["fpf"].as_string() == external_id
            )
        ).scalar_one_or_none()

    if not competition and season:
        competition = db.execute(
            select(Competition).where(
                Competition.name == payload["name"],
                Competition.season == season,
            )
        ).scalar_one_or_none()

    if not competition and season:
        legacy_name = f"{payload['name']} {season}"
        competition = db.execute(
            select(Competition).where(Competition.name == legacy_name)
        ).scalar_one_or_none()

    if not competition:
        competition = db.execute(
            select(Competition).where(Competition.name == payload["name"])
        ).scalar_one_or_none()

    if not competition:
        competition = Competition(name=payload["name"], season=season)
        db.add(competition)
        db.flush()
    else:
        competition.name = payload["name"]
        if season:
            competition.season = season

    if external_id:
        source_ids = competition.source_ids or {}
        source_ids["fpf"] = external_id
        competition.source_ids = source_ids

    return competition


def upsert_team(db, competition_id: int, payload: dict) -> Team:
    external_id = (payload.get("external_ids") or {}).get("fpf")
    team = None

    if external_id:
        team = db.execute(
            select(Team).where(Team.external_ids["fpf"].as_string() == external_id)
        ).scalar_one_or_none()

    if not team:
        team = db.execute(
            select(Team).where(
                Team.competition_id == competition_id,
                Team.name == payload["name"],
            )
        ).scalar_one_or_none()

    if not team:
        team = Team(competition_id=competition_id, name=payload["name"])
        db.add(team)
        db.flush()
    else:
        team.name = payload["name"]
        team.competition_id = competition_id

    if payload.get("external_ids"):
        team.external_ids = payload["external_ids"]
    if payload.get("logo_url"):
        team.logo_url = payload["logo_url"]
    if payload.get("city"):
        team.city = payload["city"]

    return team


def upsert_staff(db, team_id: int, payload: dict) -> Staff:
    external_id = (payload.get("external_ids") or {}).get("fpf")
    role = normalize_role(payload.get("role"))
    staff_member = None

    if external_id:
        staff_member = db.execute(
            select(Staff).where(
                Staff.external_ids["fpf"].as_string() == external_id
            )
        ).scalar_one_or_none()

    if not staff_member:
        staff_member = db.execute(
            select(Staff).where(
                Staff.team_id == team_id,
                Staff.name == payload["name"],
                Staff.role == role,
            )
        ).scalar_one_or_none()

    if not staff_member:
        staff_member = Staff(team_id=team_id, name=payload["name"], role=role)
        db.add(staff_member)
        db.flush()
    else:
        staff_member.name = payload["name"]
        staff_member.team_id = team_id
        staff_member.role = role

    if payload.get("external_ids"):
        staff_member.external_ids = payload["external_ids"]
    if payload.get("photo_url"):
        staff_member.photo_url = payload["photo_url"]

    return staff_member


def upsert_player(db, team_id: int, payload: dict) -> Player:
    external_id = (payload.get("external_ids") or {}).get("fpf")
    player = None

    if external_id:
        player = db.execute(
            select(Player).where(Player.external_ids["fpf"].as_string() == external_id)
        ).scalar_one_or_none()

    if not player:
        player = db.execute(
            select(Player).where(
                Player.team_id == team_id,
                Player.name == payload["name"],
            )
        ).scalar_one_or_none()

    if not player:
        player = Player(team_id=team_id, name=payload["name"])
        db.add(player)
        db.flush()
    else:
        player.team_id = team_id
        player.name = payload["name"]

    if payload.get("position") is not None:
        player.position = payload.get("position")
    if payload.get("number") is not None:
        player.shirt_number = payload.get("number")
    if payload.get("external_ids"):
        player.external_ids = payload["external_ids"]
    if payload.get("birth_date"):
        player.birth_date = parse_date(payload.get("birth_date"))
    if payload.get("nationality"):
        player.nationality = payload.get("nationality")
    if payload.get("photo_url"):
        player.photo_url = payload.get("photo_url")
    if payload.get("height_cm") is not None:
        player.height_cm = payload.get("height_cm")
    if payload.get("preferred_foot"):
        player.preferred_foot = payload.get("preferred_foot")

    return player


def upsert_roster_entry(db, competition_id: int, team_id: int, player_id: int) -> None:
    existing = db.execute(
        select(Roster).where(
            Roster.competition_id == competition_id,
            Roster.team_id == team_id,
            Roster.player_id == player_id,
        )
    ).scalar_one_or_none()
    if not existing:
        db.add(
            Roster(
                competition_id=competition_id,
                team_id=team_id,
                player_id=player_id,
            )
        )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m scripts.import_fpf_layer2 <path>")

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        raise SystemExit(f"File not found: {json_path}")

    with json_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    competition_payload = data["competition"]
    teams_payload = data.get("teams", [])

    competitions_count = 0
    teams_count = 0
    staff_count = 0
    players_count = 0

    with SessionLocal() as db:
        competition = upsert_competition(db, competition_payload)
        competitions_count = 1

        for team_payload in teams_payload:
            team = upsert_team(db, competition.id, team_payload)
            teams_count += 1

            for staff_payload in team_payload.get("staff", []):
                upsert_staff(db, team.id, staff_payload)
                staff_count += 1

            for player_payload in team_payload.get("players", []):
                player = upsert_player(db, team.id, player_payload)
                players_count += 1
                upsert_roster_entry(db, competition.id, team.id, player.id)

        db.commit()

    print(
        "Imported/updated: "
        f"competitions={competitions_count} "
        f"teams={teams_count} "
        f"staff={staff_count} "
        f"players={players_count}"
    )


if __name__ == "__main__":
    main()
