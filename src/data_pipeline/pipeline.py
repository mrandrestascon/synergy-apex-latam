"""
Pipeline orchestrator: config → fetch → parse → validate → metrics → upsert.

Usage:
    python3 -m src.data_pipeline.pipeline                   # full run
    python3 -m src.data_pipeline.pipeline --country México  # single country
    python3 -m src.data_pipeline.pipeline --dry-run         # no Supabase writes
"""
from __future__ import annotations
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
import requests
from dotenv import load_dotenv

# ── local imports ──────────────────────────────────────────────────────────
# Support running as module or direct script
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from src.data_pipeline.provenance import ProvenanceRecord, CountryDataPoint
from src.data_pipeline.metrics    import cagr_pct, recalculate_market_shares, deposit_total
from src.data_pipeline.validators import run_all_validations, summarise
from src.data_pipeline import fetchers, parsers

# ── env / logging ──────────────────────────────────────────────────────────
for _env in [_ROOT / ".env", _ROOT.parent / "synergy-apex-latam" / ".env"]:
    if _env.exists():
        load_dotenv(_env)
        break

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("pipeline")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
CONFIG_PATH  = _ROOT / "config" / "countries.yaml"

MACRO_FIELDS = ["pib", "pib_crecimiento", "inflacion", "tasa_bc", "desempleo", "poblacion", "bancarizacion"]


# ── Supabase helpers ───────────────────────────────────────────────────────

def _sb_headers() -> dict:
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}


def sb_upsert(table: str, rows: list[dict]) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.warning("Supabase credentials missing — skipping upsert")
        return False
    try:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=_sb_headers(), json=rows, timeout=20)
        r.raise_for_status()
        return True
    except Exception as exc:
        log.error("Supabase upsert [%s] FAIL: %s", table, exc)
        return False


def sb_fetch(table: str, params: str = "") -> list[dict]:
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}", headers=_sb_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.error("Supabase fetch [%s] FAIL: %s", table, exc)
        return []


# ── Config loader ──────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Per-field resolver ─────────────────────────────────────────────────────

BANXICO_MAP = {
    "tasa_bc":         "SF61745",
    "inflacion":       "SP1",
    "pib_crecimiento": "SE38768",
}

BCB_MAP = {
    "tasa_bc":         432,
    "inflacion":       13522,
    "pib_crecimiento": 7326,
}

BCRP_MAP = {
    "tasa_bc":         "PD04706PD",
    "inflacion":       "PD39462PD",
    "pib_crecimiento": "PD38706PD",
    "pib":             "PN01288AM",
    "desempleo":       "PD39491PD",
}

IBGE_MAP = {
    "desempleo":  ("6381", "4099"),
    "poblacion":  ("6579", "9324"),
}


def resolve_field(country: str, field: str, source_cfg: dict) -> CountryDataPoint:
    """
    Try to fetch live data. Fall back to reference value if inaccessible.
    Returns a CountryDataPoint with provenance attached.
    """
    src = source_cfg
    src_id   = src.get("id", field)
    src_name = src.get("name", field)
    src_url  = src.get("url", "")
    accessible = src.get("accessible", False)
    fallback   = src.get("fallback", "reference")

    value: Optional[float] = None
    asof_date = ""
    method = src.get("type", "manual")
    confidence = "high" if accessible else "medium"
    is_estimated = not accessible

    # ── Live fetch paths ────────────────────────────────────────────────
    if accessible:
        if country == "México" and field in BANXICO_MAP:
            raw = fetchers.fetch_banxico(BANXICO_MAP[field])
            value, asof_date = parsers.parse_banxico_serie(raw)

        elif country == "Brasil" and field in BCB_MAP:
            raw = fetchers.fetch_bcb_sgs(BCB_MAP[field])
            value, asof_date = parsers.parse_bcb_sgs(raw)
            if field in IBGE_MAP:
                ag, var = IBGE_MAP[field]
                raw = fetchers.fetch_ibge_sidra(ag, var)
                value, asof_date = parsers.parse_ibge_sidra(raw)

        elif country == "Perú" and field in BCRP_MAP:
            raw = fetchers.fetch_bcrp(BCRP_MAP[field])
            value, asof_date = parsers.parse_bcrp_serie(raw)

    # ── Fallback to reference ────────────────────────────────────────────
    if value is None:
        ref_val, ref_year = parsers.parse_reference_value(src)
        value      = ref_val
        asof_date  = ref_year
        method     = "reference"
        confidence = "medium" if ref_val is not None else "low"
        is_estimated = True

    if value is None and fallback == "supabase":
        # Caller will handle supabase fallback after this returns
        pass

    prov = ProvenanceRecord(
        value=value,
        source_id=src_id,
        source_name=src_name,
        source_url=src_url,
        fetch_method=method,
        asof_date=asof_date,
        confidence=confidence,
        is_estimated=is_estimated,
    )
    return CountryDataPoint(country=country, field=field, provenance=prov)


