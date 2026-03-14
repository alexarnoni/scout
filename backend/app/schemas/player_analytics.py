from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlayerMetricAverages(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    minutes_played: float | None = None
    goals: float | None = None
    assists: float | None = None
    shots: float | None = None
    shots_on_target: float | None = None
    key_passes: float | None = None
    passes: float | None = None
    pass_accuracy: float | None = None
    tackles: float | None = None
    interceptions: float | None = None
    duels_won: float | None = None
    fouls_committed: float | None = None
    yellow_cards: float | None = None
    red_cards: float | None = None
    rating: float | None = None
    xg: float | None = None
    xa: float | None = None


class PlayerAnalyticsSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    competition_id: int
    window: int
    averages: PlayerMetricAverages
    last_matches: list[int]


class PlayerRadar(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    competition_id: int
    window: int
    min_matches: int
    min_players: int
    eligible_players: int
    metrics: dict[str, float | None]
    note: str | None = None


class PlayerTimeSeriesPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: int
    round_number: int
    match_date_time: datetime
    minutes_played: int | None
    rating: float | None
    goals: int | None
    assists: int | None
    shots: int | None
    shots_on_target: int | None
    key_passes: int | None
    passes: int | None
    pass_accuracy: float | None
    tackles: int | None
    interceptions: int | None
    duels_won: int | None
    fouls_committed: int | None
    yellow_cards: int | None
    red_cards: int | None
    xg: float | None
    xa: float | None
