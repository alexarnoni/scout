# Scout

Scout de futebol para o Brasileirão Série A 2026.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2.0
- **Banco:** PostgreSQL (Docker)
- **Fonte de dados:** ESPN API informal
- **Scheduler:** APScheduler

## Setup

### 1. Subir o banco

```bash
cd infra
docker-compose up -d
```

### 2. Instalar dependências

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

Copiar `.env.example` para `.env` e preencher `DATABASE_URL`.

### 4. Rodar migrations

```bash
cd backend
alembic upgrade head
```

### 5. Seed inicial

```bash
python -m scripts.seed_layer0
```

Cria a competição "Brasileirao 2026" e os 21 times no banco.

## Sincronização

### Backfill histórico

```bash
python -m scripts.backfill \
  --competition-id 1 \
  --date-from 2026-01-28 \
  --date-to 2026-03-14 \
  --include-players
```

### Sync de uma data

```bash
python -m scripts.sync_date \
  --competition-id 1 \
  --date 2026-03-14 \
  --include-players
```

### Scheduler diário

Sincroniza automaticamente o dia anterior às 00:30 (BRT):

```bash
python -m scripts.scheduler
```

Variáveis de ambiente do scheduler:

| Variável | Default | Descrição |
|---|---|---|
| `SCOUT_COMPETITION_ID` | `1` | ID da competição no banco |

## Estrutura

```
backend/
  app/
    models/          # SQLAlchemy models
    providers/       # ESPN provider
    services/        # Lógica de persistência compartilhada
    routers/         # Endpoints FastAPI
  scripts/
    seed_layer0.py   # Seed inicial
    sync_date.py     # Sync de uma data
    backfill.py      # Backfill de intervalo de datas
    scheduler.py     # Scheduler diário
  alembic/           # Migrations
```