# ── Country processor ──────────────────────────────────────────────────────

def process_country(
    country: str,
    cfg: dict,
    existing_row: Optional[dict],
    existing_actors: list[dict],
    dry_run: bool,
) -> dict:
    """Process one country end-to-end. Returns summary dict."""
    sources = cfg.get("sources", {})
    log.info("  Processing: %s", country)

    updates: dict[str, object] = {
        "country":              country,
        "fecha_actualizacion":  datetime.now(timezone.utc).isoformat(),
    }
    source_meta: dict[str, dict] = {}
    validation_errors = []

    for field in MACRO_FIELDS:
        src_cfg = sources.get(field, {})
        if not src_cfg:
            continue

        dp = resolve_field(country, field, src_cfg)

        if dp.value is None and existing_row:
            dp.provenance.value = existing_row.get(field)
            dp.provenance.fetch_method = "supabase_fallback"
            dp.provenance.confidence   = "low"
            dp.provenance.notes        = "Live fetch failed — kept existing Supabase value"

        updates[field]          = dp.value
        source_meta[field]      = dp.to_supabase_meta()

    # ── Recalculate actors metrics ───────────────────────────────────────
    country_actors = [a for a in existing_actors if a.get("country") == country]
    if country_actors:
        recalculate_market_shares(country_actors, "acm")
        dep = deposit_total(country_actors, country)
        updates["depositos_plazo"]     = dep["depositos_plazo"]
        updates["depositos_inversion"] = dep["depositos_plazo"] + dep["depositos_vista"]
        updates["aum"]                 = dep["acm"]

        # CAGR from 5-year series (best effort — requires history table in future)
        # For now: stored cagr5y from existing data or None
        updates["cagr5y"] = existing_row.get("cagr5y") if existing_row else None

    updates["source_meta"] = json.dumps(source_meta, ensure_ascii=False)

    # ── Validate ─────────────────────────────────────────────────────────
    results = run_all_validations(country, updates, country_actors)
    summary = summarise(results)
    if summary["failed"] > 0:
        log.warning("  %s — %d validation failures: %s", country, summary["failed"], summary["errors"])
        validation_errors = summary["errors"]

    # ── Upsert to Supabase ────────────────────────────────────────────────
    if not dry_run and SUPABASE_URL:
        sb_upsert("countries", [updates])

    # ── Upsert recalculated actors ────────────────────────────────────────
    if not dry_run and country_actors and SUPABASE_URL:
        for a in country_actors:
            a["fecha_actualizacion"] = datetime.now(timezone.utc).isoformat()
        sb_upsert("actors", country_actors)

    return {
        "country":            country,
        "fields_updated":     len([k for k in updates if k in MACRO_FIELDS]),
        "validation_errors":  len(validation_errors),
        "dry_run":            dry_run,
    }


# ── Main ───────────────────────────────────────────────────────────────────

def run(target_country: Optional[str] = None, dry_run: bool = False) -> dict:
    log.info("═" * 60)
    log.info("  SynerGy LATAM Data Pipeline — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    if dry_run:
        log.info("  DRY RUN — no Supabase writes")
    log.info("═" * 60)

    config = load_config()

    existing_rows    = {r["country"]: r for r in sb_fetch("countries", "select=*")}
    existing_actors  = sb_fetch("actors", "select=*")

    results = []
    countries = [target_country] if target_country else list(config.keys())
    skip_keys = {"defaults"}

    for country in countries:
        if country in skip_keys or country not in config:
            continue
        cfg = config[country]
        if not isinstance(cfg, dict):
            continue
        result = process_country(
            country         = country,
            cfg             = cfg,
            existing_row    = existing_rows.get(country),
            existing_actors = existing_actors,
            dry_run         = dry_run,
        )
        results.append(result)

    total_errors = sum(r["validation_errors"] for r in results)
    log.info("═" * 60)
    log.info("  DONE — %d countries | %d validation errors", len(results), total_errors)
    log.info("═" * 60)

    return {"countries": len(results), "validation_errors": total_errors, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--country",  default=None, help="Run for one country only")
    parser.add_argument("--dry-run",  action="store_true", help="No Supabase writes")
    args = parser.parse_args()
    run(target_country=args.country, dry_run=args.dry_run)
