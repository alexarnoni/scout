# Documento de Design — Garimpo Z-Score Dual

## Visão Geral

Este design descreve a substituição da fórmula simples do Garimpo (`score / market_value_in_millions`) por um modelo de **z-score dual** no sistema de scouting "Olheiro". O novo modelo calcula z-scores independentes para performance e valor de mercado (log-transformado), produzindo um índice `garimpo_score = z_perf - z_valor` que identifica jogadores estatisticamente subvalorizados.

### Motivação

A fórmula atual (`score / mv`) tem limitações:
- Sensível a escalas absolutas (um jogador com score 50 e mv €0.5M = 100, mas score 80 e mv €1M = 80)
- Não normaliza a distribuição dos scores nem dos valores de mercado
- Valores de mercado têm distribuição log-normal, mas são tratados linearmente

O z-score dual resolve isso normalizando ambas as dimensões em suas respectivas distribuições, tornando o índice comparável e estatisticamente robusto.

### Decisões de Design

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Transformação do market value | `log(mv)` (logaritmo natural) | Valores de mercado seguem distribuição log-normal; log lineariza a distribuição |
| Floor de market value | €100.000 | Evita `log(0)` e valores extremamente baixos que distorceriam o z-score |
| Threshold mínimo de amostra | 3 jogadores com mv | Z-score requer amostra mínima para desvio padrão significativo |
| Proteção stdev=0 | Retorna `None` para todos | Se todos têm mesmo score ou mesmo mv, não há variação para medir |
| Posição de None na ordenação | Ao final da lista | Jogadores sem garimpo_score não devem competir no ranking |

## Arquitetura

```mermaid
flowchart TD
    FE["frontend/index.html<br/>loadGarimpo()"] -->|GET /scout/moneyball| EP["backend/app/main.py<br/>scout_moneyball()"]
    EP -->|get_scout_ranking()| SR["backend/app/services/scout.py<br/>get_scout_ranking()"]
    EP -->|get_player_market_value()| MV["backend/app/providers/sportdb.py<br/>get_player_market_value()"]
    EP -->|compute_garimpo()| CG["backend/app/services/scout.py<br/>compute_garimpo() ← NOVO"]
    SR -->|get_player_season_stats()| PS["backend/app/providers/sportdb_scout.py"]
    
    style CG fill:#1e1208,stroke:#ea580c,color:#ea580c
```

### Fluxo de Dados

1. Frontend chama `GET /scout/moneyball?position=X&min_minutes=180`
2. Endpoint chama `get_scout_ranking(position)` → retorna **todos** os jogadores (sem `[:20]`)
3. Para cada jogador, busca `market_value` via `get_player_market_value()`
4. Monta lista com `score`, `market_value_m` e demais campos
5. Chama `compute_garimpo(players)` → calcula z-scores e retorna lista ordenada
6. Retorna resposta com `garimpo_score` em vez de `moneyball_score`

## Componentes e Interfaces

### 1. `compute_garimpo(players: list[dict]) -> list[dict]` — NOVA FUNÇÃO

**Localização:** `backend/app/services/scout.py`

**Entrada:** Lista de dicts com campos obrigatórios:
- `score: float` — score do scout ranking
- `market_value_m: float | None` — valor de mercado em milhões de euros

**Saída:** Mesma lista com campo `garimpo_score: float | None` adicionado, ordenada por `garimpo_score` decrescente (None ao final).

**Constante:** `MARKET_VALUE_FLOOR = 100_000`

