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

    for p in players:
        norms = p.get("_norm", {})
        p["score"] = round(sum(norms.values()) / len(norms), 1) if norms else 0.0
        p["metrics"] = norms
        del p["_norm"]

    return sorted(players, key=lambda x: x["score"], reverse=True)


def get_scout_ranking(position_group: str, min_minutes: int = 180, season: str = "2026") -> list[dict]:
    pos = POSITION_MAP.get(position_group, position_group.upper())
    if pos not in METRICS_BY_POSITION:
        raise ValueError(f"Posição inválida: {position_group}. Use GK, DEF, MID, FWD ou equivalente em PT.")

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
