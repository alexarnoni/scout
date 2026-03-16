from pydantic import BaseModel


class PlayerScoutCard(BaseModel):
    player_id: int
    player_name: str
    team_name: str
    position: str
    total_minutes: int
    matches_played: int
    score: float
    rank: int
    metrics: dict[str, float | None]


class ScoutRanking(BaseModel):
    player_id: int
    player_name: str
    team_name: str
    position: str
    total_minutes: int
    matches_played: int
    score: float
    metrics: dict[str, float | None]
