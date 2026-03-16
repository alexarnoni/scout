# Documento de Requisitos — Scout Platform

## Introdução

A Scout Platform é um sistema de scouting de futebol para o Brasileirão Série A 2026.
O sistema é composto por três camadas: uma API REST (FastAPI/Python), um dashboard analítico
(Streamlit) e um frontend web estático (HTML/CSS/JS). Os dados são sincronizados
automaticamente a partir da ESPN e persistidos em PostgreSQL.

O objetivo é sair do "vibe code" e ter requisitos claros que guiem o desenvolvimento,
identifiquem lacunas e sirvam de base para um plano de implementação estruturado.

---

## Glossário

- **API**: Serviço backend FastAPI que expõe endpoints REST para todos os dados da plataforma.
- **Dashboard**: Interface Streamlit voltada para análise de scouting de jogadores.
- **Frontend**: Interface web estática (HTML/JS) voltada para perfis de times.
- **ESPN_Provider**: Módulo responsável por buscar dados da API não-oficial da ESPN.
- **Scheduler**: Processo que executa sincronizações periódicas de dados.
- **Scout_Engine**: Serviço que calcula rankings e scores de jogadores por posição.
- **Player_Analytics**: Serviço que calcula médias, radar e série temporal de um jogador.
- **Team_Analytics**: Serviço que calcula médias, radar, tendência e série temporal de um time.
- **Persistence**: Serviço de upsert que salva dados da ESPN no banco PostgreSQL.
- **Score**: Valor numérico de 0 a 100 que representa a performance relativa de um jogador dentro do seu grupo posicional.
- **p90**: Métrica normalizada por 90 minutos jogados.
- **Joia Escondida**: Jogador com Score ≥ 60 e total de minutos ≤ 270.
- **Grupo Posicional**: Agrupamento de posições ESPN em: Goleiro, Defensor, Meio-campo, Atacante.
- **Rodada**: Unidade de disputa do campeonato, equivalente a uma jornada.
- **Partida**: Confronto entre dois times em uma rodada.
- **Elenco**: Conjunto de jogadores e comissão técnica de um time.
- **Titular**: Jogador que inicia a partida no campo.
- **Reserva**: Jogador disponível no banco de reservas.

---

## Requisitos

### Requisito 1: Sincronização de Dados via ESPN

**User Story:** Como operador do sistema, quero que os dados de partidas, times e jogadores
sejam sincronizados automaticamente a partir da ESPN, para que o banco de dados esteja
sempre atualizado sem intervenção manual.

#### Critérios de Aceitação

1. WHEN a ESPN_Provider recebe uma data válida, THE ESPN_Provider SHALL buscar todas as partidas do Brasileirão Série A naquela data e retornar uma lista de objetos de partida com estatísticas de times e jogadores.
2. WHEN a ESPN_Provider encontra um erro HTTP em uma requisição de summary, THE ESPN_Provider SHALL registrar o erro em log e retornar os metadados da partida sem estatísticas, sem abortar o lote.
3. WHEN a ESPN_Provider falha em uma requisição, THE ESPN_Provider SHALL tentar novamente até 3 vezes com intervalo de 5 segundos entre tentativas antes de lançar exceção.
4. WHEN o Scheduler é iniciado, THE Scheduler SHALL executar sincronizações periódicas de dados de acordo com o intervalo configurado.
5. WHEN a Persistence recebe dados de uma partida, THE Persistence SHALL realizar upsert de Competition, Team, Player, Match, TeamMatchStats e PlayerMatchStats sem criar duplicatas.
6. IF o nome de um time recebido da ESPN não corresponde a nenhum time no banco, THEN THE Persistence SHALL registrar um aviso em log e ignorar os dados daquele time sem falhar a sincronização.
7. THE ESPN_Provider SHALL aguardar 2 segundos entre chamadas consecutivas de summary para respeitar a API da ESPN.
8. WHEN o script backfill é executado com um intervalo de datas, THE Scheduler SHALL sincronizar todas as datas do intervalo em sequência.

---

### Requisito 2: Gerenciamento de Competições e Times

