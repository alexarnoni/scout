# Scout Backend

## Run API

```bash
uvicorn app.main:app --reload --port 8000
```

## Seed camada 0

```bash
python -m scripts.seed_layer0
```

## Migrations (match stats)

```bash
alembic revision --autogenerate -m "add match stats"
alembic upgrade head
```

## Migrations (camada 2 FPF)

```bash
alembic revision --autogenerate -m "camada 2 fpf fields"
alembic upgrade head
```

## Migrations (camada 3 sync keys)

```bash
alembic revision --autogenerate -m "camada 3 sync keys"
alembic upgrade head
```

## Migrations (camada 3.2 player stats)

```bash
alembic revision --autogenerate -m "camada 3.2 player stats"
alembic upgrade head
```

## Sync round (camada 3)

```bash
python -m scripts.sync_round --competition-id 1 --round 1 --source sofascore
```

## Sync round com players (camada 3.2)

```bash
python -m scripts.sync_round --competition-id 1 --round 1 --source sofascore --include-players
```

## Test xG import (manual)

```bash
python -m scripts.sync_round --competition-id 1 --round 1 --source sofascore --verbose; psql -h localhost -p 5433 -U scout -d scout -c "select team_id, xg from team_match_stats where match_id=1;"
```

## Camada 3.1 (team analytics)

Uses existing matches + team_match_stats to compute averages, trend, radar, and time series.

## Import camada 2 (FPF)

```bash
python -m scripts.import_fpf_layer2 data/fpf/paulistao_layer2_seed.json
```

## Import match JSON

```bash
python -m scripts.import_match_json data/match_001.json
```

## Test endpoints

```bash
curl http://localhost:8000/health
curl http://localhost:8000/competitions
curl http://localhost:8000/competitions/1/teams
curl http://localhost:8000/teams/1
curl http://localhost:8000/teams/1/roster
curl http://localhost:8000/teams/1/staff
curl http://localhost:8000/players/1
curl "http://localhost:8000/matches?competition_id=1"
curl http://localhost:8000/matches/1
curl http://localhost:8000/matches/1/stats
curl http://localhost:8000/teams/1/matches
curl http://localhost:8000/teams/1/squad
curl "http://localhost:8000/matches?competition_id=1"
curl "http://localhost:8000/teams/1/radar?window=season"
curl "http://localhost:8000/teams/1/radar?window=last5"
curl "http://localhost:8000/teams/1/analytics/summary?competition_id=1&window=5"
curl "http://localhost:8000/teams/1/analytics/radar?competition_id=1&window=5"
curl "http://localhost:8000/teams/1/analytics/radar?competition_id=1&window=5&min_matches=1&min_teams=2"
curl "http://localhost:8000/teams/1/analytics/timeseries?competition_id=1"
curl "http://localhost:8000/players/1/analytics/summary?competition_id=1&window=5"
curl "http://localhost:8000/players/1/analytics/radar?competition_id=1&window=5"
```
