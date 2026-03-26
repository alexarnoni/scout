import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import DATABASE_URL  # noqa: ensures .env is loaded
from app.core.db import SessionLocal
from app.models.team import Team

API_KEY = os.getenv("SPORTDB_API_KEY")
if not API_KEY:
    raise RuntimeError("SPORTDB_API_KEY não definida no .env")

HEADERS = {"X-API-Key": API_KEY}
BASE = "https://api.sportdb.dev"


def search_team_logo(name: str) -> str | None:
    r = httpx.get(
        f"{BASE}/api/flashscore/search",
        params={"q": name, "type": "team"},
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    for result in results:
        sport = result.get("sport", {}).get("name", "")
        country = result.get("country", {}).get("name", "")
        images = result.get("images", [])
        if sport == "Soccer" and country == "Brazil" and images:
            return images[0]
    return None


def main():
    db = SessionLocal()
    teams = db.query(Team).all()
    for team in teams:
        print(f"Buscando {team.name}...")
        logo = search_team_logo(team.name)
        if logo:
            team.logo_url = logo
            print(f"  ✓ {logo}")
        else:
            print(f"  ✗ não encontrado")
    db.commit()
    db.close()
    print("Pronto!")


if __name__ == "__main__":
    main()