**User Story:** Como usuário do Frontend, quero visualizar a lista de times do Brasileirão
e selecionar um time para ver seu perfil, para que eu possa navegar facilmente entre os clubes.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /competitions que retorna todas as competições cadastradas ordenadas por nome.
2. THE API SHALL expor um endpoint GET /competitions/{competition_id}/teams que retorna todos os times de uma competição ordenados por nome.
3. IF a competition_id fornecida não existir, THEN THE API SHALL retornar HTTP 404 com mensagem "Competition not found".
4. THE Frontend SHALL carregar automaticamente a competição do Brasileirão ao inicializar, sem exigir seleção manual do usuário.
5. THE Frontend SHALL exibir a lista de times na sidebar com logo e nome de cada time.
6. WHEN o usuário digita no campo de busca da sidebar, THE Frontend SHALL filtrar a lista de times em tempo real, exibindo apenas os times cujo nome contém o texto digitado.
7. WHEN o usuário seleciona um time na sidebar, THE Frontend SHALL carregar e exibir o perfil completo daquele time.
8. WHERE a largura da tela for menor que 768px, THE Frontend SHALL substituir a sidebar por um elemento select para seleção de times.

---

### Requisito 3: Perfil de Time no Frontend

**User Story:** Como scout ou analista, quero visualizar o perfil completo de um time,
incluindo KPIs da temporada, últimos resultados e elenco posicionado, para que eu possa
avaliar rapidamente o desempenho e a composição do time.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /teams/{team_id}/analytics/summary que retorna médias de estatísticas do time para uma janela configurável de partidas.
2. THE API SHALL expor um endpoint GET /teams/{team_id}/matches que retorna todas as partidas do time ordenadas por data decrescente.
3. THE API SHALL expor um endpoint GET /teams/{team_id}/squad que retorna o elenco completo com jogadores e comissão técnica.
4. WHEN o Frontend carrega o perfil de um time, THE Frontend SHALL exibir simultaneamente: hero com logo, nome e cidade; KPIs da temporada (jogos, vitórias, empates, derrotas, gols pró, gols contra); últimos 5 resultados; campinho SVG com titulares posicionados; lista de reservas.
5. WHEN o Frontend está carregando dados de um time, THE Frontend SHALL exibir um skeleton animado no lugar do conteúdo até que os dados estejam disponíveis.
6. THE Frontend SHALL inferir a formação tática (ex: 4-3-3) a partir das posições dos 11 titulares e exibi-la no cabeçalho do campinho.
7. THE Frontend SHALL posicionar cada titular no campinho SVG de acordo com sua posição ESPN, usando coordenadas x/y pré-definidas por posição.
8. THE Frontend SHALL colorir cada jogador no campinho de acordo com seu grupo posicional (Goleiro: verde, Defensor: azul, Meio-campo: roxo, Atacante: laranja).
9. IF um time não tiver partidas finalizadas, THEN THE Frontend SHALL exibir a mensagem "Sem partidas finalizadas" na seção de últimos resultados.
10. IF o logo de um time não puder ser carregado, THEN THE Frontend SHALL ocultar o elemento de imagem sem quebrar o layout.

---

### Requisito 4: Ranking de Scouting por Posição

**User Story:** Como scout, quero visualizar um ranking de jogadores por posição com scores
normalizados, para que eu possa identificar rapidamente os melhores jogadores em cada função.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /scout/ranking que aceita competition_id, position e min_minutes como parâmetros e retorna a lista de jogadores ranqueados por score decrescente.
2. IF a position fornecida não for uma das posições válidas (Goleiro, Defensor, Meio-campo, Atacante), THEN THE API SHALL retornar HTTP 400 com mensagem descritiva.
3. THE Scout_Engine SHALL calcular métricas p90 para cada jogador elegível (total de minutos ≥ min_minutes) dentro do grupo posicional.
4. THE Scout_Engine SHALL normalizar cada métrica de 0 a 100 usando min-max normalization entre todos os jogadores elegíveis do mesmo grupo posicional.
5. WHEN todas as métricas de um grupo posicional têm o mesmo valor para todos os jogadores, THE Scout_Engine SHALL atribuir score 50 para todos os jogadores daquele grupo.
6. THE Scout_Engine SHALL calcular o Score final como a média aritmética dos scores normalizados de todas as métricas do grupo posicional.
7. THE Scout_Engine SHALL inverter a normalização de métricas negativas (fouls_p90, yellow_cards_p90, red_cards_p90, goals_conceded_p90) para que valores menores resultem em scores maiores.
8. THE Dashboard SHALL exibir o ranking em uma tabela com highlight ouro (1º), prata (2º) e bronze (3º) nas três primeiras linhas.
9. THE Dashboard SHALL exibir o ícone 🔍 ao lado do nome de jogadores classificados como Joia Escondida (Score ≥ 60 e total de minutos ≤ 270).
10. WHEN o usuário altera os filtros de competição, posição ou mínimo de minutos no Dashboard, THE Dashboard SHALL recarregar o ranking com os novos parâmetros.

