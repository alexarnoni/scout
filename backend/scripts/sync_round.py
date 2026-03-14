from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ROOT_ENV)

from app.core.config import DATABASE_URL
from app.models import Match, Player, PlayerMatchStats, Team, TeamMatchStats
from app.providers import SofaScoreProvider

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    if "T" not in value and " " not in value:
        value = f"{value}T00:00:00"
    return datetime.fromisoformat(value)


def extract_xg(stats_json) -> float | None:
    def to_float(value) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().lower().replace("%", "").replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    direct_keys = [
        "xg",
        "xG",
        "xGoals",
        "expectedGoals",
        "expected_goals",
        "expectedGoalsFor",
    ]

    def scan(obj) -> float | None:
        if isinstance(obj, dict):
            for key in direct_keys:
                if key in obj:
                    direct_val = to_float(obj.get(key))
                    if direct_val is not None:
                        return direct_val

            name = obj.get("name") or obj.get("label") or obj.get("type") or obj.get("title")
            if isinstance(name, str):
                label = name.lower()
                if "xg" in label or "expected goals" in label or "expected goal" in label:
                    val = (
                        obj.get("value")
                        or obj.get("stat")
                        or obj.get("valueText")
                        or obj.get("valueStr")
                    )
                    named_val = to_float(val)
                    if named_val is not None:
                        return named_val

            for value in obj.values():
                found = scan(value)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = scan(item)
                if found is not None:
                    return found
        return None

    return scan(stats_json)


def load_provider(name: str):
    if name == "sofascore":
        return SofaScoreProvider()
    raise ValueError(f"Unsupported source: {name}")


def upsert_match(db, competition_id: int, source: str, payload: dict) -> tuple[Match, bool]:
    external_id = payload.get("external_id")
    match = None
    if external_id:
        match = db.execute(
            select(Match).where(
                Match.external_source == source,
                Match.external_id == external_id,
            )
        ).scalar_one_or_none()

    match_date_time = parse_datetime(payload["date"])
    home_team = db.execute(
        select(Team).where(
            Team.competition_id == competition_id,
            Team.name == payload["home_team"],
        )
    ).scalar_one_or_none()
    away_team = db.execute(
        select(Team).where(
            Team.competition_id == competition_id,
            Team.name == payload["away_team"],
        )
    ).scalar_one_or_none()

    if not home_team or not away_team:
        raise ValueError("Home or away team not found for match payload")

    if not match:
        match = db.execute(
            select(Match).where(
                Match.competition_id == competition_id,
                Match.match_date_time == match_date_time,
                Match.home_team_id == home_team.id,
                Match.away_team_id == away_team.id,
            )
        ).scalar_one_or_none()

    created = False
    if not match:
        match = Match(
            competition_id=competition_id,
            round_number=payload["round"],
            match_date_time=match_date_time,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=payload.get("status", "scheduled"),
            score_home=payload.get("score_home"),
            score_away=payload.get("score_away"),
            external_source=source,
            external_id=external_id,
            external_ids={source: external_id} if external_id else None,
        )
        db.add(match)
        db.flush()
        created = True
    else:
        match.round_number = payload["round"]
        match.status = payload.get("status", match.status)
        match.score_home = payload.get("score_home")
        match.score_away = payload.get("score_away")
        match.external_source = source
        match.external_id = external_id
        if external_id:
            ids = match.external_ids or {}
            ids[source] = external_id
            match.external_ids = ids

    return match, created


def upsert_team_stats(db, match: Match, payload: dict) -> bool:
    team = db.execute(
        select(Team).where(
            Team.id == payload["team_id"],
        )
    ).scalar_one_or_none()
    if not team:
        raise ValueError("Team not found for stats payload")

    stats = db.execute(
        select(TeamMatchStats).where(
            TeamMatchStats.match_id == match.id,
            TeamMatchStats.team_id == team.id,
        )
    ).scalar_one_or_none()

    fields = {
        "match_id": match.id,
        "team_id": team.id,
        "is_home": payload["is_home"],
        "goals": payload.get("goals", 0),
        "possession": payload.get("possession"),
        "shots": payload.get("shots"),
        "shots_on_target": payload.get("shots_on_target"),
        "passes": payload.get("passes"),
        "pass_accuracy": payload.get("pass_accuracy"),
        "corners": payload.get("corners"),
        "fouls": payload.get("fouls"),
        "yellow_cards": payload.get("yellow_cards"),
        "red_cards": payload.get("red_cards"),
        "xg": payload.get("xg"),
    }

    created = False
    if not stats:
        stats = TeamMatchStats(**fields)
        db.add(stats)
        created = True
    else:
        for key, value in fields.items():
            setattr(stats, key, value)

    return created


def upsert_player_stats(db, match: Match, payload: dict) -> bool:
    player = payload.get("player")
    if not player:
        raise ValueError("Player not resolved for stats payload")

    stats = db.execute(
        select(PlayerMatchStats).where(
            PlayerMatchStats.match_id == match.id,
            PlayerMatchStats.player_id == player.id,
        )
    ).scalar_one_or_none()

    fields = {
        "match_id": match.id,
        "player_id": player.id,
        "team_id": payload["team_id"],
        "minutes": payload.get("minutes_played"),
        "goals": payload.get("goals"),
        "assists": payload.get("assists"),
        "shots": payload.get("shots"),
        "shots_on_target": payload.get("shots_on_target"),
        "key_passes": payload.get("key_passes"),
        "passes": payload.get("passes"),
        "pass_accuracy": payload.get("pass_accuracy"),
        "tackles": payload.get("tackles"),
        "interceptions": payload.get("interceptions"),
        "duels_won": payload.get("duels_won"),
        "fouls_committed": payload.get("fouls_committed"),
        "yellow_cards": payload.get("yellow_cards"),
        "red_cards": payload.get("red_cards"),
        "rating": payload.get("rating"),
        "xg": payload.get("xg"),
        "xa": payload.get("xa"),
    }

    created = False
    if not stats:
        stats = PlayerMatchStats(**fields)
        db.add(stats)
        created = True
    else:
        for key, value in fields.items():
            setattr(stats, key, value)

    return created


