"""
Source Audit — tests every official source defined in countries.yaml.

For each source:
  1. Attempts HTTP connection (GET with timeout)
  2. Verifies response is parseable (JSON/CSV)
  3. Records latency, HTTP status, data freshness
  4. Outputs: audit_report.json + sources_status.csv

Usage:
    python3 src/source_audit/auditor.py
    python3 src/source_audit/auditor.py --json     # JSON only
"""
from __future__ import annotations
import os
import csv
import json
import time
import logging
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
import requests
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

for _env in [_ROOT / ".env", _ROOT.parent / "synergy-apex-latam" / ".env"]:
    if _env.exists():
        load_dotenv(_env)
        break

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("auditor")

CONFIG_PATH = _ROOT / "config" / "countries.yaml"
OUT_DIR     = _ROOT / "reports"
OUT_DIR.mkdir(exist_ok=True)

TIMEOUT = 10


# ── Test logic ─────────────────────────────────────────────────────────────

def test_source(source_id: str, source_cfg: dict) -> dict:
    """Probe a single source. Returns a result dict."""
    url        = source_cfg.get("url", "")
    src_type   = source_cfg.get("type", "manual")
    accessible = source_cfg.get("accessible", False)
    auth_cfg   = source_cfg.get("auth", {})

    result = {
        "source_id":   source_id,
        "source_name": source_cfg.get("name", source_id),
        "type":        src_type,
        "url":         url,
        "accessible":  accessible,
        "http_status": None,
        "latency_ms":  None,
        "parseable":   None,
        "live_value":  None,
        "asof":        None,
        "status":      "NOT_TESTED",
        "notes":       source_cfg.get("notes", ""),
    }

    # ── Manual / reference sources ───────────────────────────────────────
    if src_type == "manual" or not accessible:
        result["status"] = "MANUAL" if not url else "DISABLED"
        result["notes"]  = (result["notes"] + " | auto-fetch disabled").strip(" |")
        return result

    if not url:
        result["status"] = "NO_URL"
        return result

    # ── Build headers ────────────────────────────────────────────────────
    headers = {}
    if auth_cfg.get("header") and auth_cfg.get("env"):
        token = os.getenv(auth_cfg["env"], "")
        if token:
            headers[auth_cfg["header"]] = token
        else:
            result["status"] = "MISSING_AUTH"
            result["notes"]  = f"Env var {auth_cfg['env']} not set"
            return result

    # ── HTTP probe ───────────────────────────────────────────────────────
    t0 = time.monotonic()
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        latency = int((time.monotonic() - t0) * 1000)
        result["http_status"] = r.status_code
        result["latency_ms"]  = latency

        if r.status_code != 200:
            result["status"] = "HTTP_ERROR"
            result["notes"]  = f"HTTP {r.status_code}"
            return result

        # ── Try to parse ──────────────────────────────────────────────
        ct = r.headers.get("Content-Type", "")
        if "json" in ct or url.endswith(".json"):
            data = r.json()
            result["parseable"] = True
            # Extract live value for known source types
            _try_extract(result, source_id, data)
        elif "text" in ct or "csv" in ct:
            _ = r.text[:500]
            result["parseable"] = True
        else:
            result["parseable"] = len(r.content) > 100

        result["status"] = "✅ OK" if result["parseable"] else "⚠️ PARSE_FAIL"

    except requests.exceptions.Timeout:
        result["status"] = "⚠️ TIMEOUT"
        result["notes"]  = f">{TIMEOUT}s"
    except requests.exceptions.ConnectionError as exc:
        result["status"] = "❌ CONN_ERROR"
        result["notes"]  = str(exc)[:80]
    except Exception as exc:
        result["status"] = "❌ ERROR"
        result["notes"]  = str(exc)[:80]

    return result


def _try_extract(result: dict, source_id: str, data) -> None:
    """Best-effort: pull a live value from known API shapes."""
    try:
        # Banxico SIE
        if "banxico" in source_id and isinstance(data, dict):
            datos = data["bmx"]["series"][0]["datos"]
            result["live_value"] = float(datos[-1]["dato"])
            result["asof"]       = datos[-1]["fecha"]
        # BCB SGS
        elif "bcb" in source_id and isinstance(data, list) and data:
            result["live_value"] = float(data[-1]["valor"])
            result["asof"]       = data[-1]["data"]
        # BCRP
        elif "bcrp" in source_id and isinstance(data, dict):
            periods = data.get("periods", [])
            if periods:
                result["live_value"] = float(periods[-1]["values"][0])
                result["asof"]       = periods[-1]["name"]
        # IBGE SIDRA
        elif "ibge" in source_id and isinstance(data, list) and data:
            series_data = data[0]["resultados"][0]["series"][0]["serie"]
            last = sorted(series_data)[-1]
            result["live_value"] = float(series_data[last])
            result["asof"]       = last
    except Exception:
        pass


# ── Audit runner ───────────────────────────────────────────────────────────

def run_audit() -> dict:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))

    all_results = []
    tested = skipped = ok = fail = manual = 0

    for country, country_cfg in cfg.items():
        if country == "defaults" or not isinstance(country_cfg, dict):
            continue
        sources = country_cfg.get("sources", {})
        for field, src_cfg in sources.items():
            if not isinstance(src_cfg, dict):
                continue
            src_id = src_cfg.get("id", f"{country}_{field}")
            log.info("  Testing %-18s %-14s [%s]", country, field, src_id)
            res = test_source(src_id, src_cfg)
            res["country"] = country
            res["field"]   = field
            all_results.append(res)

            if res["status"] in ("MANUAL", "DISABLED", "NOT_TESTED"):
                manual += 1
            elif "✅" in str(res["status"]):
                ok   += 1
                tested += 1
            else:
                fail  += 1
                tested += 1

    timestamp = datetime.now(timezone.utc).isoformat()
    report = {
        "generated_at":   timestamp,
        "total_sources":  len(all_results),
        "tested":         tested,
        "ok":             ok,
        "failed":         fail,
        "manual":         manual,
        "results":        all_results,
    }

    # ── Write JSON report ────────────────────────────────────────────────
    json_path = OUT_DIR / "audit_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Write CSV status ─────────────────────────────────────────────────
    csv_path = OUT_DIR / "sources_status.csv"
    fields   = ["country", "field", "source_id", "source_name", "type", "status", "http_status", "latency_ms", "live_value", "asof", "url", "notes"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_results)

    # ── Write master config YAML (pass-through — for reference) ──────────
    # sources_master_config.yaml is the config itself; symlink or copy
    master_path = OUT_DIR / "sources_master_config.yaml"
    master_path.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    log.info("═" * 60)
    log.info("  AUDIT COMPLETE: %d sources | ✅ %d OK | ❌ %d FAIL | 🖊 %d MANUAL", len(all_results), ok, fail, manual)
    log.info("  JSON → %s", json_path)
    log.info("  CSV  → %s", csv_path)
    log.info("═" * 60)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    args = parser.parse_args()
    report = run_audit()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
