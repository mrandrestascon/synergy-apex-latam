"""
Data quality validators. All rules are explicit and documented.
Every check returns a ValidationResult — never silently passes bad data.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    passed: bool
    field: str
    country: str
    value: Optional[float]
    rule: str
    message: str

    def __str__(self) -> str:
        icon = "✅" if self.passed else "❌"
        return f"{icon} {self.country} | {self.field} = {self.value} | {self.rule}: {self.message}"


# ── Bounds table ───────────────────────────────────────────────────────────
# (min_val, max_val, allow_none)
BOUNDS: dict[str, tuple] = {
    "pib":              (0.5,     20000.0,  False),
    "pib_crecimiento":  (-20.0,   25.0,     False),
    "inflacion":        (-5.0,    2000.0,   False),
    "tasa_bc":          (0.0,     150.0,    True),   # None OK for dollarised
    "desempleo":        (0.1,     35.0,     False),
    "poblacion":        (100_000, 250_000_000, False),
    "bancarizacion":    (1.0,     100.0,    False),
    "depositos_plazo":  (0.0,     1e12,     True),
    "aum":              (0.0,     1e12,     True),
}

# Countries where tasa_bc should be None (dollarised)
DOLLARISED = {"Ecuador", "El Salvador", "Panamá"}


def validate_bounds(country: str, field: str, value: Optional[float]) -> ValidationResult:
    """Value must be within expected physical bounds."""
    bounds = BOUNDS.get(field)
    if not bounds:
        return ValidationResult(True, field, country, value, "bounds", "No bounds defined — skip")

    lo, hi, allow_none = bounds

    if value is None:
        if allow_none:
            return ValidationResult(True, field, country, value, "bounds", "None allowed for this field")
        return ValidationResult(False, field, country, value, "bounds", "Unexpected None value")

    if value < lo or value > hi:
        return ValidationResult(
            False, field, country, value, "bounds",
            f"Out of range [{lo}, {hi}]"
        )
    return ValidationResult(True, field, country, value, "bounds", f"In range [{lo}, {hi}]")


def validate_no_negative(country: str, field: str, value: Optional[float]) -> ValidationResult:
    """Fields that must never be negative (populations, deposits, etc.)."""
    non_neg = {"pib", "poblacion", "bancarizacion", "depositos_plazo", "aum"}
    if field not in non_neg or value is None:
        return ValidationResult(True, field, country, value, "non_negative", "Skip")
    if value < 0:
        return ValidationResult(False, field, country, value, "non_negative", "Negative value not allowed")
    return ValidationResult(True, field, country, value, "non_negative", "OK")


def validate_dollarised_rate(country: str, tasa_bc: Optional[float]) -> ValidationResult:
    """Dollarised economies must have tasa_bc = None or 0."""
    if country not in DOLLARISED:
        return ValidationResult(True, "tasa_bc", country, tasa_bc, "dollarised", "Not dollarised — skip")
    if tasa_bc is not None and tasa_bc > 0:
        return ValidationResult(
            False, "tasa_bc", country, tasa_bc, "dollarised",
            f"{country} is dollarised; tasa_bc should be NULL not {tasa_bc}"
        )
    return ValidationResult(True, "tasa_bc", country, tasa_bc, "dollarised", "Correctly NULL for dollarised economy")


def validate_market_shares_sum(country: str, actors: list[dict]) -> ValidationResult:
    """Sum of cuota_mercado for a country must be within 0.1pp of 100%."""
    shares = [a["cuota_mercado"] for a in actors if a.get("country") == country and a.get("cuota_mercado") is not None]
    if not shares:
        return ValidationResult(False, "cuota_mercado", country, None, "shares_sum", "No actors found")
    total = sum(shares)
    ok = abs(total - 100.0) <= 0.11
    return ValidationResult(
        ok, "cuota_mercado", country, total, "shares_sum",
        f"Sum = {total:.2f}% ({'OK' if ok else 'FAIL — should be 100%'})"
    )


def validate_population_reasonable(country: str, value: Optional[float], prev_value: Optional[float]) -> ValidationResult:
    """Population should not change by more than 5% year-over-year."""
    if value is None or prev_value is None or prev_value == 0:
        return ValidationResult(True, "poblacion", country, value, "pop_yoy", "Skip — no previous value")
    pct_change = abs(value - prev_value) / prev_value
    ok = pct_change <= 0.05
    return ValidationResult(
        ok, "poblacion", country, value, "pop_yoy",
        f"YoY change {pct_change*100:.1f}% ({'OK' if ok else '>5% — check'})"
    )


def run_all_validations(country: str, row: dict, actors: list[dict]) -> list[ValidationResult]:
    """Run every applicable validation for a country row. Returns all results."""
    results = []
    for field in BOUNDS:
        value = row.get(field)
        results.append(validate_bounds(country, field, value))
        results.append(validate_no_negative(country, field, value))
    results.append(validate_dollarised_rate(country, row.get("tasa_bc")))
    results.append(validate_market_shares_sum(country, actors))
    return results


def summarise(results: list[ValidationResult]) -> dict:
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    return {
        "total":  len(results),
        "passed": passed,
        "failed": failed,
        "errors": [str(r) for r in results if not r.passed],
    }
