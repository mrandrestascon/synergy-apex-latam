"""
Source-specific parsers. Each function:
  - Takes raw API/CSV response
  - Returns (value: float | None, asof_date: str)
  - Never raises — returns (None, "") on parse failure
"""
from __future__ import annotations
import logging
from typing import Optional
from datetime import datetime

log = logging.getLogger(__name__)


def _safe_float(v) -> Optional[float]:
    try:
        f = float(str(v).replace(",", "").strip())
        return f if not (f != f) else None  # NaN check
    except Exception:
        return None


# ── Banxico SIE ────────────────────────────────────────────────────────────

def parse_banxico_serie(raw: Optional[dict]) -> tuple[Optional[float], str]:
    """
    Banxico SIE response:
    {"bmx":{"series":[{"idSerie":"SF61745","datos":[{"fecha":"17/05/2026","dato":"9.00"}]}]}}
    """
    if not raw:
        return None, ""
    try:
        datos = raw["bmx"]["series"][0]["datos"]
        last  = datos[-1]
        val   = _safe_float(last["dato"])
        # date format: "DD/MM/YYYY"
        d     = datetime.strptime(last["fecha"], "%d/%m/%Y").strftime("%Y-%m-%d")
        return val, d
    except Exception as exc:
        log.debug("parse_banxico_serie error: %s", exc)
        return None, ""


# ── BCB SGS (Brazil) ───────────────────────────────────────────────────────

def parse_bcb_sgs(raw: Optional[list]) -> tuple[Optional[float], str]:
    """
    BCB SGS response: [{"data":"18/05/2026","valor":"13.75"}, ...]
    """
    if not raw:
        return None, ""
    try:
        last = raw[-1]
        val  = _safe_float(last["valor"])
        d    = datetime.strptime(last["data"], "%d/%m/%Y").strftime("%Y-%m-%d")
        return val, d
    except Exception as exc:
        log.debug("parse_bcb_sgs error: %s", exc)
        return None, ""


# ── BCRP (Peru) ────────────────────────────────────────────────────────────

def parse_bcrp_serie(raw: Optional[dict]) -> tuple[Optional[float], str]:
    """
    BCRP response:
    {"periods":[{"name":"May.25","values":["4.75"]}]}
    """
    if not raw:
        return None, ""
    try:
        periods = raw.get("periods", [])
        if not periods:
            return None, ""
        last  = periods[-1]
        val   = _safe_float(last["values"][0])
        # period name e.g. "May.25" → approximate date
        asof  = last.get("name", "")
        return val, asof
    except Exception as exc:
        log.debug("parse_bcrp_serie error: %s", exc)
        return None, ""


# ── IBGE SIDRA (Brazil) ────────────────────────────────────────────────────

def parse_ibge_sidra(raw: Optional[list]) -> tuple[Optional[float], str]:
    """
    IBGE SIDRA v3:
    [{"id":"...", "resultados":[{"series":[{"serie":{"2024Q4":"6.8"}}]}]}]
    """
    if not raw:
        return None, ""
    try:
        series_data = raw[0]["resultados"][0]["series"][0]["serie"]
        last_period = sorted(series_data.keys())[-1]
        val = _safe_float(series_data[last_period])
        return val, last_period
    except Exception as exc:
        log.debug("parse_ibge_sidra error: %s", exc)
        return None, ""


# ── open.er-api exchange rates ─────────────────────────────────────────────

def parse_exchange_rates(raw: Optional[dict]) -> tuple[Optional[dict], str]:
    """Returns (rates_dict, date_str). rates_dict maps ISO code → float."""
    if not raw or raw.get("result") != "success":
        return None, ""
    return raw.get("rates", {}), raw.get("time_last_update_utc", "")


# ── Reference / fallback ───────────────────────────────────────────────────

def parse_reference_value(source_cfg: dict) -> tuple[Optional[float], str]:
    """
    Returns (reference_value, reference_year_str) from config entry.
    Used when a source is inaccessible.
    """
    val  = source_cfg.get("reference_value")
    year = source_cfg.get("reference_year", "")
    if val is None:
        return None, str(year)
    return _safe_float(val), f"{year}-12-31" if year else ""
