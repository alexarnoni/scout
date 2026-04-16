"""Testes para compute_garimpo (z-score dual)."""
from app.services.scout import compute_garimpo


def _player(name, score, mv_m):
    return {"player_name": name, "score": score, "market_value_m": mv_m}


class TestComputeGarimpo:
    def test_high_score_low_value_leads(self):
        """Jogador com score alto e valor baixo deve ter garimpo maior."""
        players = [
            _player("Barato Bom", 75, 0.2),
            _player("Caro Bom", 80, 8.0),
            _player("Barato Ruim", 30, 0.15),
        ]
        result = compute_garimpo(players)
        garimpos = {p["player_name"]: p["garimpo_score"] for p in result}
        assert garimpos["Barato Bom"] > garimpos["Caro Bom"]

    def test_expensive_star_near_zero(self):
        """Jogador caro com score alto deve ter garimpo próximo de zero."""
        players = [
            _player("Estrela", 85, 10.0),
            _player("Normal A", 50, 1.0),
            _player("Normal B", 55, 1.5),
            _player("Normal C", 45, 0.8),
        ]
        result = compute_garimpo(players)
        estrela = next(p for p in result if p["player_name"] == "Estrela")
        assert result[0]["player_name"] != "Estrela" or abs(estrela["garimpo_score"]) < 1.0

    def test_no_mv_gets_none(self):
        """Jogadores sem valor de mercado recebem garimpo_score=None."""
        players = [
            _player("Com MV", 60, 1.0),
            _player("Sem MV", 70, None),
            _player("Outro", 50, 0.5),
        ]
        result = compute_garimpo(players)
        sem_mv = next(p for p in result if p["player_name"] == "Sem MV")
        assert sem_mv["garimpo_score"] is None

    def test_too_few_players_returns_none(self):
        """Com menos de 3 jogadores com MV, garimpo=None para todos."""
        players = [
            _player("A", 60, 1.0),
            _player("B", 70, None),
        ]
        result = compute_garimpo(players)
        assert all(p["garimpo_score"] is None for p in result)

    def test_all_same_score_same_value(self):
        """Todos iguais → garimpo 0.0 para todos."""
        players = [
            _player("A", 50, 1.0),
            _player("B", 50, 1.0),
            _player("C", 50, 1.0),
        ]
        result = compute_garimpo(players)
        for p in result:
            assert p["garimpo_score"] == 0.0

    def test_sorted_by_garimpo_desc(self):
        """Resultado deve estar ordenado por garimpo_score descendente."""
        players = [
            _player("A", 80, 0.2),
            _player("B", 40, 5.0),
            _player("C", 60, 1.0),
        ]
        result = compute_garimpo(players)
        scores = [p["garimpo_score"] for p in result if p["garimpo_score"] is not None]
        assert scores == sorted(scores, reverse=True)

    def test_floor_applied(self):
        """Valor de mercado abaixo de 100K deve ser tratado como 100K."""
        players = [
            _player("Gratis", 60, 0.01),  # 10K → floor 100K
            _player("Normal", 60, 1.0),
            _player("Caro", 60, 5.0),
        ]
        result = compute_garimpo(players)
        gratis = next(p for p in result if p["player_name"] == "Gratis")
        assert gratis["garimpo_score"] is not None
        assert gratis["garimpo_score"] < 5.0  # sanity check


# ---------------------------------------------------------------------------
# Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------
import math
from statistics import mean, stdev as sample_stdev

from hypothesis import given, settings, assume
from hypothesis import strategies as st


def _player_st(name_prefix="P"):
    """Strategy para gerar um jogador com score e market_value_m opcionais."""
    return st.fixed_dictionaries({
        "player_name": st.text(min_size=1, max_size=8),
        "score": st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        "market_value_m": st.one_of(
            st.none(),
            st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        ),
    })


