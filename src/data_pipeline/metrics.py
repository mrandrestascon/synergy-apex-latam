"""
Mathematically correct metric calculations with documented denominators.
No magic numbers. Every formula is explicit and testable.
"""
from __future__ import annotations
from typing import Optional
import math


# ── CAGR ──────────────────────────────────────────────────────────────────

def cagr(start: float, end: float, years: int) -> Optional[float]:
    """
    Compound Annual Growth Rate.

    Formula: (end / start) ^ (1 / years) - 1

    Returns None if inputs are invalid (negative, zero, or years < 1).
    Returns a decimal (0.075 = 7.5%). Caller multiplies by 100 for display.
    """
    if years < 1:
        raise ValueError(f"years must be >= 1, got {years}")
    if start is None or end is None:
        return None
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def cagr_pct(start: float, end: float, years: int, decimals: int = 2) -> Optional[float]:
    """CAGR as a percentage, rounded to `decimals` places."""
    rate = cagr(start, end, years)
    if rate is None:
        return None
    return round(rate * 100, decimals)


def cagr_series(series: list[float], years: Optional[int] = None) -> Optional[float]:
    """
    CAGR from a time series (list of values, oldest first).
    Uses first and last non-None values.
    years defaults to len(series) - 1.
    """
    valid = [(i, v) for i, v in enumerate(series) if v is not None and v > 0]
    if len(valid) < 2:
        return None
    i_start, v_start = valid[0]
    i_end,   v_end   = valid[-1]
    n = years if years is not None else (i_end - i_start)
    if n < 1:
        return None
    return cagr_pct(v_start, v_end, n)


# ── Market share ───────────────────────────────────────────────────────────

def market_share(
    bank_value: float,
    all_actors: list[dict],
    value_field: str = "acm",
    country: Optional[str] = None,
) -> Optional[float]:
    """
    Market share of one bank within its country's system.

    Denominator: SUM(value_field) for all actors in the same country.
    If `country` is provided, filters actors list to that country first.

    Returns a percentage (0–100), rounded to 2 decimal places.
    """
    pool = all_actors
    if country:
        pool = [a for a in all_actors if a.get("country") == country]
    total = sum(a.get(value_field, 0) or 0 for a in pool)
    if total <= 0:
        return None
    return round(bank_value / total * 100, 2)


def recalculate_market_shares(
    actors: list[dict],
    value_field: str = "acm",
) -> list[dict]:
    """
    Recalculate market_share for every actor in a list, grouped by country.
    Returns the same list with `cuota_mercado` updated in-place.
    Guarantees shares sum to 100% within each country.
    """
    # Build country totals
    totals: dict[str, float] = {}
    for a in actors:
        c = a.get("country", "")
        totals[c] = totals.get(c, 0) + (a.get(value_field, 0) or 0)

    for a in actors:
        c = a.get("country", "")
        total = totals.get(c, 0)
        if total > 0:
            a["cuota_mercado"] = round(a.get(value_field, 0) / total * 100, 2)
        else:
            a["cuota_mercado"] = None

    return actors


# ── Validation helpers ─────────────────────────────────────────────────────

def verify_shares_sum_to_100(actors: list[dict], country: str, tolerance: float = 0.1) -> bool:
    """Returns True if market shares for a country sum to ~100%."""
    shares = [a["cuota_mercado"] for a in actors if a.get("country") == country and a.get("cuota_mercado") is not None]
    if not shares:
        return False
    total = sum(shares)
    return abs(total - 100.0) <= tolerance


def deposit_total(actors: list[dict], country: str) -> dict[str, float]:
    """Aggregate vista, plazo, acm for a country from actors list."""
    pool = [a for a in actors if a.get("country") == country]
    return {
        "depositos_vista":  sum(a.get("depositos_vista", 0) or 0 for a in pool),
        "depositos_plazo":  sum(a.get("depositos_plazo", 0) or 0 for a in pool),
        "acm":              sum(a.get("acm", 0) or 0 for a in pool),
    }
