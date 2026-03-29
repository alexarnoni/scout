# Implementation Plan: sportdb-scout-migration

## Overview

Migração cirúrgica do sistema de scout/ranking para eliminar a dependência do banco ESPN. Cria o módulo `sportdb_scout.py` como novo provider, modifica `scout.py` para usar o novo provider, e atualiza o endpoint `/scout/ranking` em `main.py`.

## Tasks

- [x] 1. Criar `backend/app/providers/sportdb_scout.py` com cache e busca de partidas
  - Criar o arquivo com as variáveis de cache compartilhado (`_cache: dict`, `_cache_lock: threading.Lock`)
  - Implementar `_cache_get(key)` e `_cache_set(key, data, ttl_seconds)` usando `datetime` para verificação de TTL
  - Implementar `get_season_results(season)` que itera todos os pages da API SportDB até retornar lista vazia, com TTL de 7200s
  - Reutilizar `SPORTDB_API_KEY`, `SPORTDB_BASE`, `COMPETITION_SLUG` e `HEADERS` já definidos em `sportdb.py`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.1, 7.3, 7.4_

  - [ ]* 1.1 Escrever property test para cache hit idempotência (Property 1)
    - **Property 1: Cache hit idempotência**
    - Mockar a função HTTP; verificar que segunda chamada com mesmo parâmetro não dispara nova requisição
    - **Validates: Requirements 1.3, 2.4, 8.1**

- [x] 2. Implementar `get_match_player_stats` e `_merge_lineup_stats` em `sportdb_scout.py`
  - Implementar `_merge_lineup_stats(lineups_data, stats_data, event_id)` que combina lineup e stats por `participantId`; jogadores sem stats recebem zeros
  - Implementar `get_match_player_stats(event_id)` que busca `/lineups` e `/stats` da partida, chama `_merge_lineup_stats`, e armazena no cache com TTL de 86400s
  - Derivar `goals_conceded` para goleiros a partir do placar da partida (score do time adversário)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 2.1 Escrever property test para merge de lineup e stats (Property 7)
    - **Property 7: Merge de lineup e stats por identificador de jogador**
    - Gerar lineup e stats aleatórios com Hypothesis; verificar que resultado tem exatamente um registro por jogador único do lineup
    - **Validates: Requirements 2.2, 2.3**

- [x] 3. Implementar `get_player_season_stats` em `sportdb_scout.py`
  - Iterar sobre todas as partidas de `get_season_results`, acumular stats por `participantId` via `get_match_player_stats`
  - Ignorar partidas individuais com erro (`try/except` com `continue`)
  - Calcular métricas p90 (goals, assists, shots, shots_on_target, fouls, yellow_cards, red_cards, saves, goals_conceded)
  - Calcular `avg_rating` (média dos ratings não-nulos), `conversion_rate` (goals/shots se shots>0 else 0.0), `save_rate` (saves/(saves+goals_conceded) se denominador>0 else 0.0)
  - Calcular `clean_sheet_rate` (partidas sem gols sofridos / total de partidas do goleiro)
  - Mapear `positionKey` → `position_group` via `SPORTDB_POSITION_GROUPS`; excluir jogadores com posição não mapeada
  - Filtrar jogadores com `total_minutes < min_minutes`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 3.1 Escrever property test para cálculo p90 (Property 2)
    - **Property 2: Cálculo correto de p90**
    - `@given(v=st.floats(min_value=0, max_value=1e6), minutes=st.floats(min_value=0.1, max_value=1e5))`
    - Verificar `abs(result - v / (minutes / 90)) < 1e-9`; para `minutes <= 0` verificar `result == 0.0`
    - **Validates: Requirements 3.2, 5.4**

  - [ ]* 3.2 Escrever property test para métricas derivadas (Property 5)
    - **Property 5: Métricas derivadas matematicamente corretas**
    - Gerar jogadores com shots, goals, saves, goals_conceded aleatórios; verificar fórmulas de conversion_rate, save_rate e avg_rating
    - **Validates: Requirements 3.3, 3.4, 3.5**

  - [ ]* 3.3 Escrever property test para filtro por minutos mínimos (Property 6)
    - **Property 6: Filtro por minutos mínimos**
    - `@given(min_minutes=st.integers(min_value=0, max_value=500))`
    - Verificar que nenhum jogador no resultado tem `total_minutes < min_minutes`
    - **Validates: Requirements 3.6**

  - [ ]* 3.4 Escrever property test para métricas p90 não-negativas (Property 11)
    - **Property 11: Métricas p90 são floats não-negativos**
    - Verificar que todos os campos `*_p90` são `float >= 0.0` para qualquer entrada válida
    - **Validates: Requirements 8.2, 8.3**

