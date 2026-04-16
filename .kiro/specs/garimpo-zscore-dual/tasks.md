# Plano de Implementação: Garimpo Z-Score Dual

## Visão Geral

Implementação incremental do modelo z-score dual para o índice Garimpo no sistema Olheiro. A abordagem começa pela função core `compute_garimpo`, segue para a refatoração do endpoint, depois atualiza o frontend, e finaliza com validação de preservação dos testes existentes.

## Tasks

- [x] 1. Implementar a função `compute_garimpo` em `backend/app/services/scout.py`
  - [x] 1.1 Adicionar a constante `MARKET_VALUE_FLOOR = 100_000` e a função `compute_garimpo(players: list[dict]) -> list[dict]` ao final do arquivo `backend/app/services/scout.py`
    - Importar `math` no topo do arquivo
    - Implementar o algoritmo completo conforme o design: separar jogadores com/sem mv, threshold mínimo de 3, cálculo de z_perf e z_valor (log-transformado com floor), proteção stdev=0, atribuição de garimpo_score, ordenação decrescente com None ao final
    - Não modificar nenhuma função existente (`get_scout_ranking`, `_normalize_group`, `_normalize`, `_p90`)
    - _Requisitos: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 4.1_

  - [x]* 1.2 Escrever testes unitários para `compute_garimpo` em `backend/tests/test_garimpo.py`
    - Criar o arquivo `backend/tests/test_garimpo.py`
    - Teste 1: jogador score alto + mv baixo lidera o ranking (Req 5.1)
    - Teste 2: estrela cara (score alto + mv alto) tem garimpo_score ≈ 0 (Req 5.2)
    - Teste 3: jogador sem mv recebe None (Req 5.3)
    - Teste 4: menos de 3 com mv → todos None (Req 5.4)
    - Teste 5: stdev zero → todos None (Req 5.5)
    - Teste 6: resultado ordenado decrescente (Req 5.6)
    - Teste 7: MARKET_VALUE_FLOOR aplicado para mv < €100K (Req 5.7)
    - _Requisitos: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [x]* 1.3 Escrever teste property-based: Round-trip do garimpo_score
    - **Property 1: Round-trip do garimpo_score**
    - Adicionar ao arquivo `backend/tests/test_garimpo.py`
    - Gerar listas com pelo menos 3 jogadores com mv, scores e mvs não todos iguais
    - Verificar que `garimpo_score ≈ z_perf - z_valor` (tolerância 1e-9) calculados independentemente
    - Usar `@settings(max_examples=100)` com Hypothesis
    - **Validates: Requisitos 1.1, 1.2, 1.3, 1.4, 5.8**

  - [x]* 1.4 Escrever teste property-based: Atribuição correta de None
    - **Property 2: Atribuição correta de None**
    - Adicionar ao arquivo `backend/tests/test_garimpo.py`
    - Gerar listas com mix de `market_value_m = None` e valores válidos, incluindo cenários com <3 mvs e stdev=0
    - Verificar: jogadores sem mv → None; grupo com <3 mvs → todos None; stdev=0 → todos None
    - Usar `@settings(max_examples=100)` com Hypothesis
    - **Validates: Requisitos 1.5, 1.6, 1.7**

  - [x]* 1.5 Escrever teste property-based: Invariante de ordenação
    - **Property 3: Invariante de ordenação**
    - Adicionar ao arquivo `backend/tests/test_garimpo.py`
    - Gerar listas aleatórias de jogadores
    - Verificar que o resultado está ordenado por garimpo_score decrescente, com None ao final
    - Usar `@settings(max_examples=100)` com Hypothesis
    - **Validates: Requisitos 1.8, 2.4**

- [x] 2. Checkpoint — Validar função core e testes
  - Executar todos os testes em `backend/tests/test_garimpo.py`
  - Executar `backend/tests/test_scout_service.py` e `backend/tests/test_scout_confidence_penalty.py` para garantir que não quebraram
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Refatorar o endpoint `/scout/moneyball` em `backend/app/main.py`
  - [x] 3.1 Atualizar a função `scout_moneyball` em `backend/app/main.py`
    - Importar `compute_garimpo` de `app.services.scout`
    - Remover `ranking[:20]` → usar `ranking` completo (todos os jogadores)
    - Remover cálculo inline `score / mv_num` e a variável `moneyball`
    - Montar lista `result` com `score`, `market_value`, `market_value_m` e demais campos (sem `moneyball_score`)
    - Chamar `compute_garimpo(result)` para calcular e ordenar
    - Remover `result.sort(...)` manual (compute_garimpo já retorna ordenado)
    - O campo de saída será `garimpo_score` (adicionado por compute_garimpo) em vez de `moneyball_score`
    - _Requisitos: 2.1, 2.2, 2.3, 2.4_

- [x] 4. Atualizar o frontend em `frontend/index.html`
  - [x] 4.1 Atualizar a função `loadGarimpo` em `frontend/index.html`
    - Substituir `p.moneyball_score` → `p.garimpo_score` no filter e sort
    - Nova lógica de cor: `>= 1.5` → `var(--accent)`, `>= 0.5` → `var(--draw)`, `< 0` → `var(--loss)`, else → `var(--text-secondary)`
    - Formatação com sinal explícito: `+1.23` / `-0.45` (prefixo "+" para positivos)
    - Subtítulo: trocar `"score ÷ valor de mercado"` → `"z-score dual · performance vs. preço"`
    - Cabeçalho da coluna: trocar `"⛏️ Score"` → `"⛏️ Garimpo"`
    - Atualizar texto do info box para descrever o modelo z-score dual
    - Filtrar jogadores com `garimpo_score !== null && garimpo_score !== undefined` em vez de truthy check
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

- [x] 5. Checkpoint final — Validar tudo
  - Executar todos os testes em `backend/tests/test_garimpo.py`
  - Executar `backend/tests/test_scout_service.py` e `backend/tests/test_scout_confidence_penalty.py` para confirmar preservação
  - Ensure all tests pass, ask the user if questions arise.
  - _Requisitos: 4.1, 4.2_

## Notas

- Tasks marcadas com `*` são opcionais e podem ser puladas para um MVP mais rápido
- Cada task referencia requisitos específicos para rastreabilidade
- Checkpoints garantem validação incremental
- Property tests validam propriedades universais de correção
- Testes unitários validam exemplos específicos e edge cases
- A linguagem de implementação é Python (backend) e JavaScript (frontend), conforme o código existente
