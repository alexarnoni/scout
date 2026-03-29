# Backend

FastAPI + SQLAlchemy 2.0.

## Estrutura

```
app/
  core/config.py           # DATABASE_URL e settings
  models/                  # SQLAlchemy ORM models
  providers/espn.py        # ESPN API provider (sync histórico)
  providers/sportdb.py     # SportDB provider (standings, fixtures, lineups)
  providers/sportdb_scout.py  # SportDB scout provider (player stats por partida)
  services/scout.py        # Ranking de jogadores (stateless, sem DB)
  services/persistence.py  # Funções de upsert compartilhadas
scripts/
  seed_layer0.py           # Cria competição + times
  sync_date.py             # Sync de uma data via ESPN
  backfill.py              # Loop de datas para backfill
  scheduler.py             # Roda sync_date todo dia às 00:30 BRT
alembic/                   # Migrations Alembic
```

## Fonte de dados

### ESPN (dados históricos persistidos)
Usada para sync de partidas e stats de time no banco local.

Endpoints:
- `GET /apis/site/v2/sports/soccer/bra.1/scoreboard?dates=YYYYMMDD`
- `GET /apis/site/v2/sports/soccer/bra.1/summary?event={id}`

### SportDB / Flashscore (tempo real)
Usada para standings, fixtures, lineups e ranking de jogadores.
Requer `SPORTDB_API_KEY` no ambiente.

Endpoints principais:
- `GET /api/flashscore/{competition}/{season}/results`
- `GET /api/flashscore/{competition}/{season}/standings`
- `GET /api/flashscore/match/{eventId}/lineups`
- `GET /api/flashscore/match/{eventId}/playerstats`

## Scout / Ranking

O endpoint `/scout/ranking` é **stateless** — não usa banco de dados.
Busca resultados e stats diretamente da SportDB em tempo real.

Métricas por posição:
- **Goleiro**: save_rate, avg_rating, goals_p90_inv, yellow_cards_p90_inv
- **Defensor**: goals_p90, assists_p90, shots_p90, fouls_p90_inv, yellow_cards_p90_inv, avg_rating
- **Meio-campo**: goals_p90, assists_p90, shots_p90, shots_on_target_p90, fouls_p90_inv, yellow_cards_p90_inv, avg_rating
- **Atacante**: goals_p90, assists_p90, shots_p90, shots_on_target_p90, conversion_rate, xg_p90, yellow_cards_p90_inv, avg_rating

Cache em memória: 2h para stats de temporada, 24h para stats por partida.

### Score e penalização por confiança

O score de cada jogador é calculado em duas etapas:

1. **score_raw** — média simples das métricas normalizadas (min-max 0-100 dentro do grupo de posição)
2. **score final** — `score_raw * confidence`, onde `confidence = total_minutes / max_minutes_do_grupo`

Isso penaliza jogadores com poucos minutos (amostra pequena), evitando scores inflados. O jogador com mais minutos no grupo tem `confidence = 1.0` (sem redução). O campo `metrics` retornado por jogador sempre contém os valores pré-penalização.

## Variáveis de ambiente

```
DATABASE_URL=postgresql://...
SPORTDB_API_KEY=...
```
