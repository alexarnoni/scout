from __future__ import annotations

from decimal import Decimal


def to_float(value: int | float | Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def minmax_score(
    value: int | float | Decimal | None,
    min_val: int | float | Decimal | None,
    max_val: int | float | Decimal | None,
    invert: bool = False,
) -> float | None:
    value_f = to_float(value)
    min_f = to_float(min_val)
    max_f = to_float(max_val)
    if value_f is None or min_f is None or max_f is None:
        return None
    if max_f == min_f:
        score = 50.0
    else:
        denom = max_f - min_f
        if denom == 0:
            score = 50.0
        else:
            score = (value_f - min_f) / denom * 100.0
            score = max(0.0, min(100.0, score))
    if invert:
        score = 100.0 - score
    return round(score, 1)