- [x] 4. Checkpoint — Testar provider isoladamente
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Modificar `backend/app/services/scout.py` para usar o novo provider
  - Remover imports de `sqlalchemy`, `Session`, `Player`, `PlayerMatchStats`, `Team`, `Match`, `TeamMatchStats`
  - Remover funções `_aggregate_player_stats` e `_get_goals_conceded`
  - Remover dicionário `POSITION_GROUPS` (ESPN)
  - Adicionar `SPORTDB_POSITION_GROUPS` com mapeamento GKP/DEF/MID/FWD → Goleiro/Defensor/Meio-campo/Atacante
  - Adicionar import de `get_player_season_stats` de `app.providers.sportdb_scout`
  - Manter `_p90`, `_normalize` e `GROUP_METRICS` inalterados
  - Reescrever `get_scout_ranking(position_group, season="2026", min_minutes=180)` sem `db` e `competition_id`: chamar `get_player_season_stats`, filtrar por `position_group`, calcular métricas, normalizar e ordenar por score
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 5.1 Escrever property test para invariantes de _normalize (Property 3)
    - **Property 3: Invariantes de _normalize**
    - `@given(values=st.lists(st.floats(min_value=-1e6, max_value=1e6), min_size=1))`
    - Verificar que todos os valores de saída estão em `[0.0, 100.0]`; quando todos iguais, saída é `50.0`
    - **Validates: Requirements 5.3**

  - [ ]* 5.2 Escrever property test para positionKey não mapeado (Property 8)
    - **Property 8: positionKey não mapeado implica exclusão**
    - Gerar jogadores com positionKey fora de {GKP, DEF, MID, FWD}; verificar que não aparecem no resultado de `get_scout_ranking`
    - **Validates: Requirements 4.5**

  - [ ]* 5.3 Escrever property test para ordenação por score (Property 9)
    - **Property 9: Resultado ordenado por score decrescente**
    - Para qualquer lista de jogadores retornada, verificar que `score[i] >= score[i+1]` para todo par adjacente
    - **Validates: Requirements 6.5**

  - [ ]* 5.4 Escrever property test para campos obrigatórios do PlayerScoutCard (Property 10)
    - **Property 10: Campos obrigatórios do PlayerScoutCard presentes**
    - Verificar que cada dict retornado contém `player_id`, `player_name`, `team_name`, `position`, `total_minutes`, `matches_played`, `score`, `metrics`
    - **Validates: Requirements 6.1, 6.2**

- [x] 6. Atualizar endpoint `/scout/ranking` em `backend/app/main.py`
  - Remover parâmetros `db: Session = Depends(get_db)` e `competition_id: int` do endpoint `scout_ranking`
  - Adicionar parâmetro `season: str = "2026"` ao endpoint
  - Atualizar chamada para `get_scout_ranking(position, season, min_minutes)` sem `db` e `competition_id`
  - Remover import de `POSITION_GROUPS` de `app.services.scout` (não existe mais); manter `VALID_POSITIONS` local
  - Atualizar endpoint `/scout/moneyball` da mesma forma (remover `db`/`competition_id`, adicionar `season`)
  - Atualizar endpoint `/scout/player/{player_id}`: remover dependência de `POSITION_GROUPS` ESPN; usar `SPORTDB_POSITION_GROUPS` ou buscar `position_group` via `get_player_season_stats`
  - _Requirements: 5.1, 5.2, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 7. Criar testes unitários em `backend/tests/`
  - Criar `backend/tests/test_sportdb_scout_provider.py` com testes unitários para:
    - Cache miss → requisição HTTP realizada
    - Cache hit dentro do TTL → sem requisição HTTP
    - Jogador no lineup sem entrada nos stats → métricas zeradas
    - `conversion_rate` com `shots = 0` → `0.0`
    - `save_rate` com denominador `0` → `0.0`
    - `_p90` com `minutes = 0` → `0.0`
    - Erro em partida individual → partida ignorada, demais processadas
  - Criar `backend/tests/test_scout_service.py` com testes unitários para:
    - Mapeamento correto de todos os positionKey (GKP/DEF/MID/FWD → grupos)
    - `positionKey` inválido → jogador excluído do resultado
    - `position_group` inválido → lista vazia
    - Nenhum jogador com minutos suficientes → lista vazia
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 6.3, 6.4_

- [x] 8. Escrever property tests em `backend/tests/`
  - Adicionar a `test_sportdb_scout_provider.py` os property tests das Properties 1, 4, 5, 6, 7, 11
  - Adicionar a `test_scout_service.py` os property tests das Properties 2, 3, 8, 9, 10
  - Cada teste deve usar `@settings(max_examples=100)` e incluir a tag de referência no comentário
  - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 8.1 Property test para agregação completa de partidas (Property 4)
    - **Property 4: Agregação completa de partidas**
    - Mockar `get_season_results` com N partidas; verificar que `get_player_season_stats` processa todas as N partidas
    - **Validates: Requirements 3.1, 3.7**

- [x] 9. Checkpoint final — Garantir que todos os testes passam
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marcadas com `*` são opcionais e podem ser puladas para MVP mais rápido
- Cada task referencia requirements específicos para rastreabilidade
- O arquivo `sportdb.py` existente não deve ser modificado; `sportdb_scout.py` é um módulo separado
- O schema `PlayerScoutCard` e `ScoutRanking` não mudam — compatibilidade com frontend garantida
- Property tests usam `hypothesis` (`pip install hypothesis`)
