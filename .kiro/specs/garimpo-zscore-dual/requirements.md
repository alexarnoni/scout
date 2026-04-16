# Documento de Requisitos

## Introdução

Substituição da fórmula simples do Garimpo (`score / market_value_in_millions`) por um modelo de z-score dual que mede a desconexão entre performance e preço de mercado no sistema de scouting "Olheiro" para o Brasileirão Série A 2026. O novo modelo calcula z-scores independentes para performance (score) e valor de mercado (log-transformado), e o garimpo final é a diferença `z_perf - z_valor`, identificando jogadores que performam acima do que seu preço sugere.

## Glossário

- **Sistema_Garimpo**: Módulo responsável pelo cálculo do índice garimpo via z-score dual, implementado na função `compute_garimpo` em `backend/app/services/scout.py`
- **Endpoint_Moneyball**: Endpoint HTTP `GET /scout/moneyball` em `backend/app/main.py` que orquestra o cálculo do garimpo e retorna os resultados ao frontend
- **Frontend_Garimpo**: Seção da interface `frontend/index.html` que exibe a aba Garimpo com ranking, cores e textos explicativos
- **z_perf**: Z-score de performance — `(score - média_scores) / desvio_padrão_scores`
- **z_valor**: Z-score de valor de mercado — `(log(mv) - média_log_mvs) / desvio_padrão_log_mvs`
- **garimpo_score**: Índice final calculado como `z_perf - z_valor`
- **MARKET_VALUE_FLOOR**: Constante de piso mínimo de valor de mercado, fixada em €100.000 (100_000)
- **Ranking_Scout**: Lista de jogadores ranqueados por posição retornada por `get_scout_ranking`

## Requisitos

### Requisito 1: Função compute_garimpo — Cálculo do z-score dual

**User Story:** Como analista de futebol, eu quero que o índice garimpo use z-scores de performance e valor de mercado, para que eu identifique com precisão estatística jogadores que performam acima do que seu preço sugere.

#### Critérios de Aceitação

1. WHEN o Sistema_Garimpo recebe uma lista de jogadores com scores e valores de mercado, THE Sistema_Garimpo SHALL calcular z_perf como `(score - média_scores) / desvio_padrão_scores` para cada jogador que possui valor de mercado
2. WHEN o Sistema_Garimpo recebe uma lista de jogadores com valores de mercado, THE Sistema_Garimpo SHALL calcular z_valor como `(log(mv) - média_log_mvs) / desvio_padrão_log_mvs` usando logaritmo natural dos valores de mercado
3. WHEN z_perf e z_valor são calculados para um jogador, THE Sistema_Garimpo SHALL atribuir garimpo_score como `z_perf - z_valor`
4. THE Sistema_Garimpo SHALL aplicar MARKET_VALUE_FLOOR de 100_000 (€100K) como valor mínimo de mercado antes do cálculo logarítmico
5. WHEN um jogador não possui market_value_m (valor nulo ou ausente), THE Sistema_Garimpo SHALL atribuir garimpo_score igual a None para esse jogador
6. WHEN menos de 3 jogadores no grupo possuem valor de mercado válido, THE Sistema_Garimpo SHALL atribuir garimpo_score igual a None para todos os jogadores do grupo
7. WHEN o desvio padrão dos scores ou dos log-valores é igual a zero, THE Sistema_Garimpo SHALL atribuir garimpo_score igual a None para todos os jogadores do grupo
8. THE Sistema_Garimpo SHALL retornar a lista de jogadores ordenada por garimpo_score em ordem decrescente, com jogadores sem garimpo_score (None) posicionados ao final

### Requisito 2: Refatoração do endpoint /scout/moneyball

**User Story:** Como desenvolvedor do backend, eu quero que o endpoint moneyball use a nova função compute_garimpo e processe todos os jogadores do grupo, para que o cálculo estatístico tenha uma amostra representativa.

#### Critérios de Aceitação

1. WHEN o Endpoint_Moneyball recebe uma requisição válida, THE Endpoint_Moneyball SHALL processar todos os jogadores retornados pelo Ranking_Scout sem limitar a 20 registros
2. WHEN o Endpoint_Moneyball calcula o garimpo, THE Endpoint_Moneyball SHALL usar a função compute_garimpo do Sistema_Garimpo em vez da fórmula `score / mv_num`
3. THE Endpoint_Moneyball SHALL retornar o campo `garimpo_score` em vez de `moneyball_score` em cada registro da resposta
4. THE Endpoint_Moneyball SHALL retornar os resultados ordenados por garimpo_score em ordem decrescente

