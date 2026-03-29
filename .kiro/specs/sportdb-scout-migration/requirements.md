# Requirements Document

## Introduction

Migração do sistema de scout/ranking da Scout Platform para eliminar a dependência do banco ESPN (populado por scraper) e passar a consumir dados em tempo real via SportDB/Flashscore. O novo fluxo busca estatísticas de partidas diretamente da API SportDB, agrega métricas por jogador com cache em memória, e mantém compatibilidade total com os schemas e endpoints existentes.

Fluxo atual: banco ESPN → `scout.py` (SQLAlchemy) → `/scout/ranking` → frontend  
Fluxo novo: SportDB API → `sportdb_scout.py` (cache em memória) → `scout.py` (normalização) → `/scout/ranking` → frontend

## Glossary

- **SportDB_Provider**: Módulo `backend/app/providers/sportdb_scout.py` responsável por buscar e agregar dados da API SportDB.
- **Scout_Service**: Módulo `backend/app/services/scout.py` responsável por normalizar métricas e calcular o score de ranking.
- **Cache**: Dicionário em memória protegido por `threading.Lock`, com TTL configurável por tipo de dado.
- **Season_Results**: Lista de partidas finalizadas de uma temporada, retornada pela API SportDB.
- **Match_Player_Stats**: Estatísticas individuais de jogadores em uma partida, combinando dados de lineup e stats da API SportDB.
- **Player_Season_Stats**: Agregação de estatísticas de um jogador ao longo de toda a temporada, com métricas p90 calculadas.
- **positionKey**: Identificador de posição no formato SportDB (GKP, DEF, MID, FWD).
- **position_group**: Grupo de posição usado internamente pelo Scout_Service (Goleiro, Defensor, Meio-campo, Atacante).
- **p90**: Métrica normalizada por 90 minutos jogados (valor / (minutos / 90)).
- **score**: Média aritmética das métricas normalizadas (min-max 0–100) de um jogador dentro do seu grupo de posição.
- **TTL**: Tempo de vida de uma entrada no Cache antes de ser revalidada.
- **PlayerScoutCard**: Schema Pydantic existente que representa um jogador no ranking com seu score e métricas.
- **ScoutRanking**: Schema Pydantic existente que representa a lista de jogadores ranqueados.

---

## Requirements

### Requirement 1: Busca de Partidas da Temporada

**User Story:** Como desenvolvedor, quero buscar todas as partidas finalizadas de uma temporada via SportDB, para que o sistema tenha a base de dados necessária para calcular estatísticas dos jogadores.

#### Acceptance Criteria

1. WHEN `get_season_results` é chamado com um parâmetro de temporada, THE SportDB_Provider SHALL retornar a lista de partidas finalizadas daquela temporada consultando todos os pages disponíveis da API SportDB.
2. WHEN a API SportDB retorna erro HTTP, THE SportDB_Provider SHALL propagar a exceção para o chamador.
3. WHILE o Cache contém uma entrada válida para a temporada solicitada, THE SportDB_Provider SHALL retornar os dados do Cache sem realizar nova requisição HTTP.
4. WHEN o TTL de uma entrada de Season_Results no Cache expira, THE SportDB_Provider SHALL buscar dados atualizados da API SportDB e atualizar o Cache.
5. THE SportDB_Provider SHALL usar TTL de 2 horas para entradas de Season_Results no Cache.

---

### Requirement 2: Busca de Estatísticas de Partida Individual

**User Story:** Como desenvolvedor, quero buscar e combinar dados de lineup e estatísticas de jogadores de uma partida específica, para que cada jogador tenha suas métricas individuais associadas.

#### Acceptance Criteria

1. WHEN `get_match_player_stats` é chamado com um `event_id`, THE SportDB_Provider SHALL buscar os dados de lineup e de stats da partida nos respectivos endpoints da API SportDB.
2. WHEN os dados de lineup e stats são obtidos, THE SportDB_Provider SHALL combinar os dois conjuntos de dados por identificador de jogador, produzindo um registro unificado por jogador com posição, minutos jogados e estatísticas.
3. WHEN um jogador aparece no lineup mas não possui entrada correspondente nos stats, THE SportDB_Provider SHALL incluir o jogador com valores numéricos zerados para as métricas ausentes.
4. WHILE o Cache contém uma entrada válida para o `event_id` solicitado, THE SportDB_Provider SHALL retornar os dados do Cache sem realizar novas requisições HTTP.
5. THE SportDB_Provider SHALL usar TTL de 24 horas para entradas de Match_Player_Stats de partidas já finalizadas no Cache.
6. THE SportDB_Provider SHALL usar `threading.Lock` para garantir acesso thread-safe ao Cache em todas as operações de leitura e escrita.

---

### Requirement 3: Agregação de Estatísticas da Temporada por Jogador

**User Story:** Como desenvolvedor, quero agregar as estatísticas de todas as partidas da temporada por jogador, para que o Scout_Service possa calcular o ranking sem depender do banco ESPN.

#### Acceptance Criteria

