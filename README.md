# Olheiro — Brasileirão 2026

> Plataforma de analytics e scouting de futebol para o Campeonato Brasileiro Série A 2026.

**Live:** [scout.alexarnoni.com](https://scout.alexarnoni.com) · **API:** [scout-api.alexarnoni.com](https://scout-api.alexarnoni.com/docs)

---

## Visão Geral

O Olheiro coleta, processa e expõe dados do Brasileirão 2026 em tempo real, calculando scores de scout por posição, identificando **Joias Escondidas** (alta performance com poucos minutos) e ranqueando jogadores via modelo **Moneyball** (score ÷ valor de mercado).

Desenvolvido como projeto de portfólio com foco em **Engenharia de Dados**: pipeline de ingestão automatizada, modelagem em camadas, infra containerizada e API documentada.

---

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI · Uvicorn · SQLAlchemy 2.0 · Alembic |
| Banco | PostgreSQL 16 (Docker) |
| Scheduler | APScheduler |
| Frontend | HTML/CSS/JS vanilla · Chart.js · Cloudflare Pages |
| Infra | Oracle Cloud VM · Docker Compose · Nginx · Let's Encrypt |
| Dados | SportDB API · Flashscore (avg\_rating) · ESPN CDN (logos) |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloudflare Pages                       │
│                   scout.alexarnoni.com                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────┐
│                  Oracle Cloud VM (arnoni-cloud)             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Nginx + SSL                       │    │
│  │         scout-api.alexarnoni.com → :8001            │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                   │
│  ┌──────────────────────▼──────────────────────────────┐    │
│  │           Docker Compose                            │    │
│  │                                                     │    │
│  │  ┌─────────────────────┐  ┌──────────────────────┐  │    │
│  │  │   scout-backend     │  │   scout-postgres     │  │    │
│  │  │  FastAPI · :8001    │◄─►│  PostgreSQL 16 :5433 │  │    │
│  │  │  APScheduler        │  │                      │  │    │
│  │  └──────────┬──────────┘  └──────────────────────┘  │    │
│  │             │                                        │    │
│  └─────────────┼────────────────────────────────────────┘    │
│                │                                             │
└────────────────┼─────────────────────────────────────────────┘
                 │ X-API-Key
         ┌───────▼────────┐
         │   SportDB API  │
         └────────────────┘
```

---

## Estrutura do Projeto

```
olheiro/
├── backend/
│   ├── app/
│   │   ├── models/          # SQLAlchemy models (Match, Player, PlayerMatchStats…)
│   │   ├── providers/       # Integração SportDB + Flashscore
│   │   │   ├── sportdb.py          # Cliente principal + cache inteligente
│   │   │   └── sportdb_scout.py    # Lógica de scout e ranking
│   │   ├── routers/         # Endpoints FastAPI
│   │   │   ├── teams.py
│   │   │   ├── matches.py
│   │   │   ├── players.py
│   │   │   └── scout.py
│   │   └── services/        # Persistência compartilhada
│   ├── scripts/
│   │   ├── seed_layer0.py   # Seed inicial (competição + times)
│   │   ├── sync_date.py     # Sync de uma data específica
│   │   ├── backfill.py      # Backfill de intervalo de datas
│   │   └── scheduler.py     # Scheduler diário (APScheduler)
│   └── alembic/             # Migrations
├── frontend/
│   ├── index.html           # SPA principal
│   └── assets/
├── infra/
│   └── docker-compose.yml
└── tests/
    └── test_sportdb_scout_provider.py
```

---

## Setup Local

### Pré-requisitos

- Docker + Docker Compose
- Python 3.11+
- Chave de API do [SportDB](https://api.sportdb.dev)

### 1. Clonar e configurar variáveis

```bash
git clone https://github.com/alexarnoni/Scout.git
cd Scout
cp backend/.env.example backend/.env
# preencher SPORTDB_API_KEY e DATABASE_URL
```

### 2. Subir o banco

```bash
cd infra
docker-compose up -d
```

### 3. Instalar dependências do backend

```bash
cd backend
pip install -r requirements.txt
```

### 4. Rodar migrations

```bash
cd backend
alembic upgrade head
```

### 5. Seed inicial

```bash
python -m scripts.seed_layer0
```

Cria a competição "Brasileirao 2026" e os times no banco.

### 6. Subir o backend

```bash
uvicorn app.main:app --reload --port 8001
```

Documentação disponível em `http://localhost:8001/docs`.

---

## Pipeline de Dados

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

### Scheduler automático

Sincroniza automaticamente às 00:30 BRT (rodada anterior):

```bash
python -m scripts.scheduler
```

| Variável | Default | Descrição |
|---|---|---|
| `SCOUT_COMPETITION_ID` | `1` | ID da competição no banco |

---

## Modelo de Scout

O score é calculado **por posição**, com métricas normalizadas por 90 minutos.

| Posição | Métricas principais |
|---|---|
| Goleiro | Defesas/90, Gols sofridos/90, Clean sheet rate |
| Defensor | Duelos ganhos, Interceptações, Cartões |
| Meio-campo | Passes, Assistências, Recuperações |
| Atacante | Gols/90, Chutes, Conversão, xG |

**Joias Escondidas:** jogadores com score ≥ 60 e ≤ 270 minutos jogados.

**Garimpo (Moneyball):** `moneyball_score = scout_score ÷ valor_de_mercado (M€)`. Identifica jogadores subvalorizados antes do mercado perceber.

---

## Deploy (Produção)

### Frontend

```bash
git push origin main
# Cloudflare Pages detecta mudanças em frontend/ e faz deploy automático
```

### Backend

```bash
sudo docker compose -f /opt/scout/infra/docker-compose.yml up -d --build backend
```

> Mudanças em `.env` exigem `--force-recreate` ao invés de simples restart.

---

## Testes

```bash
cd backend
pytest tests/ -v
```

---

## Roadmap

- [ ] **dbt** — camadas `stg_` e `mart_` substituindo cálculos Python
- [ ] **Airflow** — substituir APScheduler por DAGs
- [ ] **Copa do Mundo 2026** — grupos, convocados, fixtures, stats por seleção
- [ ] **PWA** — manifest.json + service worker
- [ ] **Percentis** — exibição de percentil nos cards de jogadores
- [ ] **Métricas avançadas** — Índice de Pressão, Consistência Ponderada, Eficiência de Substituição

---

## Autor

**Alexandre Arnoni** — Analista de Dados na Prefeitura de Praia Grande, estudante de Ciência de Dados (Uninter), em transição para Engenharia de Dados.

[GitHub](https://github.com/alexarnoni) · [scout.alexarnoni.com](https://scout.alexarnoni.com)
