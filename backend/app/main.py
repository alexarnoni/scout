from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.router import api_router
from app.core.db import get_db
from app.models import (
    Competition,
    Match,
    Player,
    Roster,
    Staff,
    Team,
    TeamMatchStats,
)
from app.schemas import (
    CompetitionOut,
    PlayerOut,
    MatchOut,
    PlayerDetailOut,
    RosterOut,
    StaffOut,
    TeamSquadOut,
    TeamMatchStatsOut,
    TeamOut,
)
from app.schemas.analytics import (
    TeamAnalyticsSummary,
    TeamRadar,
    TeamTimeSeriesPoint,
)
from app.schemas.player_analytics import (
    PlayerAnalyticsSummary,
    PlayerRadar,
    PlayerTimeSeriesPoint,
)
from app.services.team_analytics import (
    get_last_matches,
    get_team_averages,
    get_team_radar as build_team_radar,
    get_team_timeseries,
    get_team_trend,
)
from app.services.player_analytics import (
    get_last_matches as get_player_last_matches,
    get_player_averages,
    get_player_radar,
    get_player_timeseries,
)

app = FastAPI(title="Scout API", version="0.1.0")
app.include_router(api_router)


def get_competition_or_404(db: Session, competition_id: int) -> Competition:
    competition = db.execute(
        select(Competition).where(Competition.id == competition_id)
    ).scalar_one_or_none()
    if not competition:
        raise HTTPException(status_code=404, detail="Competition not found")
    return competition


def get_team_or_404(db: Session, team_id: int) -> Team:
    team = db.execute(select(Team).where(Team.id == team_id)).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def get_team_in_competition_or_404(
    db: Session, team_id: int, competition_id: int
) -> Team:
    team = db.execute(
        select(Team).where(
            Team.id == team_id,
            Team.competition_id == competition_id,
        )
    ).scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in competition")
    return team


def get_player_or_404(db: Session, player_id: int) -> Player:
    player = db.execute(
        select(Player).where(Player.id == player_id)
    ).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


def get_player_with_team_or_404(db: Session, player_id: int) -> Player:
    player = db.execute(
        select(Player)
        .where(Player.id == player_id)
        .options(joinedload(Player.team))
    ).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


def get_player_in_competition_or_404(
    db: Session, player_id: int, competition_id: int
) -> Player:
    player = db.execute(
        select(Player)
        .join(Team, Team.id == Player.team_id)
        .where(Player.id == player_id, Team.competition_id == competition_id)
    ).scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found in competition")
    return player


def get_match_or_404(db: Session, match_id: int) -> Match:
    match = db.execute(
        select(Match)
        .where(Match.id == match_id)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
    ).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@app.get("/competitions", response_model=list[CompetitionOut])
def list_competitions(db: Session = Depends(get_db)) -> list[Competition]:
    competitions = db.execute(
        select(Competition).order_by(Competition.name)
    ).scalars().all()
    return competitions


@app.get("/competitions/{competition_id}/teams", response_model=list[TeamOut])
def list_competition_teams(
    competition_id: int, db: Session = Depends(get_db)
) -> list[Team]:
    get_competition_or_404(db, competition_id)
    teams = db.execute(
        select(Team)
        .where(Team.competition_id == competition_id)
        .order_by(Team.name)
    ).scalars().all()
    return teams


@app.get("/teams/{team_id}", response_model=TeamOut)
def get_team_detail(team_id: int, db: Session = Depends(get_db)) -> Team:
    return get_team_or_404(db, team_id)


@app.get("/teams/{team_id}/roster", response_model=list[RosterOut])
def get_team_roster(
    team_id: int, db: Session = Depends(get_db)
) -> list[Roster]:
    get_team_or_404(db, team_id)
    rosters = db.execute(
        select(Roster)
        .where(Roster.team_id == team_id)
        .options(joinedload(Roster.player))
    ).scalars().all()
    return rosters


