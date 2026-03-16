from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class CompetitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    season: str | None = None


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    name: str
    external_ids: dict[str, str] | None = None
    logo_url: str | None = None
    city: str | None = None


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    name: str
    position: str | None = None
    shirt_number: int | None = None
    external_ids: dict[str, str] | None = None
    birth_date: date | None = None
    nationality: str | None = None
    photo_url: str | None = None
    height_cm: int | None = None
    preferred_foot: str | None = None


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    name: str
    role: str | None = None
    external_ids: dict[str, str] | None = None
    photo_url: str | None = None


class RosterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    team_id: int
    player: PlayerOut


class TeamMatchStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    team_id: int
    is_home: bool
    goals: int
    possession: float | None = None
    shots: int | None = None
    shots_on_target: int | None = None
    passes: int | None = None
    pass_accuracy: float | None = None
    corners: int | None = None
    fouls: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    xg: float | None = None


class PlayerMatchStatsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    player_id: int
    team_id: int
    minutes: int | None = None
    goals: int | None = None
    assists: int | None = None
    shots: int | None = None
    shots_on_target: int | None = None
    key_passes: int | None = None
    passes: int | None = None
    pass_accuracy: float | None = None
    tackles: int | None = None
    interceptions: int | None = None
    duels_won: int | None = None
    fouls_committed: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    rating: float | None = None
    xg: float | None = None
    xa: float | None = None


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    round_number: int | None = None
    match_date_time: datetime
    status: str
    score_home: int | None = None
    score_away: int | None = None
    home_team: TeamOut
    away_team: TeamOut


class TeamSquadOut(BaseModel):
    team: TeamOut
    players: list[PlayerOut]
    staff: list[StaffOut]


class PlayerDetailOut(PlayerOut):
    team: TeamOut
