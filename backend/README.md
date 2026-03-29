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

## Changelog

### Scout / Ranking (2026-03-29)

**Migração completa do ranking para SportDB em tempo real.**

- Fonte do ranking: banco ESPN → SportDB ao vivo (`/api/flashscore/match/{id}/playerstats`)
- `xg_p90` agora é real — antes sempre retornava zero. Valor vem de `expectedGoals` da SportDB
- `avg_rating` do Flashscore (`fsRating`) adicionado como métrica para todas as posições (ATT, MID, DEF, GK)
- `scout.py` stateless — removida dependência de sessão de banco (`db`) e `competition_id` do endpoint `/scout/ranking`
- Corrigido mapeamento de posições PT→EN (`Atacante`→`FWD`, etc.)
- Corrigido parsing do endpoint `/playerstats`: dados estão em `stats`, não em `players`
- Adicionado `POSITION_KEY_MAP` para converter `positionKey` numérico da SportDB para grupos GKP/DEF/MID/FWD
- `xg_p90` adicionado ao cálculo de métricas por temporada
