from __future__ import annotations

import datetime
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/bra.1"
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF = 5   # seconds between retry attempts
_SUMMARY_DELAY = 2   # seconds between summary calls — ESPN doesn't rate-limit but courtesy

_STATUS_MAP = {
    "STATUS_FINAL": "finished",
    "STATUS_FULL_TIME": "finished",      # ESPN usa esse pro futebol brasileiro
    "STATUS_SCHEDULED": "scheduled",
    "STATUS_IN_PROGRESS": "in_progress",
}

# ESPN usa nomes inconsistentes para o mesmo time entre datas — normalizar antes
# de qualquer lookup no banco.
_TEAM_NAME_ALIASES: dict[str, str] = {
    "Athletico Paranaense": "Athletico-PR",
}


class ESPNProvider:
    """Provider for ESPN's unofficial soccer API.

    Does NOT inherit BaseProvider: ESPN's API is date-based, not round-based,
    so implementing fetch_round would require an artificial mapping that doesn't
    exist reliably. This class exposes its own interface instead.
    """

    name = "espn"

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def fetch_matches_by_date(self, date: datetime.date) -> list[dict]:
        """Fetch all Paulistão matches on a given date, with stats.

        Flow: one scoreboard call → one summary call per game (with delay).
        Returns list in the format sync_round.py already expects.
        """
        scoreboard = self._get(
            f"{_BASE}/scoreboard",
            params={"dates": date.strftime("%Y%m%d")},
        )
        events = scoreboard.get("events", [])
        logger.info("Scoreboard for %s: %d event(s) found", date, len(events))

        results = []
        for i, event in enumerate(events):
            game_id = event["id"]

            # Delay before every call except the first — keeps 2s gap between requests
            if i > 0:
                time.sleep(_SUMMARY_DELAY)

            try:
                summary = self._get(f"{_BASE}/summary", params={"event": game_id})
            except requests.RequestException as exc:
                # Degrade gracefully: return match metadata without stats rather
                # than aborting the entire date batch
                logger.warning("Could not fetch summary for game %s: %s", game_id, exc)
                summary = {}

            results.append(self._build_match(event, summary))

        return results

    def fetch_match_summary(self, espn_game_id: str) -> dict:
        """Return the raw ESPN summary JSON for a game. Intended for inspection/debug."""
        return self._get(f"{_BASE}/summary", params={"event": espn_game_id})

    # -------------------------------------------------------------------------
    # HTTP layer
    # -------------------------------------------------------------------------

    def _get(self, url: str, params: dict | None = None) -> dict:
        """GET with retry/backoff. Raises on the final failed attempt."""
        last_exc: Exception = RuntimeError("Retry loop exhausted")
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except (requests.HTTPError, requests.RequestException) as exc:
                last_exc = exc
                if attempt == _RETRY_ATTEMPTS:
                    logger.error(
                        "Failed after %d attempts — %s: %s", attempt, url, exc
                    )
                    break
                logger.warning(
                    "Attempt %d/%d failed for %s: %s. Retrying in %ds…",
                    attempt, _RETRY_ATTEMPTS, url, exc, _RETRY_BACKOFF,
                )
                time.sleep(_RETRY_BACKOFF)
        raise last_exc

    # -------------------------------------------------------------------------
    # Match assembly
    # -------------------------------------------------------------------------

    def _build_match(self, event: dict, summary: dict) -> dict:
        """Combine scoreboard event + summary into the sync_round format."""
        competition = event.get("competitions", [{}])[0]
        competitors = competition.get("competitors", [])

        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})

        status_name = event.get("status", {}).get("type", {}).get("name", "")
        status = _STATUS_MAP.get(status_name, "scheduled")

        # ESPN exposes round as "week" inside the season object
        round_number: int | None = event.get("week", {}).get("number")

        # Only parse scores for finished matches — in-progress scores can be
        # misleading depending on when the scoreboard was fetched
        score_home: int | None = None
        score_away: int | None = None
        if status == "finished":
            score_home = _parse_int(home.get("score"))
            score_away = _parse_int(away.get("score"))

        raw_home = home.get("team", {}).get("displayName", "")
        raw_away = away.get("team", {}).get("displayName", "")

        return {
            "external_id": event["id"],
            "date": event.get("date", ""),
            "home_team": _TEAM_NAME_ALIASES.get(raw_home, raw_home),
            "away_team": _TEAM_NAME_ALIASES.get(raw_away, raw_away),
            "score_home": score_home,
            "score_away": score_away,
            "status": status,
            "round": round_number,
            "team_stats": self._parse_team_stats(summary),
            "player_stats": self._parse_player_stats(summary),
        }

    # -------------------------------------------------------------------------
    # Team stats
    # -------------------------------------------------------------------------

    def _parse_team_stats(self, summary: dict) -> list[dict]:
        """Extract team-level stats from boxscore.teams.

        ESPN represents team stats as a flat list of {name, displayValue} pairs,
        so we build a lookup dict first.
        """
        teams = summary.get("boxscore", {}).get("teams", [])
        result = []

        for team_entry in teams:
            # Build name→value lookup from the flat statistics list
            stats = {
                s["name"]: s.get("displayValue")
                for s in team_entry.get("statistics", [])
            }

            goals = _parse_int(stats.get("totalGoals"))

            raw_name = team_entry.get("team", {}).get("displayName", "")
            result.append({
                "team_name": _TEAM_NAME_ALIASES.get(raw_name, raw_name),
                "is_home": team_entry.get("homeAway") == "home",
                "goals": goals if goals is not None else 0,
                "possession": _parse_float(stats.get("possessionPct")),
                "shots": _parse_int(stats.get("totalShots")),
                "shots_on_target": _parse_int(stats.get("shotsOnTarget")),
                "corners": _parse_int(stats.get("corners")),
                "fouls": _parse_int(stats.get("foulsCommitted")),
                "yellow_cards": _parse_int(stats.get("yellowCards")),
                "red_cards": _parse_int(stats.get("redCards")),
            })

        return result

    # -------------------------------------------------------------------------
    # Player stats
    # -------------------------------------------------------------------------

    def _parse_player_stats(self, summary: dict) -> list[dict]:
        """Extract per-player stats from summary["rosters"].

        Soccer uses rosters[], not boxscore.players — confirmed by live test.
        Each roster entry has "roster" (list of athletes) and "homeAway" for
        determining which team the athletes belong to.
        """
        result = []

        for team_entry in summary.get("rosters", []):
            raw_name = team_entry.get("team", {}).get("displayName", "")
            team_name = _TEAM_NAME_ALIASES.get(raw_name, raw_name)

            for athlete_entry in team_entry.get("roster", []):
                result.append(self._build_player_entry(athlete_entry, team_name))

        return result

    def _build_player_entry(
        self,
        entry: dict,
        team_name: str,
    ) -> dict:
        """Map a single ESPN roster athlete entry to the expected player_stats structure."""
        athlete = entry.get("athlete", {})

        # stats is a list of {name, value} objects — build lookup from it.
        # Using value (float) instead of displayValue (string) for numeric reliability.
        stats_lookup: dict[str, Any] = {
            s["name"]: s.get("value") for s in entry.get("stats", [])
        }

        starter: bool = entry.get("starter", False)
        subbed_in: bool = entry.get("subbedIn", False)
        subbed_out: bool = entry.get("subbedOut", False)

        return {
            "player_name": athlete.get("displayName", ""),
            "player_external_id": str(athlete.get("id", "")),
            "team_name": team_name,
            "is_starter": starter,
            "subbed_in": subbed_in,
            "subbed_out": subbed_out,
            "position": entry.get("position", {}).get("displayName"),
            "jersey": entry.get("jersey"),
            "stats": {
                "goals": _parse_int(stats_lookup.get("totalGoals")) or 0,
                "assists": _parse_int(stats_lookup.get("goalAssists")) or 0,
                "shots": _parse_int(stats_lookup.get("totalShots")) or 0,
                "shots_on_target": _parse_int(stats_lookup.get("shotsOnTarget")) or 0,
                "fouls_committed": _parse_int(stats_lookup.get("foulsCommitted")) or 0,
                "yellow_cards": _parse_int(stats_lookup.get("yellowCards")) or 0,
                "red_cards": _parse_int(stats_lookup.get("redCards")) or 0,
                # saves is keeper-specific — None is semantically different from 0
                "saves": _parse_int(stats_lookup.get("saves")),
                "minutes_played": self._calc_minutes(entry, starter, subbed_out, subbed_in),
            },
        }

    def _calc_minutes(
        self,
        entry: dict,
        starter: bool,
        subbed_out: bool,
        subbed_in: bool,
    ) -> int | None:
        """Calculate minutes played.

        Rules (from spec):
        - Starter, not subbed out → 90
        - Subbed out (starter) or subbed in → find the substitution event in plays[]
          and read clock.value (the minute)
        - No play data available → None (caller decides how to handle)
        """
        if starter and not subbed_out:
            return 90

        if subbed_out or subbed_in:
            for play in entry.get("plays", []):
                play_type = play.get("type", {}).get("text", "").lower()
                if "sub" in play_type:  # covers "Substitution", "Sub", etc.
                    minute = play.get("clock", {}).get("value")
                    if minute is not None:
                        return int(minute)

        return None


# =============================================================================
# Module-level helpers — not part of the provider interface
# =============================================================================

def _parse_int(value: Any) -> int | None:
    """String/numeric → int. ESPN occasionally returns floats like '2.0'."""
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _parse_float(value: Any) -> float | None:
    """String/numeric → float. Returns None on any parse failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