**Algoritmo:**
```python
import math

MARKET_VALUE_FLOOR = 100_000

def compute_garimpo(players: list[dict]) -> list[dict]:
    # 1. Separar jogadores com e sem market value
    with_mv = [p for p in players if p.get("market_value_m") is not None]
    
    # 2. Verificar threshold mínimo
    if len(with_mv) < 3:
        for p in players:
            p["garimpo_score"] = None
        return sorted(players, key=lambda x: (x["garimpo_score"] is None, -(x["garimpo_score"] or 0)))
    
    # 3. Calcular z_perf
    scores = [p["score"] for p in with_mv]
    mean_score = sum(scores) / len(scores)
    stdev_score = (sum((s - mean_score) ** 2 for s in scores) / len(scores)) ** 0.5
    
    # 4. Calcular z_valor (log-transformado com floor)
    log_mvs = [math.log(max(p["market_value_m"] * 1_000_000, MARKET_VALUE_FLOOR)) for p in with_mv]
    mean_log = sum(log_mvs) / len(log_mvs)
    stdev_log = (sum((v - mean_log) ** 2 for v in log_mvs) / len(log_mvs)) ** 0.5
    
    # 5. Proteção stdev=0
    if stdev_score == 0 or stdev_log == 0:
        for p in players:
            p["garimpo_score"] = None
        return sorted(players, key=lambda x: (x["garimpo_score"] is None, -(x["garimpo_score"] or 0)))
    
    # 6. Calcular garimpo para jogadores com mv
    mv_set = {id(p) for p in with_mv}
    for i, p in enumerate(with_mv):
        z_perf = (p["score"] - mean_score) / stdev_score
        log_mv = math.log(max(p["market_value_m"] * 1_000_000, MARKET_VALUE_FLOOR))
        z_valor = (log_mv - mean_log) / stdev_log
        p["garimpo_score"] = round(z_perf - z_valor, 2)
    
    # 7. None para jogadores sem mv
    for p in players:
        if id(p) not in mv_set:
            p["garimpo_score"] = None
    
    # 8. Ordenar: garimpo_score desc, None ao final
    return sorted(players, key=lambda x: (x["garimpo_score"] is None, -(x["garimpo_score"] or 0)))
```

### 2. Refatoração do endpoint `scout_moneyball` 

**Localização:** `backend/app/main.py`

**Mudanças:**
- Remover `ranking[:20]` → usar `ranking` completo (todos os jogadores)
- Remover cálculo inline `score / mv_num`
- Chamar `compute_garimpo(result)` após montar a lista
- Campo de saída: `garimpo_score` em vez de `moneyball_score`
- Remover `result.sort(...)` manual (compute_garimpo já retorna ordenado)

### 3. Atualização do Frontend

**Localização:** `frontend/index.html`, função `loadGarimpo()`

**Mudanças:**
- Substituir `p.moneyball_score` → `p.garimpo_score`
- Nova lógica de cor:
  - `>= 1.5` → `var(--accent)` (laranja)
  - `>= 0.5` → `var(--draw)` (amarelo)
  - `< 0` → `var(--loss)` (cinza escuro)
  - else (`>= 0 && < 0.5`) → `var(--text-secondary)`
- Formatação com sinal: `+1.23` / `-0.45`
- Subtítulo: `"z-score dual · performance vs. preço"`
- Cabeçalho coluna: `"⛏️ Garimpo"`
- Texto info box: descrição do modelo z-score dual

## Modelos de Dados

### Entrada de `compute_garimpo`

```python
# Cada dict na lista de entrada:
{
    "player_id": str,
    "player_name": str,
    "team_name": str,
    "position": str,
    "score": float,           # score do scout ranking (0-100)
    "market_value": str,      # ex: "€1.5M", "€500K"
    "market_value_m": float | None,  # valor em milhões, ex: 1.5, 0.5
    # ... demais campos do scout ranking
}
```

### Saída de `compute_garimpo`

```python
# Cada dict na lista de saída (mesmos campos + garimpo_score):
{
    # ... todos os campos de entrada preservados
    "garimpo_score": float | None,  # z_perf - z_valor, arredondado 2 casas
}
```

### Resposta do endpoint `/scout/moneyball`

Campo renomeado: `moneyball_score` → `garimpo_score`

```python
# Exemplo de resposta:
[
    {
        "player_id": "abc123",
        "player_name": "Jogador X",
        "team_name": "Time Y",
        "position": "FWD",
        "score": 78.5,
        "market_value": "€500K",
        "market_value_m": 0.5,
        "garimpo_score": 1.87,  # ← novo campo
        # ... demais campos
    }
]
```

## Propriedades de Correção

*Uma propriedade é uma característica ou comportamento que deve ser verdadeiro em todas as execuções válidas de um sistema — essencialmente, uma declaração formal sobre o que o sistema deve fazer. Propriedades servem como ponte entre especificações legíveis por humanos e garantias de correção verificáveis por máquina.*

### Propriedade 1: Round-trip do garimpo_score

