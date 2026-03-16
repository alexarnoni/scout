# Backend

FastAPI + SQLAlchemy 2.0.

## Estrutura

```
app/
  core/config.py       # DATABASE_URL e settings
  models/              # SQLAlchemy ORM models
  providers/espn.py    # ESPN API provider (date-based)
  services/persistence.py  # Funções de upsert compartilhadas
  routers/             # Endpoints FastAPI
scripts/
  seed_layer0.py       # Cria competição + times
  sync_date.py         # Sync de uma data via ESPN
  backfill.py          # Loop de datas para backfill
  scheduler.py         # Roda sync_date todo dia às 00:30 BRT
alembic/               # Migrations Alembic
```

## Fonte de dados

ESPN API informal — sem autenticação, sem rate limit oficial.

Endpoints usados:
- `GET /apis/site/v2/sports/soccer/bra.1/scoreboard?dates=YYYYMMDD`
- `GET /apis/site/v2/sports/soccer/bra.1/summary?event={id}`