def _to_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_player_stats(stats_payload: dict) -> dict:
    return {
        "minutes_played": _to_int(stats_payload.get("minutes_played")),
        "goals": _to_int(stats_payload.get("goals")),
        "assists": _to_int(stats_payload.get("assists")),
        "shots": _to_int(stats_payload.get("shots")),
        "shots_on_target": _to_int(stats_payload.get("shots_on_target")),
        "key_passes": _to_int(stats_payload.get("key_passes")),
        "passes": _to_int(stats_payload.get("passes")),
        "pass_accuracy": _to_float(stats_payload.get("pass_accuracy")),
        "tackles": _to_int(stats_payload.get("tackles")),
        "interceptions": _to_int(stats_payload.get("interceptions")),
        "duels_won": _to_int(stats_payload.get("duels_won")),
        "fouls_committed": _to_int(stats_payload.get("fouls_committed")),
        "yellow_cards": _to_int(stats_payload.get("yellow_cards")),
        "red_cards": _to_int(stats_payload.get("red_cards")),
        "rating": _to_float(stats_payload.get("rating")),
        "xg": _to_float(stats_payload.get("xg")),
        "xa": _to_float(stats_payload.get("xa")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition-id", type=int, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--source", type=str, default="sofascore")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--include-players", nargs="?", const="true", default="false")
    args = parser.parse_args()

    include_players = str(args.include_players).lower() in {"1", "true", "yes", "y"}

    provider = load_provider(args.source)
    payload = provider.fetch_round(args.competition_id, args.round)

    inserted_matches = 0
    updated_matches = 0
    inserted_stats = 0
    updated_stats = 0
    skipped_stats = 0
    inserted_player_stats = 0
    updated_player_stats = 0

    with SessionLocal() as db:
        for match_payload in payload.get("matches", []):
            match_payload["round"] = args.round
            match, created = upsert_match(
                db, args.competition_id, args.source, match_payload
            )
            if created:
                inserted_matches += 1
            else:
                updated_matches += 1

            if match.status != "finished":
                skipped_stats += 1
                continue

            for stats_payload in match_payload.get("team_stats", []):
                team = db.execute(
                    select(Team).where(
                        Team.competition_id == args.competition_id,
                        Team.name == stats_payload["team_name"],
                    )
                ).scalar_one_or_none()
                if not team:
                    raise ValueError(f"Team not found: {stats_payload['team_name']}")
                stats_payload["team_id"] = team.id
                stats_payload["xg"] = extract_xg(stats_payload)
                if args.verbose:
                    if stats_payload["xg"] is not None:
                        print(
                            "xg found:",
                            f"match_id={match.id}",
                            f"team_id={team.id}",
                            f"xg={stats_payload['xg']}",
                        )
                    else:
                        print(
                            "xg missing:",
                            f"match_id={match.id}",
                            f"team_id={team.id}",
                        )

                stats_created = upsert_team_stats(db, match, stats_payload)
                if stats_created:
                    inserted_stats += 1
                else:
                    updated_stats += 1

            if include_players:
                for player_payload in match_payload.get("player_stats", []):
                    team = db.execute(
                        select(Team).where(
                            Team.competition_id == args.competition_id,
                            Team.name == player_payload["team_name"],
                        )
                    ).scalar_one_or_none()
                    if not team:
                        raise ValueError(
                            f"Team not found: {player_payload['team_name']}"
                        )

                    player = None
                    external_id = player_payload.get("player_external_id")
                    if external_id:
                        player = db.execute(
                            select(Player).where(
                                Player.external_ids["sofascore"].as_string()
                                == external_id
                            )
                        ).scalar_one_or_none()

                    if not player:
                        player = db.execute(
                            select(Player).where(
                                Player.team_id == team.id,
                                Player.name == player_payload["player_name"],
                            )
                        ).scalar_one_or_none()

                    if not player:
                        if args.verbose:
                            print(
                                "player missing:",
                                f"match_id={match.id}",
                                f"team_id={team.id}",
                                f"name={player_payload['player_name']}",
                            )
                        continue

                    parsed_stats = parse_player_stats(player_payload.get("stats", {}))
                    parsed_stats["team_id"] = team.id
                    parsed_stats["player"] = player

                    created_player = upsert_player_stats(db, match, parsed_stats)
                    if created_player:
                        inserted_player_stats += 1
                    else:
                        updated_player_stats += 1

        if args.dry_run:
            db.rollback()
        else:
            db.commit()

    print(
        "Summary: "
        f"matches_inserted={inserted_matches} "
        f"matches_updated={updated_matches} "
        f"stats_inserted={inserted_stats} "
        f"stats_updated={updated_stats} "
        f"stats_skipped={skipped_stats} "
        f"player_stats_inserted={inserted_player_stats} "
        f"player_stats_updated={updated_player_stats}"
    )


if __name__ == "__main__":
    main()