### Requisito 3: Atualização do frontend — campo e referências

**User Story:** Como usuário do Olheiro, eu quero que a interface reflita o novo modelo z-score dual com nomenclatura e formatação adequadas, para que eu entenda o significado dos valores exibidos.

#### Critérios de Aceitação

1. WHEN o Frontend_Garimpo recebe dados do Endpoint_Moneyball, THE Frontend_Garimpo SHALL usar o campo `garimpo_score` em vez de `moneyball_score` para exibição e ordenação
2. WHEN o garimpo_score de um jogador é maior ou igual a 1.5, THE Frontend_Garimpo SHALL exibir o valor na cor accent (var(--accent))
3. WHEN o garimpo_score de um jogador é maior ou igual a 0.5 e menor que 1.5, THE Frontend_Garimpo SHALL exibir o valor na cor draw (var(--draw))
4. WHEN o garimpo_score de um jogador é menor que 0, THE Frontend_Garimpo SHALL exibir o valor na cor loss (var(--loss))
5. WHEN o garimpo_score de um jogador é maior ou igual a 0 e menor que 0.5, THE Frontend_Garimpo SHALL exibir o valor na cor text-secondary (var(--text-secondary))
6. THE Frontend_Garimpo SHALL formatar o garimpo_score com sinal explícito (prefixo "+" para valores positivos, "-" implícito para negativos)
7. THE Frontend_Garimpo SHALL exibir o subtítulo da aba como "z-score dual · performance vs. preço" em vez de "score ÷ valor de mercado"
8. THE Frontend_Garimpo SHALL exibir o cabeçalho da coluna como "⛏️ Garimpo" em vez de "⛏️ Score"
9. THE Frontend_Garimpo SHALL atualizar o texto explicativo do info box para descrever o modelo z-score dual

### Requisito 4: Preservação de funcionalidades existentes

**User Story:** Como desenvolvedor, eu quero garantir que as funções existentes do scout não sejam alteradas, para que o sistema mantenha compatibilidade e os testes existentes continuem passando.

#### Critérios de Aceitação

1. THE Sistema_Garimpo SHALL preservar as funções get_scout_ranking, get_player_season_stats, _normalize_group e get_player_market_value sem modificações
2. THE Sistema_Garimpo SHALL preservar todos os testes existentes em test_scout_service.py e test_scout_confidence_penalty.py sem alterações

### Requisito 5: Testes da função compute_garimpo

**User Story:** Como desenvolvedor, eu quero testes unitários abrangentes para a função compute_garimpo, para que eu tenha confiança na correção do cálculo z-score dual.

#### Critérios de Aceitação

1. WHEN um jogador tem score alto e valor de mercado baixo, THE teste SHALL verificar que esse jogador lidera o ranking de garimpo_score
2. WHEN um jogador tem score alto e valor de mercado alto (estrela cara), THE teste SHALL verificar que o garimpo_score desse jogador é próximo de zero
3. WHEN um jogador não possui valor de mercado, THE teste SHALL verificar que garimpo_score é None
4. WHEN menos de 3 jogadores possuem valor de mercado, THE teste SHALL verificar que todos recebem garimpo_score igual a None
5. WHEN todos os jogadores possuem o mesmo score e o mesmo valor de mercado, THE teste SHALL verificar que todos recebem garimpo_score igual a None (desvio padrão zero)
6. THE teste SHALL verificar que a lista retornada está ordenada por garimpo_score em ordem decrescente
7. WHEN um jogador possui valor de mercado abaixo de €100K, THE teste SHALL verificar que o MARKET_VALUE_FLOOR de 100_000 é aplicado antes do cálculo logarítmico
8. FOR ALL listas válidas de jogadores com pelo menos 3 valores de mercado distintos e desvio padrão não-zero, o cálculo de garimpo_score SHALL satisfazer a propriedade round-trip: `garimpo_score == z_perf - z_valor` onde z_perf e z_valor são calculados independentemente a partir dos dados de entrada