@app.get("/teams/{team_id}/staff", response_model=list[StaffOut])
def get_team_staff(team_id: int, db: Session = Depends(get_db)) -> list[Staff]:
    get_team_or_404(db, team_id)
    staff_members = db.execute(
        select(Staff).where(Staff.team_id == team_id).order_by(Staff.name)
    ).scalars().all()
    return staff_members


@app.get("/players/{player_id}", response_model=PlayerDetailOut)
def get_player_detail(player_id: int, db: Session = Depends(get_db)) -> Player:
    return get_player_with_team_or_404(db, player_id)


@app.get(
    "/players/{player_id}/analytics/summary", response_model=PlayerAnalyticsSummary
)
def get_player_analytics_summary(
    player_id: int,
    competition_id: int,
    window: int = 5,
    db: Session = Depends(get_db),
) -> dict:
    get_player_in_competition_or_404(db, player_id, competition_id)
    last_matches = get_player_last_matches(db, player_id, competition_id, window)
    averages = get_player_averages(db, player_id, competition_id, window)
    return {
        "player_id": player_id,
        "competition_id": competition_id,
        "window": window,
        "averages": averages,
        "last_matches": last_matches,
    }


@app.get("/players/{player_id}/analytics/radar", response_model=PlayerRadar)
def get_player_analytics_radar(
    player_id: int,
    competition_id: int,
    window: int = 5,
    min_matches: int = 3,
    min_players: int = 30,
    db: Session = Depends(get_db),
) -> dict:
    get_player_in_competition_or_404(db, player_id, competition_id)
    radar = get_player_radar(
        db, player_id, competition_id, window, min_matches, min_players
    )
    return {
        "player_id": player_id,
        "competition_id": competition_id,
        "window": window,
        "min_matches": min_matches,
        "min_players": min_players,
        "eligible_players": radar["eligible_players"],
        "metrics": radar["metrics"],
        "note": radar["note"],
    }


@app.get(
    "/players/{player_id}/analytics/timeseries",
    response_model=list[PlayerTimeSeriesPoint],
)
def get_player_analytics_timeseries(
    player_id: int,
    competition_id: int,
    db: Session = Depends(get_db),
) -> list[dict]:
    get_player_in_competition_or_404(db, player_id, competition_id)
    return get_player_timeseries(db, player_id, competition_id)


@app.get("/matches", response_model=list[MatchOut])
def list_matches(
    competition_id: int, db: Session = Depends(get_db)
) -> list[Match]:
    matches = db.execute(
        select(Match)
        .where(Match.competition_id == competition_id)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .order_by(Match.match_date_time)
    ).scalars().all()
    return matches


@app.get("/matches/{match_id}", response_model=MatchOut)
def get_match_detail(match_id: int, db: Session = Depends(get_db)) -> Match:
    return get_match_or_404(db, match_id)


@app.get("/matches/{match_id}/stats", response_model=list[TeamMatchStatsOut])
def get_match_stats(
    match_id: int, db: Session = Depends(get_db)
) -> list[TeamMatchStats]:
    get_match_or_404(db, match_id)
    stats = db.execute(
        select(TeamMatchStats)
        .where(TeamMatchStats.match_id == match_id)
        .order_by(TeamMatchStats.is_home.desc())
    ).scalars().all()
    return stats