---

### Requisito 5: Card de Jogador com Radar Chart

**User Story:** Como scout, quero visualizar o card detalhado de um jogador com radar chart
e métricas brutas, para que eu possa avaliar sua performance em profundidade.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /scout/player/{player_id} que aceita competition_id e min_minutes e retorna o card completo do jogador incluindo score, rank, métricas e dados de identificação.
2. IF o jogador não tiver posição mapeável para um grupo posicional, THEN THE API SHALL retornar HTTP 422 com mensagem descritiva.
3. IF o jogador não aparecer no ranking (minutos insuficientes ou sem estatísticas), THEN THE API SHALL retornar HTTP 404 com mensagem descritiva.
4. THE Dashboard SHALL exibir o card do jogador com: nome, time, posição, score, minutos jogados, número de partidas, radar chart e tabela de métricas brutas.
5. THE Dashboard SHALL renderizar o radar chart usando Plotly com os valores normalizados de 0 a 100 para o eixo radial.
6. WHEN o Score do jogador for ≥ 60 e o total de minutos for ≤ 270, THE Dashboard SHALL exibir o badge "🔍 Joia Escondida" no card.
7. WHEN o usuário clica em "← Voltar" no card do jogador, THE Dashboard SHALL retornar para a página de ranking mantendo os filtros anteriores.
8. WHEN o usuário seleciona um jogador no selectbox da sidebar do Dashboard, THE Dashboard SHALL navegar para o card daquele jogador.

---

### Requisito 6: Analytics de Jogador

**User Story:** Como analista, quero acessar dados analíticos detalhados de um jogador
via API, para que eu possa construir visualizações e relatórios customizados.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /players/{player_id}/analytics/summary que retorna médias de todas as métricas disponíveis para uma janela configurável de partidas.
2. THE API SHALL expor um endpoint GET /players/{player_id}/analytics/radar que retorna scores normalizados de 0 a 100 para cada métrica, comparando o jogador com todos os jogadores elegíveis da competição.
3. THE API SHALL expor um endpoint GET /players/{player_id}/analytics/timeseries que retorna os valores de cada métrica por rodada, ordenados por número de rodada crescente.
4. WHEN o número de jogadores elegíveis for menor que min_players (padrão: 30), THE Player_Analytics SHALL retornar todos os scores de métricas como null com note "insufficient sample".
5. IF o player_id fornecido não existir na competition_id especificada, THEN THE API SHALL retornar HTTP 404 com mensagem "Player not found in competition".

---

### Requisito 7: Analytics de Time

**User Story:** Como analista, quero acessar dados analíticos detalhados de um time
via API, para que eu possa avaliar tendências de performance ao longo da temporada.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /teams/{team_id}/analytics/summary que retorna médias de estatísticas do time, tendência de forma e lista das últimas partidas para uma janela configurável.
2. THE API SHALL expor um endpoint GET /teams/{team_id}/analytics/radar que retorna scores normalizados de 0 a 100 para cada métrica do time, comparando com todos os times elegíveis da competição.
3. THE API SHALL expor um endpoint GET /teams/{team_id}/analytics/timeseries que retorna os valores de cada métrica por rodada para o time.
4. WHEN o número de times elegíveis for menor que min_teams (padrão: 6), THE Team_Analytics SHALL retornar todos os scores de métricas como null com note "insufficient sample".
5. IF o team_id fornecido não existir na competition_id especificada, THEN THE API SHALL retornar HTTP 404 com mensagem "Team not found in competition".

---

### Requisito 8: Dados de Partidas