class TestPropertyRoundTrip:
    """Property 1: Round-trip do garimpo_score.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 5.8**
    """

    @given(
        data=st.lists(
            st.tuples(
                st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
                st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
            ),
            min_size=3,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_garimpo_equals_zperf_minus_zvalor(self, data):
        """garimpo_score deve ser ≈ z_perf - z_valor calculados independentemente."""
        # Build players with unique names so we can match them after sorting
        players = [
            {"player_name": f"P{i}", "score": score, "market_value_m": mv}
            for i, (score, mv) in enumerate(data)
        ]

        scores = [p["score"] for p in players]
        log_mvs = [math.log(max(p["market_value_m"] * 1_000_000, 100_000)) for p in players]

        # Need variation for the test to be meaningful
        assume(len(set(scores)) > 1 or len(scores) >= 3)
        assume(len(set(log_mvs)) > 1 or len(log_mvs) >= 3)

        # Keep originals indexed by name before mutation
        originals = {p["player_name"]: dict(p) for p in players}

        result = compute_garimpo([dict(p) for p in players])

        # Calculate z-scores independently using statistics.stdev (sample, N-1)
        scores_mean = mean(scores)
        scores_std = sample_stdev(scores) if len(scores) > 1 else 1.0
        if scores_std == 0:
            scores_std = 1.0

        mvs_mean = mean(log_mvs)
        mvs_std = sample_stdev(log_mvs) if len(log_mvs) > 1 else 1.0
        if mvs_std == 0:
            mvs_std = 1.0

        for p_result in result:
            if p_result["garimpo_score"] is None:
                continue
            orig = originals[p_result["player_name"]]
            z_perf = (orig["score"] - scores_mean) / scores_std
            log_mv = math.log(max(orig["market_value_m"] * 1_000_000, 100_000))
            z_valor = (log_mv - mvs_mean) / mvs_std
            expected = round(z_perf - z_valor, 2)
            assert abs(p_result["garimpo_score"] - expected) <= 0.01, (
                f"Player {p_result['player_name']}: got {p_result['garimpo_score']}, expected {expected}"
            )


class TestPropertyNoneAttribution:
    """Property 2: Atribuição correta de None.

    **Validates: Requirements 1.5, 1.6, 1.7**
    """

    @given(
        players=st.lists(
            _player_st(),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_none_attribution_rules(self, players):
        """Jogadores sem mv → None; grupo com <3 mvs → todos None."""
        result = compute_garimpo([dict(p) for p in players])

        with_mv = [p for p in players if p.get("market_value_m") is not None and p["market_value_m"] > 0]

        if len(with_mv) < 3:
            # Todos devem ter garimpo_score = None
            for p in result:
                assert p["garimpo_score"] is None, (
                    f"Expected None for all when <3 have mv, got {p['garimpo_score']} for {p['player_name']}"
                )
        else:
            # Jogadores sem mv devem ter None
            for p in result:
                has_mv = p.get("market_value_m") is not None and p["market_value_m"] > 0
                if not has_mv:
                    assert p["garimpo_score"] is None, (
                        f"Player without mv should have None, got {p['garimpo_score']} for {p['player_name']}"
                    )


class TestPropertySortingInvariant:
    """Property 3: Invariante de ordenação.

    **Validates: Requirements 1.8, 2.4**
    """

    @given(
        players=st.lists(
            _player_st(),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_result_sorted_desc_none_at_end(self, players):
        """Resultado deve estar ordenado por garimpo_score desc, None ao final."""
        result = compute_garimpo([dict(p) for p in players])

        scores = [p["garimpo_score"] for p in result]

        # Separate non-None and None scores
        non_none = [s for s in scores if s is not None]
        none_indices = [i for i, s in enumerate(scores) if s is None]
        non_none_indices = [i for i, s in enumerate(scores) if s is not None]

        # All None values must be at the end
        if none_indices and non_none_indices:
            assert max(non_none_indices) < min(none_indices), (
                f"None values not at end: non_none_indices={non_none_indices}, none_indices={none_indices}"
            )

        # Non-None scores must be in descending order
        for i in range(len(non_none) - 1):
            assert non_none[i] >= non_none[i + 1], (
                f"Not sorted desc: {non_none[i]} < {non_none[i + 1]} at positions {i}, {i+1}"
            )