@app.get("/teams/{team_id}/matches", response_model=list[MatchOut])
def get_team_matches(team_id: int, db: Session = Depends(get_db)) -> list[Match]:
    get_team_or_404(db, team_id)
    matches = db.execute(
        select(Match)
        .where(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .order_by(Match.match_date_time.desc())
    ).scalars().all()
    return matches


@app.get("/teams/{team_id}/squad", response_model=TeamSquadOut)
def get_team_squad(team_id: int, db: Session = Depends(get_db)) -> dict:
    team = get_team_or_404(db, team_id)
    players = db.execute(
        select(Player).where(Player.team_id == team_id).order_by(Player.name)
    ).scalars().all()
    staff_members = db.execute(
        select(Staff).where(Staff.team_id == team_id).order_by(Staff.name)
    ).scalars().all()
    return {"team": team, "players": players, "staff": staff_members}


@app.get("/teams/{team_id}/radar")
def get_team_radar(
    team_id: int, window: str = "season", db: Session = Depends(get_db)
) -> dict:
    get_team_or_404(db, team_id)
    if window not in {"season", "last5"}:
        raise HTTPException(status_code=400, detail="Invalid window")

    query = (
        select(TeamMatchStats, Match.match_date_time)
        .join(Match, Match.id == TeamMatchStats.match_id)
        .where(TeamMatchStats.team_id == team_id)
        .order_by(Match.match_date_time.desc())
    )
    if window == "last5":
        query = query.limit(5)

    rows = db.execute(query).all()
    stats = [row[0] for row in rows]

    def avg(values: list[float | int]) -> float | None:
        return sum(values) / len(values) if values else None

    def normalize(value: float | None, min_val: float, max_val: float) -> float | None:
        if value is None:
            return None
        if max_val <= min_val:
            return None
        scaled = (value - min_val) / (max_val - min_val) * 100
        return max(0.0, min(100.0, scaled))

    metrics_raw = {
        "goals": avg([s.goals for s in stats if s.goals is not None]),
        "shots": avg([s.shots for s in stats if s.shots is not None]),
        "shots_on_target": avg(
            [s.shots_on_target for s in stats if s.shots_on_target is not None]
        ),
        "possession": avg([s.possession for s in stats if s.possession is not None]),
        "pass_accuracy": avg(
            [s.pass_accuracy for s in stats if s.pass_accuracy is not None]
        ),
        "corners": avg([s.corners for s in stats if s.corners is not None]),
        "fouls": avg([s.fouls for s in stats if s.fouls is not None]),
        "xg": avg([s.xg for s in stats if s.xg is not None]),
    }

    ranges = {
        "goals": (0.0, 5.0),
        "shots": (0.0, 30.0),
        "shots_on_target": (0.0, 15.0),
        "possession": (0.0, 100.0),
        "pass_accuracy": (0.0, 100.0),
        "corners": (0.0, 15.0),
        "fouls": (0.0, 30.0),
        "xg": (0.0, 5.0),
    }

    metrics = {
        key: normalize(metrics_raw[key], *ranges[key]) for key in ranges
    }

    return {"team_id": team_id, "window": window, "metrics": metrics}


@app.get("/teams/{team_id}/analytics/summary", response_model=TeamAnalyticsSummary)
def get_team_analytics_summary(
    team_id: int,
    competition_id: int,
    window: int = 5,
    db: Session = Depends(get_db),
) -> dict:
    get_team_in_competition_or_404(db, team_id, competition_id)
    last_matches = get_last_matches(db, team_id, competition_id, window)
    averages = get_team_averages(db, team_id, competition_id, window)
    trend = get_team_trend(db, team_id, competition_id, window)
    return {
        "team_id": team_id,
        "competition_id": competition_id,
        "window": window,
        "averages": averages,
        "trend": trend,
        "last_matches": last_matches,
    }


@app.get("/teams/{team_id}/analytics/radar", response_model=TeamRadar)
def get_team_analytics_radar(
    team_id: int,
    competition_id: int,
    window: int = 5,
    min_matches: int = 3,
    min_teams: int = 6,
    db: Session = Depends(get_db),
) -> dict:
    get_team_in_competition_or_404(db, team_id, competition_id)
    radar = build_team_radar(
        db, team_id, competition_id, window, min_matches, min_teams
    )
    return {
        "team_id": team_id,
        "competition_id": competition_id,
        "window": window,
        "min_matches": min_matches,
        "min_teams": min_teams,
        "eligible_teams": radar["eligible_teams"],
        "metrics": radar["metrics"],
        "note": radar["note"],
    }


@app.get("/teams/{team_id}/analytics/timeseries", response_model=list[TeamTimeSeriesPoint])
def get_team_analytics_timeseries(
    team_id: int,
    competition_id: int,
    db: Session = Depends(get_db),
) -> list[dict]:
    get_team_in_competition_or_404(db, team_id, competition_id)
    return get_team_timeseries(db, team_id, competition_id)
