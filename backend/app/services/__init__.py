"""Service layer for the Scout backend."""

from app.services.persistence import (
    extract_xg,
    parse_player_stats,
    upsert_match,
    upsert_player_stats,
    upsert_team_stats,
)

__all__ = [
    "extract_xg",
    "parse_player_stats",
    "upsert_match",
    "upsert_player_stats",
    "upsert_team_stats",
]
