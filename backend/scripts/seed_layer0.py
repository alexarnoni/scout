from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)

from app.core.config import DATABASE_URL
from app.models import Competition, Player, Roster, Team

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_or_create_competition(db) -> Competition:
    competition = db.execute(
        select(Competition).where(Competition.name == "Brasileirao 2026")
    ).scalar_one_or_none()
    if competition:
        return competition

    competition = Competition(name="Brasileirao 2026")
    db.add(competition)
    db.flush()
    return competition


def get_or_create_team(db, competition_id: int, name: str) -> Team:
    team = db.execute(
        select(Team).where(
            Team.competition_id == competition_id,
            Team.name == name,
        )
    ).scalar_one_or_none()
    if team:
        return team

    team = Team(competition_id=competition_id, name=name)
    db.add(team)
    db.flush()
    return team


def ensure_roster_entries(db, competition_id: int, team: Team) -> None:
    players = db.execute(
        select(Player).where(Player.team_id == team.id)
    ).scalars().all()
    for player in players:
        existing = db.execute(
            select(Roster).where(
                Roster.competition_id == competition_id,
                Roster.team_id == team.id,
                Roster.player_id == player.id,
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(
                Roster(
                    competition_id=competition_id,
                    team_id=team.id,
                    player_id=player.id,
                )
            )


def main() -> None:
    team_names = [
        "Vitória",
        "Atlético-MG",
        "Botafogo",
        "Flamengo",
        "Palmeiras",
        "São Paulo",
        "Corinthians",
        "Santos",
        "Grêmio",
        "Internacional",
        "Fluminense",
        "Vasco da Gama",
        "Athletico-PR",
        "Cruzeiro",
        "Bahia",
        "Ceará",
        "Red Bull Bragantino",
        "Coritiba",
        "Remo",
        "Chapecoense",
        "Mirassol",
    ]

    with SessionLocal() as db:
        competition = get_or_create_competition(db)

        for name in team_names:
            team = get_or_create_team(db, competition.id, name)
            ensure_roster_entries(db, competition.id, team)

        db.commit()


if __name__ == "__main__":
    main()