*Para qualquer* lista de jogadores com pelo menos 3 valores de mercado distintos e desvio padrão não-zero tanto nos scores quanto nos log-valores de mercado, o `garimpo_score` de cada jogador com market value deve ser igual a `z_perf - z_valor`, onde `z_perf = (score - mean(scores)) / stdev(scores)` e `z_valor = (log(max(mv*1e6, 100_000)) - mean(log_mvs)) / stdev(log_mvs)`, calculados independentemente a partir dos dados de entrada.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 5.8**

### Propriedade 2: Atribuição correta de None

*Para qualquer* lista de jogadores, se um jogador não possui `market_value_m`, OU se menos de 3 jogadores no grupo possuem market value válido, OU se o desvio padrão dos scores ou dos log-valores é zero, então o `garimpo_score` desse jogador deve ser `None`.

**Validates: Requirements 1.5, 1.6, 1.7**

### Propriedade 3: Invariante de ordenação

*Para qualquer* lista de jogadores processada por `compute_garimpo`, a lista retornada deve estar ordenada por `garimpo_score` em ordem decrescente, com todos os jogadores cujo `garimpo_score` é `None` posicionados ao final da lista.

**Validates: Requirements 1.8, 2.4**

## Tratamento de Erros

| Cenário | Comportamento |
|---------|---------------|
| `market_value_m` é `None` | Jogador recebe `garimpo_score = None` |
| Menos de 3 jogadores com mv | Todos recebem `garimpo_score = None` |
| `stdev_score == 0` (todos scores iguais) | Todos recebem `garimpo_score = None` |
| `stdev_log == 0` (todos mvs iguais após floor) | Todos recebem `garimpo_score = None` |
| `market_value_m < 0.1` (abaixo de €100K) | Floor aplicado: `max(mv * 1e6, 100_000)` |
| `get_player_market_value()` falha | Retorna `None` → jogador sem mv → garimpo = None |
| Lista vazia de jogadores | Retorna lista vazia |

## Estratégia de Testes

### Testes Unitários (`backend/tests/test_garimpo.py`)

7 testes de exemplo cobrindo cenários específicos:

1. **Jogador score alto + mv baixo lidera** — Validates 5.1
2. **Estrela cara (score alto + mv alto) ≈ 0** — Validates 5.2
3. **Jogador sem mv recebe None** — Validates 5.3
4. **Menos de 3 com mv → todos None** — Validates 5.4
5. **Stdev zero → todos None** — Validates 5.5
6. **Resultado ordenado decrescente** — Validates 5.6
7. **MARKET_VALUE_FLOOR aplicado** — Validates 5.7

### Testes Property-Based (`backend/tests/test_garimpo.py`)

Biblioteca: **Hypothesis** (já utilizada no projeto em `test_scout_confidence_penalty.py`)

Configuração: `@settings(max_examples=100)` para cada propriedade.

1. **Property 1: Round-trip do garimpo_score**
   - Tag: `Feature: garimpo-zscore-dual, Property 1: Round-trip do garimpo_score`
   - Gerador: listas de jogadores com scores `float(0-100)` e market_values `float(0.01-100)` em milhões, pelo menos 3 com mv, scores e mvs não todos iguais
   - Asserção: `garimpo_score ≈ z_perf - z_valor` (tolerância 1e-9)

2. **Property 2: Atribuição correta de None**
   - Tag: `Feature: garimpo-zscore-dual, Property 2: Atribuição correta de None`
   - Gerador: listas de jogadores com mix de `market_value_m = None` e valores válidos, incluindo cenários com <3 mvs e stdev=0
   - Asserção: jogadores sem mv → None; grupo com <3 mvs → todos None; stdev=0 → todos None

3. **Property 3: Invariante de ordenação**
   - Tag: `Feature: garimpo-zscore-dual, Property 3: Invariante de ordenação`
   - Gerador: listas aleatórias de jogadores
   - Asserção: resultado ordenado decrescente, None ao final

### Testes de Preservação

- Executar `test_scout_service.py` e `test_scout_confidence_penalty.py` sem modificações para garantir que funções existentes não foram afetadas.

### Testes Manuais (Frontend)

- Verificar cores dos thresholds no navegador
- Verificar formatação com sinal (+/-)
- Verificar textos atualizados (subtítulo, cabeçalho, info box)