1. WHEN `get_player_season_stats` é chamado com parâmetros de temporada e minutos mínimos, THE SportDB_Provider SHALL iterar sobre todas as partidas retornadas por `get_season_results` e acumular as estatísticas de cada jogador.
2. WHEN as estatísticas são acumuladas, THE SportDB_Provider SHALL calcular as métricas p90 (goals_p90, assists_p90, shots_p90, shots_on_target_p90, fouls_p90, yellow_cards_p90, red_cards_p90, saves_p90) dividindo o total acumulado por (total_minutes / 90).
3. WHEN as estatísticas são acumuladas, THE SportDB_Provider SHALL calcular `avg_rating` como a média aritmética dos ratings individuais por partida quando disponíveis.
4. WHEN as estatísticas são acumuladas, THE SportDB_Provider SHALL calcular `conversion_rate` como goals / shots quando shots > 0, e 0.0 caso contrário.
5. WHEN as estatísticas são acumuladas, THE SportDB_Provider SHALL calcular `save_rate` como saves / (saves + goals_conceded) quando o denominador > 0, e 0.0 caso contrário.
6. WHEN `get_player_season_stats` é chamado com `min_minutes`, THE SportDB_Provider SHALL excluir da resposta jogadores com total de minutos jogados inferior ao valor de `min_minutes`.
7. IF a API SportDB retornar erro ao buscar stats de uma partida individual, THEN THE SportDB_Provider SHALL ignorar aquela partida e continuar a agregação das demais.

---

### Requirement 4: Mapeamento de Posição SportDB para Grupos de Posição

**User Story:** Como desenvolvedor, quero mapear os `positionKey` do SportDB para os grupos de posição internos do Scout_Service, para que a lógica de normalização e scoring existente continue funcionando sem alterações.

#### Acceptance Criteria

1. THE Scout_Service SHALL mapear o `positionKey` "GKP" para o grupo "Goleiro".
2. THE Scout_Service SHALL mapear o `positionKey` "DEF" para o grupo "Defensor".
3. THE Scout_Service SHALL mapear o `positionKey` "MID" para o grupo "Meio-campo".
4. THE Scout_Service SHALL mapear o `positionKey` "FWD" para o grupo "Atacante".
5. WHEN um jogador possui `positionKey` não mapeado ou ausente, THE Scout_Service SHALL excluir o jogador do ranking.

---

### Requirement 5: Substituição da Fonte de Dados no Scout_Service

**User Story:** Como desenvolvedor, quero que o Scout_Service use o SportDB_Provider como fonte de dados em vez do banco ESPN, para que o ranking seja calculado com dados em tempo real sem dependência de scraper.

#### Acceptance Criteria

1. WHEN `get_scout_ranking` é chamado, THE Scout_Service SHALL obter os dados de jogadores chamando `get_player_season_stats` do SportDB_Provider em vez de executar queries SQLAlchemy contra o banco ESPN.
2. THE Scout_Service SHALL remover todas as importações e referências a `PlayerMatchStats`, `TeamMatchStats`, `Match` e `Session` do SQLAlchemy após a migração.
3. THE Scout_Service SHALL manter a função `_normalize` com comportamento idêntico ao atual (min-max 0–100, retorno de 50.0 para todos quando todos os valores são iguais).
4. THE Scout_Service SHALL manter a função `_p90` com comportamento idêntico ao atual.
5. THE Scout_Service SHALL manter o dicionário `GROUP_METRICS` com as mesmas métricas e flags de inversão definidas atualmente.

---

### Requirement 6: Compatibilidade com Schemas e Endpoint Existentes

**User Story:** Como desenvolvedor, quero que a migração não altere os contratos de API existentes, para que o frontend continue funcionando sem modificações.

#### Acceptance Criteria

1. THE Scout_Service SHALL retornar dados compatíveis com o schema `PlayerScoutCard` para cada jogador no ranking, incluindo os campos `player_id`, `player_name`, `team_name`, `position`, `total_minutes`, `matches_played`, `score` e `metrics`.
2. THE Scout_Service SHALL retornar dados compatíveis com o schema `ScoutRanking` para a lista de jogadores ranqueados.
3. WHEN `get_scout_ranking` é chamado com um `position_group` inválido, THE Scout_Service SHALL retornar uma lista vazia.
4. WHEN `get_scout_ranking` é chamado e nenhum jogador atinge o mínimo de minutos, THE Scout_Service SHALL retornar uma lista vazia.
5. THE Scout_Service SHALL ordenar o resultado final por `score` em ordem decrescente, mantendo o comportamento atual.

---

### Requirement 7: Integridade do Cache e Concorrência

**User Story:** Como desenvolvedor, quero que o cache em memória seja thread-safe e respeite os TTLs definidos, para que múltiplas requisições simultâneas não causem inconsistências ou chamadas desnecessárias à API.

#### Acceptance Criteria

1. THE SportDB_Provider SHALL usar um único `threading.Lock` compartilhado para todas as operações de leitura e escrita no Cache.
2. WHEN duas threads solicitam o mesmo recurso simultaneamente e o Cache está expirado, THE SportDB_Provider SHALL garantir que apenas uma requisição HTTP seja feita à API SportDB, com a outra thread aguardando o resultado.
3. THE SportDB_Provider SHALL armazenar o timestamp de criação junto com cada entrada do Cache para permitir verificação de TTL.
4. WHEN uma entrada do Cache é verificada, THE SportDB_Provider SHALL comparar o tempo decorrido desde o timestamp de criação com o TTL correspondente ao tipo de dado.

---

### Requirement 8: Propriedade de Round-Trip do Provider

**User Story:** Como desenvolvedor, quero garantir que os dados retornados pelo SportDB_Provider sejam estruturalmente consistentes após múltiplas chamadas, para que o sistema de cache não introduza regressões silenciosas.

#### Acceptance Criteria

1. FOR ALL chamadas a `get_player_season_stats` com os mesmos parâmetros dentro do TTL do Cache, THE SportDB_Provider SHALL retornar resultados idênticos (propriedade de idempotência do cache).
2. WHEN `get_player_season_stats` retorna um jogador, THE SportDB_Provider SHALL garantir que todos os campos numéricos de métricas p90 sejam valores do tipo `float` maiores ou iguais a 0.0.
3. WHEN `get_player_season_stats` retorna um jogador com `total_minutes` igual a 0, THE SportDB_Provider SHALL retornar 0.0 para todas as métricas p90 desse jogador.
