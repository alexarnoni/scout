"""
Busca logos dos times na ESPN e salva no banco via team.logo_url.

Uso:
    python -m scripts.fetch_logos
"""
from __future__ import annotations

import time
import sys
import os

import requests
from sqlalchemy import select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.db import SessionLocal
from app.models.team import Team

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1/scoreboard"

DATES = [
    "20260128",
    "20260129",
    "20260204",
    "20260211",
    "20260225",
]


def fetch_logo_map() -> dict[str, str]:
    """Retorna {team_name: logo_url} varrendo os scoreboards das datas configuradas."""
    logo_map: dict[str, str] = {}

    for date in DATES:
        try:
            resp = requests.get(ESPN_SCOREBOARD_URL, params={"dates": date}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"[WARN] Falha ao buscar scoreboard {date}: {exc}")
            time.sleep(1)
            continue

        for event in data.get("events", []):
            for competitor in event.get("competitions", [{}])[0].get("competitors", []):
                team = competitor.get("team", {})
                name = team.get("displayName") or team.get("name")
                logo = team.get("logo")
                if name and logo and name not in logo_map:
                    logo_map[name] = logo

        print(f"[INFO] {date}: {len(logo_map)} times mapeados até agora")
        time.sleep(1)

    return logo_map


def main() -> None:
    logo_map = fetch_logo_map()
    print(f"[INFO] Total de logos encontrados na ESPN: {len(logo_map)}")

    db = SessionLocal()
    try:
        teams = db.execute(select(Team)).scalars().all()
        updated = 0
        not_found: list[str] = []

        for team in teams:
            logo_url = logo_map.get(team.name)
            if logo_url:
                team.logo_url = logo_url
                updated += 1
            else:
                not_found.append(team.name)

        db.commit()
    finally:
        db.close()

    for name in not_found:
        print(f"[WARN] Logo não encontrado: {name}")

    print(f"\nResumo: updated={updated} not_found={len(not_found)}")


if __name__ == "__main__":
    main()