**User Story:** Como desenvolvedor de integrações, quero acessar dados completos de partidas
via API, para que eu possa construir funcionalidades baseadas em resultados e estatísticas.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /matches que aceita competition_id e retorna todas as partidas da competição ordenadas por data/hora crescente.
2. THE API SHALL expor um endpoint GET /matches/{match_id} que retorna os detalhes de uma partida incluindo times mandante e visitante.
3. THE API SHALL expor um endpoint GET /matches/{match_id}/stats que retorna as estatísticas de time para uma partida, com o time mandante listado primeiro.
4. IF o match_id fornecido não existir, THEN THE API SHALL retornar HTTP 404 com mensagem "Match not found".
5. THE API SHALL incluir nos dados de partida: id, competition_id, round_number, match_date_time, status, score_home, score_away, home_team e away_team.

---

### Requisito 9: Perfil de Jogador

**User Story:** Como scout, quero acessar o perfil completo de um jogador via API,
para que eu possa obter informações biográficas e de identificação.

#### Critérios de Aceitação

1. THE API SHALL expor um endpoint GET /players/{player_id} que retorna os dados completos do jogador incluindo nome, posição, número de camisa, data de nascimento, nacionalidade, foto, altura e pé preferido.
2. THE API SHALL incluir nos dados do jogador o nome e id do time ao qual pertence.
3. IF o player_id fornecido não existir, THEN THE API SHALL retornar HTTP 404 com mensagem "Player not found".

---

### Requisito 10: Infraestrutura e Operação

**User Story:** Como operador, quero que o sistema seja executável localmente via Docker
e deployável em produção, para que o ambiente seja reproduzível e o deploy seja previsível.

#### Critérios de Aceitação

1. THE API SHALL aceitar requisições de qualquer origem (CORS allow_origins=["*"]) para permitir acesso do Frontend estático e do Dashboard.
2. THE Frontend SHALL ser configurável via constante API_BASE no topo do script para apontar para diferentes ambientes (local, produção).
3. THE infra SHALL fornecer um docker-compose.yml que suba o banco PostgreSQL e a API com um único comando.
4. THE API SHALL executar migrações Alembic para manter o schema do banco atualizado.
5. WHEN o Frontend é deployado no Cloudflare Pages, THE Frontend SHALL funcionar como arquivo estático sem dependência de servidor de aplicação.
6. THE Dashboard SHALL ser executável localmente com `streamlit run dashboard/app.py` apontando para a API via variável API_BASE.

---

### Requisito 11: Lacunas Identificadas — Autenticação e Segurança

**User Story:** Como operador de produção, quero que o sistema tenha controles básicos de
acesso, para que dados sensíveis de scouting não sejam expostos publicamente sem restrição.

#### Critérios de Aceitação

1. WHERE autenticação estiver habilitada, THE API SHALL exigir um token de API válido no header Authorization para todos os endpoints de scout e analytics.
2. WHERE autenticação estiver habilitada, THE API SHALL retornar HTTP 401 para requisições sem token válido.
3. THE API SHALL restringir CORS allow_origins a domínios específicos em ambiente de produção, em vez de aceitar qualquer origem.

---

### Requisito 12: Lacunas Identificadas — Paginação e Performance

**User Story:** Como desenvolvedor, quero que endpoints que retornam listas grandes suportem
paginação, para que a API não retorne payloads excessivos conforme o volume de dados cresce.

#### Critérios de Aceitação

1. THE API SHALL suportar parâmetros limit e offset no endpoint GET /matches para paginar resultados.
2. THE API SHALL suportar parâmetros limit e offset no endpoint GET /scout/ranking para paginar resultados.
3. WHEN limit não for fornecido, THE API SHALL usar um valor padrão de 100 itens por página.

---

### Requisito 13: Lacunas Identificadas — Tratamento de Erros no Frontend

**User Story:** Como usuário do Frontend, quero receber feedback claro quando a API estiver
indisponível ou retornar erros, para que eu entenda o que aconteceu e não fique com a tela travada.

#### Critérios de Aceitação

1. IF a API retornar erro ao carregar o perfil de um time, THEN THE Frontend SHALL exibir uma mensagem de erro visível na área de conteúdo principal.
2. IF a API estiver indisponível ao inicializar, THEN THE Frontend SHALL exibir uma mensagem de erro na sidebar indicando que os times não puderam ser carregados.
3. THE Frontend SHALL exibir o skeleton de carregamento por no máximo 10 segundos antes de exibir mensagem de timeout.
