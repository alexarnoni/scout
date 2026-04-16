import math
from statistics import mean, stdev

from ..providers.sportdb_scout import get_player_season_stats

POSITION_MAP = {
    "GKP": "GK",
    "DEF": "DEF",
    "MID": "MID",
    "FWD": "FWD",
    "Goalkeeper": "GK",
    "Defender": "DEF",
    "Midfielder": "MID",
    "Forward": "FWD",
    # português
    "Goleiro": "GK",
    "Defensor": "DEF",
    "Meio-campo": "MID",
    "Atacante": "FWD",
}

METRICS_BY_POSITION = {
    "GK":  ["save_rate", "avg_rating", "goals_p90_inv", "yellow_cards_p90_inv"],
    "DEF": ["goals_p90", "assists_p90", "shots_p90", "fouls_p90_inv", "yellow_cards_p90_inv", "avg_rating"],
    "MID": ["goals_p90", "assists_p90", "shots_p90", "shots_on_target_p90", "fouls_p90_inv", "yellow_cards_p90_inv", "avg_rating"],
    "FWD": ["goals_p90", "assists_p90", "shots_p90", "shots_on_target_p90", "conversion_rate", "xg_p90", "yellow_cards_p90_inv", "avg_rating"],
}

# Alias com nomes em português para compatibilidade com testes
GROUP_METRICS = {
    "Goleiro": METRICS_BY_POSITION["GK"],
    "Defensor": METRICS_BY_POSITION["DEF"],
    "Meio-campo": METRICS_BY_POSITION["MID"],
    "Atacante": METRICS_BY_POSITION["FWD"],
}


def _p90(value: float, minutes: float) -> float:
    """Calcula valor por 90 minutos."""
    if not minutes:
        return 0.0
    return value / (minutes / 90)


def _normalize(values: list[float], inverted: bool = False) -> list[float]:
    """Normaliza uma lista de valores para o intervalo 0-100 via min-max.
    Se todos os valores forem iguais, retorna 50.0 para todos.
    Se inverted=True, inverte a escala (100 - norm).
    """
    min_v = min(values)
    max_v = max(values)
    rng = max_v - min_v
    if rng == 0:
        return [50.0] * len(values)
    result = [(v - min_v) / rng * 100 for v in values]
    if inverted:
        result = [100.0 - v for v in result]
    return result


def _normalize_group(players: list[dict], metrics: list[str]) -> list[dict]:
    """Normaliza métricas 0-100 por min-max dentro do grupo."""
    for metric in metrics:
        base = metric.replace("_inv", "")
        values = [p.get(base, 0) for p in players]
        min_v, max_v = min(values), max(values)
        rng = max_v - min_v or 1  # evita divisão por zero
        for p in players:
            raw = p.get(base, 0)
            norm = (raw - min_v) / rng * 100
            if metric.endswith("_inv"):
                norm = 100 - norm
            p.setdefault("_norm", {})[metric] = round(norm, 1)

    max_minutes = max(p.get("total_minutes", 0) for p in players) or 1
    for p in players:
        norms = p.get("_norm", {})
        score_raw = round(sum(norms.values()) / len(norms), 1) if norms else 0.0
        confidence = p.get("total_minutes", 0) / max_minutes
        p["score"] = round(score_raw * confidence, 1)
        p["metrics"] = norms
        del p["_norm"]

    return sorted(players, key=lambda x: x["score"], reverse=True)


def get_scout_ranking(position_group: str, min_minutes: int = 180, season: str = "2026") -> list[dict]:
    pos = POSITION_MAP.get(position_group, position_group.upper() if position_group else "")
    if pos not in METRICS_BY_POSITION:
        return []

    all_players = get_player_season_stats(season)

    # Filtra por posição e minutos mínimos
    group = [
        p for p in all_players
        if POSITION_MAP.get(p["position"], p["position"]) == pos
        and p["total_minutes"] >= min_minutes
    ]

    if not group:
        return []

    metrics = METRICS_BY_POSITION[pos]
    ranked = _normalize_group(group, metrics)

    # Adiciona rank e "joia escondida" (top 25% score, bottom 25% minutos)
    minutes_values = sorted([p["total_minutes"] for p in ranked])
    minutes_p25 = minutes_values[len(minutes_values) // 4] if minutes_values else 0
    score_p75 = sorted([p["score"] for p in ranked])[int(len(ranked) * 0.75)] if ranked else 0

    for i, p in enumerate(ranked):
        p["rank"] = i + 1
        p["is_hidden_gem"] = p["score"] >= score_p75 and p["total_minutes"] <= minutes_p25

    return ranked


MARKET_VALUE_FLOOR = 100_000  # €100K — mínimo realista para Série A


def compute_garimpo(players: list[dict]) -> list[dict]:
    """
    Calcula o Garimpo (z-score dual) para uma lista de jogadores já ranqueados.
    Cada jogador no input deve ter: score (float), market_value_m (float|None).
    Jogadores sem market_value_m são incluídos com garimpo_score=None.

    Fórmula:
        z_perf  = (score - mean(scores)) / stdev(scores)
        z_valor = (log(mv) - mean(log_mvs)) / stdev(log_mvs)
        garimpo = z_perf - z_valor

    O log comprime a escala de valor de mercado.
    A subtração mede a desconexão: performance acima da média MENOS custo acima da média.
    """
    # Separa jogadores com e sem valor de mercado
    with_mv = [p for p in players if p.get("market_value_m") and p["market_value_m"] > 0]
    without_mv = [p for p in players if not p.get("market_value_m") or p["market_value_m"] <= 0]

    if len(with_mv) < 3:  # Grupo muito pequeno — z-score não faz sentido
        for p in players:
            p["garimpo_score"] = None
        return sorted(players, key=lambda x: x.get("score", 0), reverse=True)

    scores = [p["score"] for p in with_mv]
    log_mvs = [math.log(max(p["market_value_m"] * 1_000_000, MARKET_VALUE_FLOOR)) for p in with_mv]

    scores_mean = mean(scores)
    scores_std  = stdev(scores) if len(scores) > 1 else 1.0
    mvs_mean    = mean(log_mvs)
    mvs_std     = stdev(log_mvs) if len(log_mvs) > 1 else 1.0

    # Proteção contra std=0 (todos iguais)
    if scores_std == 0:
        scores_std = 1.0
    if mvs_std == 0:
        mvs_std = 1.0

    for p in with_mv:
        z_perf  = (p["score"] - scores_mean) / scores_std
        log_mv  = math.log(max(p["market_value_m"] * 1_000_000, MARKET_VALUE_FLOOR))
        z_valor = (log_mv - mvs_mean) / mvs_std
        p["garimpo_score"] = round(z_perf - z_valor, 2)

    for p in without_mv:
        p["garimpo_score"] = None

    all_players = with_mv + without_mv
    return sorted(
        all_players,
        key=lambda x: (x["garimpo_score"] is None, -(x["garimpo_score"] or 0)),
    )
