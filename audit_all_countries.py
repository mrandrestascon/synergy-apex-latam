"""
SynerGy Apex LATAM — Automated Data Audit System
=================================================
Audits all 18 LATAM countries against official central bank / statistical
institute sources.  Produces:
  1. Console report  (human-readable)
  2. AUDITORÍA_COMPLETA_18PAÍSES.csv  (desktop)
  3. corrections.sql  (ready for Supabase SQL editor)
  4. audit_log.jsonl  (append-only machine log for Railway)

Run modes
---------
  python3 audit_all_countries.py          # full audit + CSV + SQL
  python3 audit_all_countries.py --json   # JSON output only (Railway cron)
  python3 audit_all_countries.py --sql    # print corrections SQL only

Schedule (Railway cron)
-----------------------
  0 8 1 * *   — 1st of every month at 08:00 UTC (03:00 Guayaquil)

Official sources used
---------------------
  Macro : FMI WEO Apr 2025, BCE, Banxico, BCCh, BanRep, BCB, BCRP,
          BCU, BCP, BCH, Banguat, BCRD, BCR-SV, BCN, BCB-Bolivia,
          MEF Panamá, BCCR, BCV
  Demo  : INEGI, DANE, IBGE, INEI, INEC, INE-CL, INDEC, INE-Bo,
          DGEEC, INE-Uy, IIES/CEPAL, INE-Gt, INE-Hn, DIGESTYC,
          INIDE, INEC-Py, ONE-RD
  Banks : SBS, SIB, CNBS, SSF, SIBOIF, SBP, SUGEF, CMF, BCB-BR,
          BCRA, SBS-Pe, SB-RD, ASFI
  FX    : Global Findex BM 2021 / 2023 (bancarización)
"""

import os
import sys
import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

# Look for .env next to this script, then in the synergy-apex-latam project dir
_HERE = Path(__file__).resolve().parent
for _candidate in [
    _HERE / ".env",
    _HERE.parent / "synergy-apex-latam" / ".env",
    Path.home() / "Desktop" / "synergy-apex-latam" / ".env",
]:
    if _candidate.exists():
        load_dotenv(_candidate)
        break
else:
    load_dotenv()  # fallback: search CWD upward

# ── Logging ────────────────────────────────────────────────────────────────
LOG_FILE = Path(__file__).parent / "audit_log.jsonl"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("audit")

# ── Supabase connection ────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    log.error("SUPABASE_URL / SUPABASE_KEY not set. Check .env")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# ── Thresholds (% deviation before flagging) ──────────────────────────────
OK_PCT   = 5.0    # ≤ 5%  → ✅
WARN_PCT = 15.0   # ≤ 15% → ⚠️  else → ❌
# Absolute thresholds for indicators where % is misleading
ABS_TASA = 0.75   # ±0.75 pp for policy rates  → ✅
ABS_DEFL = 1.0    # ±1.0 pp for inflation/unemployment in high-vol countries


# ══════════════════════════════════════════════════════════════════════════
# OFFICIAL REFERENCE TABLE
# Format per indicator: (official_value, source_string, reference_year)
# None for official_value = not applicable (e.g. dollarised rate)
# ══════════════════════════════════════════════════════════════════════════
REFERENCE: dict[str, dict] = {

  # ── México ──────────────────────────────────────────────────────────────
  "México": {
    "pib":             (1347.0,  "FMI WEO Abr 2025 / INEGI",               2024),
    "pib_crecimiento": (1.5,     "INEGI Primer Estimado PIB",               2024),
    "inflacion":       (3.8,     "INEGI INPC Mar 2025 (anual)",             2025),
    "tasa_bc":         (9.0,     "Banxico Tasa Objetivo Mar 2025",          2025),
    "desempleo":       (2.8,     "INEGI ENOE Q1 2025",                      2025),
    "poblacion":       (129406736,"INEGI Proyecciones",                     2024),
    "bancarizacion":   (56.0,    "ENIF 2021 / Global Findex BM",            2021),
  },

  # ── Chile ───────────────────────────────────────────────────────────────
  "Chile": {
    "pib":             (335.4,   "Banco Central Chile",                     2024),
    "pib_crecimiento": (2.5,     "BCCh Crecimiento PIB",                    2024),
    "inflacion":       (4.5,     "INE IPC Abr 2025 (anual)",                2025),
    "tasa_bc":         (5.0,     "BCCh TPM May 2025",                       2025),
    "desempleo":       (8.5,     "INE Encuesta Nacional Empleo Q1 2025",    2025),
    "poblacion":       (19764742,"INE Chile Proyecciones",                  2024),
    "bancarizacion":   (87.0,    "CMF Chile / Global Findex BM",            2021),
  },

  # ── Colombia ────────────────────────────────────────────────────────────
  "Colombia": {
    "pib":             (370.0,   "DANE PIB / BanRep",                       2024),
    "pib_crecimiento": (1.7,     "DANE Crecimiento PIB",                    2024),
    "inflacion":       (5.1,     "DANE IPC Abr 2025 (anual)",               2025),
    "tasa_bc":         (9.25,    "BanRep Tasa May 2025",                    2025),
    "desempleo":       (10.1,    "DANE GEIH Q1 2025",                       2025),
    "poblacion":       (52215503,"DANE Proyecciones",                       2024),
    "bancarizacion":   (92.0,    "Banca de las Oportunidades",              2023),
  },

  # ── Brasil ──────────────────────────────────────────────────────────────
  "Brasil": {
    "pib":             (2174.0,  "BCB / IBGE PIB",                          2024),
    "pib_crecimiento": (3.4,     "IBGE Crecimiento PIB",                    2024),
    "inflacion":       (5.83,    "IBGE IPCA Abr 2025 (anual 12m)",          2025),
    "tasa_bc":         (13.75,   "BCB Copom Selic Meta Mar 2025",           2025),
    "desempleo":       (6.8,     "IBGE PNAD Continua Q4 2024",              2024),
    "poblacion":       (215313498,"IBGE Censo 2022 / Proyección",           2024),
    "bancarizacion":   (84.0,    "BCB Relatório Inclusão Financeira",       2023),
  },

  # ── Argentina ───────────────────────────────────────────────────────────
  "Argentina": {
    "pib":             (641.0,   "INDEC / FMI (tipo cambio oficial)",       2024),
    "pib_crecimiento": (5.0,     "INDEC EMAE proyección",                   2025),
    "inflacion":       (55.0,    "INDEC IPC Abr 2025 (interanual)",         2025),
    "tasa_bc":         (40.0,    "BCRA Tasa Política Monetaria May 2025",   2025),
    "desempleo":       (7.0,     "INDEC EPH Q4 2024",                       2024),
    "poblacion":       (46654581,"INDEC Proyecciones",                      2024),
    "bancarizacion":   (49.0,    "BCRA Encuesta Capacidades Financieras",   2022),
  },

  # ── Perú ────────────────────────────────────────────────────────────────
  "Perú": {
    "pib":             (271.0,   "BCRP PIB",                                2024),
    "pib_crecimiento": (3.0,     "BCRP Crecimiento PIB",                    2024),
    "inflacion":       (1.9,     "INEI IPC Lima Abr 2025 (anual)",          2025),
    "tasa_bc":         (4.75,    "BCRP Tasa Referencia May 2025",           2025),
    "desempleo":       (5.7,     "INEI Desempleo Lima",                     2024),
    "poblacion":       (33359418,"INEI Proyecciones",                       2024),
    "bancarizacion":   (58.0,    "SBS Perú / Global Findex",                2021),
  },

  # ── Ecuador ─────────────────────────────────────────────────────────────
  "Ecuador": {
    "pib":             (119.0,   "BCE Cuentas Nacionales 2024 (preliminar)",2024),
    "pib_crecimiento": (-0.2,    "BCE / FMI WEO Abr 2025 (crisis energética H2-2024)", 2024),
    "inflacion":       (0.82,    "INEC IPC Dic 2024 (anual – dolarizado)",  2024),
    "tasa_bc":         (None,    "Economía dolarizada – sin tasa BC propio",None),
    "desempleo":       (3.3,     "INEC ENEMDU Dic 2024 (urbano)",           2024),
    "poblacion":       (18139000,"INEC Proyecciones",                       2024),
    "bancarizacion":   (57.0,    "Global Findex BM / SBS Ecuador",          2021),
  },

  # ── Bolivia ─────────────────────────────────────────────────────────────
  "Bolivia": {
    "pib":             (44.0,    "BCB PIB / FMI",                           2024),
    "pib_crecimiento": (1.5,     "BCB / INE Bolivia",                       2024),
    "inflacion":       (6.8,     "INE Bolivia IPC",                         2025),
    "tasa_bc":         (3.5,     "BCB Tasa Política",                       2025),
    "desempleo":       (3.3,     "INE Bolivia",                             2024),
    "poblacion":       (12311000,"INE Bolivia Proyecciones",                2024),
    "bancarizacion":   (67.0,    "ASFI Bolivia / Global Findex",            2021),
  },

  # ── Paraguay ────────────────────────────────────────────────────────────
  "Paraguay": {
    "pib":             (43.6,    "BCP PIB",                                 2024),
    "pib_crecimiento": (3.8,     "BCP Crecimiento",                         2024),
    "inflacion":       (3.9,     "BCP IPC",                                 2025),
    "tasa_bc":         (6.0,     "BCP Tasa Política Monetaria May 2025",    2025),
    "desempleo":       (5.6,     "DGEEC / INE Paraguay",                    2024),
    "poblacion":       (7359000, "DGEEC Proyecciones",                      2024),
    "bancarizacion":   (29.0,    "BCP / Global Findex",                     2021),
  },

  # ── Uruguay ─────────────────────────────────────────────────────────────
  "Uruguay": {
    "pib":             (82.0,    "BCU PIB",                                 2024),
    "pib_crecimiento": (3.1,     "BCU / INE Uruguay",                       2024),
    "inflacion":       (5.4,     "INE Uruguay IPC Abr 2025",                2025),
    "tasa_bc":         (8.5,     "BCU Tasa Política Monetaria",             2025),
    "desempleo":       (8.2,     "INE Uruguay ECH",                         2024),
    "poblacion":       (3444000, "INE Uruguay Proyecciones",                2024),
    "bancarizacion":   (72.0,    "BCU / Global Findex",                     2021),
  },

  # ── Venezuela ───────────────────────────────────────────────────────────
  "Venezuela": {
    "pib":             (90.0,    "FMI estimado (BCV sin datos confiables)", 2024),
    "pib_crecimiento": (4.0,     "FMI WEO Abr 2025 proyección",            2025),
    "inflacion":       (200.0,   "BCV / FMI – interanual 2025 (en descenso)",2025),
    "tasa_bc":         (60.0,    "BCV Tasa Referencia",                     2025),
    "desempleo":       (7.0,     "FMI / CEPAL estimado",                    2024),
    "poblacion":       (28302000,"IIES / CEPAL estimado",                   2024),
    "bancarizacion":   (35.0,    "FMI / Global Findex estimado",            2021),
  },

  # ── Guatemala ───────────────────────────────────────────────────────────
  "Guatemala": {
    "pib":             (103.0,   "Banguat / FMI WEO",                       2024),
    "pib_crecimiento": (3.5,     "Banguat Crecimiento",                     2024),
    "inflacion":       (6.2,     "INE Guatemala IPC",                       2025),
    "tasa_bc":         (5.0,     "Banguat Tasa Líder",                      2025),
    "desempleo":       (2.6,     "INE Guatemala ENEI",                      2024),
    "poblacion":       (17263000,"INE Guatemala Proyecciones",              2024),
    "bancarizacion":   (43.0,    "SIB Guatemala / Global Findex",           2021),
  },

  # ── Honduras ────────────────────────────────────────────────────────────
  "Honduras": {
    "pib":             (35.0,    "BCH PIB",                                 2024),
    "pib_crecimiento": (3.5,     "BCH Crecimiento",                         2024),
    "inflacion":       (5.1,     "INE Honduras IPC",                        2025),
    "tasa_bc":         (3.0,     "BCH Tasa Política Monetaria",             2025),
    "desempleo":       (6.1,     "INE Honduras EPHPM",                      2024),
    "poblacion":       (10280000,"INE Honduras Proyecciones",               2024),
    "bancarizacion":   (30.0,    "CNBS Honduras / Global Findex",           2021),
  },

  # ── El Salvador ─────────────────────────────────────────────────────────
  "El Salvador": {
    "pib":             (34.0,    "BCR El Salvador PIB",                     2024),
    "pib_crecimiento": (2.0,     "BCR Crecimiento",                         2024),
    "inflacion":       (2.5,     "DIGESTYC IPC",                            2025),
    "tasa_bc":         (0.0,     "Economía dolarizada – sin tasa BC propio",None),
    "desempleo":       (4.5,     "DIGESTYC EHPM",                           2024),
    "poblacion":       (6314000, "MINEC / DIGESTYC Proyecciones",           2024),
    "bancarizacion":   (40.0,    "SSF El Salvador / Global Findex",         2021),
  },

  # ── Nicaragua ───────────────────────────────────────────────────────────
  "Nicaragua": {
    "pib":             (17.0,    "BCN PIB",                                 2024),
    "pib_crecimiento": (3.8,     "BCN Crecimiento",                         2024),
    "inflacion":       (7.2,     "BCN / INIDE IPC",                         2025),
    "tasa_bc":         (7.0,     "BCN Tasa de Referencia",                  2025),
    "desempleo":       (4.5,     "INIDE Nicaragua",                         2024),
    "poblacion":       (6948000, "INIDE Proyecciones",                      2024),
    "bancarizacion":   (22.0,    "SIBOIF Nicaragua / Global Findex",        2021),
  },

  # ── Panamá ──────────────────────────────────────────────────────────────
  "Panamá": {
    "pib":             (78.5,    "MEF Panamá / FMI",                        2024),
    "pib_crecimiento": (3.2,     "MEF / INEC Crecimiento",                  2024),
    "inflacion":       (2.8,     "INEC IPC Panamá",                         2025),
    "tasa_bc":         (None,    "Economía dolarizada – tasa referencia Fed",None),
    "desempleo":       (9.8,     "INEC Mercado Laboral",                     2024),
    "poblacion":       (4408581, "INEC Proyecciones",                       2024),
    "bancarizacion":   (58.0,    "SBP / Global Findex",                     2021),
  },

  # ── Costa Rica ──────────────────────────────────────────────────────────
  "Costa Rica": {
    "pib":             (70.0,    "BCCR PIB",                                2024),
    "pib_crecimiento": (4.5,     "BCCR Crecimiento",                        2024),
    "inflacion":       (3.0,     "INEC IPC Abr 2025 (anual)",               2025),
    "tasa_bc":         (5.25,    "BCCR Tasa Política Monetaria May 2025",   2025),
    "desempleo":       (11.2,    "INEC ENAHO Q1 2025",                      2025),
    "poblacion":       (5180829, "INEC Proyecciones",                       2024),
    "bancarizacion":   (65.0,    "SUGEF / Global Findex",                   2021),
  },

  # ── Rep. Dominicana ─────────────────────────────────────────────────────
  "Rep. Dominicana": {
    "pib":             (113.0,   "BCRD PIB",                                2024),
    "pib_crecimiento": (4.6,     "BCRD Crecimiento",                        2024),
    "inflacion":       (4.9,     "BCRD IPC Abr 2025 (anual)",               2025),
    "tasa_bc":         (7.0,     "BCRD Tasa Política Monetaria May 2025",   2025),
    "desempleo":       (5.9,     "ONE / BCRD Mercado Laboral",              2024),
    "poblacion":       (11117000,"ONE Proyecciones",                        2024),
    "bancarizacion":   (56.0,    "SB Rep. Dominicana / Global Findex",      2021),
  },
}

# Human-readable label + unit for each field
INDICATORS = {
    "pib":             ("PIB",            "B USD"),
    "pib_crecimiento": ("Crec. PIB",      "%"),
    "inflacion":       ("Inflación",      "%"),
    "tasa_bc":         ("Tasa BC",        "%"),
    "desempleo":       ("Desempleo",      "%"),
    "poblacion":       ("Población",      "hab"),
    "bancarizacion":   ("Bancarización",  "%"),
}


# ══════════════════════════════════════════════════════════════════════════
# DATA FETCH
# ══════════════════════════════════════════════════════════════════════════

def fetch_supabase(table: str, params: str = "") -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.error("Supabase fetch error [%s]: %s", table, exc)
        return []


# ══════════════════════════════════════════════════════════════════════════
# AUDIT LOGIC
# ══════════════════════════════════════════════════════════════════════════

def compute_estado(
    dash_val: float,
    ref_val: Optional[float],
    indicator: str,
) -> tuple[str, str, str]:
    """Return (estado_emoji, diff_abs, diff_pct_str)."""
    if ref_val is None:
        return "N/A", "—", "—"

    diff_abs = dash_val - ref_val
    diff_pct = (diff_abs / abs(ref_val) * 100) if ref_val != 0 else float("inf")

    # Absolute tolerance for policy rates (pp, not %)
    if indicator == "tasa_bc":
        if abs(diff_abs) <= ABS_TASA:
            return "✅", f"{diff_abs:+.2f} pp", f"{diff_pct:+.1f}%"
        if abs(diff_abs) <= 2.0:
            return "⚠️", f"{diff_abs:+.2f} pp", f"{diff_pct:+.1f}%"
        return "❌", f"{diff_abs:+.2f} pp", f"{diff_pct:+.1f}%"

    # Population: tight absolute tolerance
    if indicator == "poblacion":
        pct = abs(diff_pct)
        emoji = "✅" if pct <= 1.0 else ("⚠️" if pct <= 3.0 else "❌")
        return emoji, f"{diff_abs:+,.0f}", f"{diff_pct:+.1f}%"

    # PIB: moderate tolerance (data lags up to a year)
    if indicator == "pib":
        pct = abs(diff_pct)
        emoji = "✅" if pct <= 5.0 else ("⚠️" if pct <= 12.0 else "❌")
        return emoji, f"{diff_abs:+.1f}", f"{diff_pct:+.1f}%"

    # Inflation: high-vol countries get wider band
    if indicator == "inflacion":
        band = 30.0 if abs(ref_val) > 50 else WARN_PCT
        pct = abs(diff_pct)
        emoji = "✅" if pct <= OK_PCT else ("⚠️" if pct <= band else "❌")
        return emoji, f"{diff_abs:+.2f} pp", f"{diff_pct:+.1f}%"

    # General case
    pct = abs(diff_pct)
    emoji = "✅" if pct <= OK_PCT else ("⚠️" if pct <= WARN_PCT else "❌")
    return emoji, f"{diff_abs:+.2f}", f"{diff_pct:+.1f}%"


def audit_country(country_row: dict) -> list[dict]:
    country = country_row["country"]
    ref_country = REFERENCE.get(country)
    if not ref_country:
        log.warning("No reference data for country: %s", country)
        return []

    rows = []
    for field, (label, unit) in INDICATORS.items():
        dash_val = country_row.get(field)
        ref_entry = ref_country.get(field)

        if dash_val is None:
            continue

        if ref_entry is None:
            ref_val, source, ref_year = None, "Sin referencia", None
        else:
            ref_val, source, ref_year = ref_entry

        estado, diff_abs, diff_pct = compute_estado(float(dash_val), ref_val, field)

        rows.append({
            "País":               country,
            "Indicador":          label,
            "Unidad":             unit,
            "Valor Dashboard":    str(dash_val),
            "Valor Oficial":      str(ref_val) if ref_val is not None else "N/A",
            "Diferencia":         diff_abs,
            "Diferencia %":       diff_pct,
            "Estado":             estado,
            "Fuente Oficial":     source,
            "Año Referencia":     str(ref_year) if ref_year else "N/A",
            "Fecha Auditoría":    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        })
    return rows


# ══════════════════════════════════════════════════════════════════════════
# SQL GENERATOR
# ══════════════════════════════════════════════════════════════════════════

def generate_sql(audit_rows: list[dict]) -> str:
    """Produce a ready-to-execute SQL correction script."""
    # Collect corrections: country → {field: new_val}
    corrections: dict[str, dict] = {}
    for row in audit_rows:
        if row["Estado"] not in ("❌", "⚠️"):
            continue
        if row["Valor Oficial"] == "N/A":
            continue
        country = row["País"]
        # Reverse-map label → field
        field = next(
            (f for f, (lbl, _) in INDICATORS.items() if lbl == row["Indicador"]),
            None,
        )
        if not field:
            continue
        # Only auto-suggest fixes for ❌ errors (not ⚠️ warnings — those may be
        # intentional estimates or lagged data)
        if row["Estado"] != "❌":
            continue
        corrections.setdefault(country, {})[field] = row["Valor Oficial"]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "-- ══════════════════════════════════════════════════════════════════",
        f"-- SynerGy Apex LATAM — SQL Corrections  ({now})",
        "-- Generated by audit_all_countries.py  |  Execute in Supabase SQL editor",
        "-- ══════════════════════════════════════════════════════════════════",
        "",
        "-- ── PRE-AUDIT SELECT ────────────────────────────────────────────",
        "SELECT country, pib, pib_crecimiento, inflacion, tasa_bc, desempleo,",
        "       poblacion, bancarizacion",
        "FROM countries",
        "ORDER BY country;",
        "",
        "-- ── CORRECTIONS (❌ errors only) ─────────────────────────────────",
    ]

    if not corrections:
        lines.append("-- No critical (❌) errors found — no corrections needed.")
    else:
        for country, fields in sorted(corrections.items()):
            set_parts = []
            for field, val in fields.items():
                try:
                    float(val)
                    set_parts.append(f"  {field} = {val}")
                except ValueError:
                    continue
            if not set_parts:
                continue
            set_parts.append("  fecha_actualizacion = NOW()")
            lines.append(f"\n-- {country}")
            lines.append("UPDATE countries SET")
            lines.append(",\n".join(set_parts))
            lines.append(f"WHERE country = '{country}';")

    lines += [
        "",
        "-- ── POST-AUDIT VERIFICATION ─────────────────────────────────────",
        "SELECT country, pib, pib_crecimiento, inflacion, tasa_bc, desempleo,",
        "       poblacion, bancarizacion, fecha_actualizacion",
        "FROM countries",
        "ORDER BY country;",
    ]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# CONSOLE REPORT
# ══════════════════════════════════════════════════════════════════════════

def print_report(audit_rows: list[dict]) -> dict:
    counts = {"✅": 0, "⚠️": 0, "❌": 0, "N/A": 0}
    errors, warnings = [], []

    for r in audit_rows:
        st = r["Estado"]
        counts[st] = counts.get(st, 0) + 1
        if st == "❌":
            errors.append(r)
        elif st == "⚠️":
            warnings.append(r)

    total = len(audit_rows)
    print()
    print("═" * 76)
    print("  SYNERGY APEX LATAM — AUDITORÍA AUTOMATIZADA DE DATOS")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  18 países · {total} indicadores auditados")
    print("═" * 76)
    print(
        f"  ✅ OK          : {counts['✅']:>3}  ({counts['✅']/total*100:.0f}%)\n"
        f"  ⚠️  Aproximado  : {counts['⚠️']:>3}  ({counts['⚠️']/total*100:.0f}%)\n"
        f"  ❌ Error crítico: {counts['❌']:>3}  ({counts['❌']/total*100:.0f}%)\n"
        f"  N/A            : {counts.get('N/A',0):>3}"
    )
    print("═" * 76)

    if errors:
        print(f"\n── ERRORES CRÍTICOS ❌  ({len(errors)} total) ──────────────────────────────")
        for r in errors:
            print(
                f"  {r['País']:<18} │ {r['Indicador']:<14} │ "
                f"Dashboard: {r['Valor Dashboard']:>10} {r['Unidad']:<5} │ "
                f"Oficial: {r['Valor Oficial']:>10} {r['Unidad']:<5} │ "
                f"Δ {r['Diferencia %']}"
            )
            print(f"  {'':18}   Fuente: {r['Fuente Oficial']}")

    if warnings:
        print(f"\n── ADVERTENCIAS ⚠️   ({len(warnings)} total) ─────────────────────────────────")
        for r in warnings:
            print(
                f"  {r['País']:<18} │ {r['Indicador']:<14} │ "
                f"Dashboard: {r['Valor Dashboard']:>10} {r['Unidad']:<5} │ "
                f"Oficial: {r['Valor Oficial']:>10} {r['Unidad']:<5} │ "
                f"Δ {r['Diferencia %']}"
            )

    print()
    return counts


# ══════════════════════════════════════════════════════════════════════════
# JSONL LOG  (append-only, for Railway monitoring)
# ══════════════════════════════════════════════════════════════════════════

def write_log_entry(counts: dict, total: int, output_csv: str) -> None:
    entry = {
        "ts":        datetime.now(timezone.utc).isoformat(),
        "total":     total,
        "ok":        counts.get("✅", 0),
        "warn":      counts.get("⚠️", 0),
        "error":     counts.get("❌", 0),
        "na":        counts.get("N/A", 0),
        "output":    output_csv,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    log.info("Log entry written → %s", LOG_FILE)


# ══════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    mode_json = "--json" in sys.argv
    mode_sql  = "--sql"  in sys.argv

    # 1. Fetch from Supabase
    log.info("Fetching countries from Supabase…")
    rows = fetch_supabase("countries", "select=*&order=country")
    if not rows:
        log.error("No data returned from Supabase. Aborting.")
        sys.exit(1)
    log.info("  %d countries loaded", len(rows))

    # 2. Audit each country
    all_audit: list[dict] = []
    for row in rows:
        all_audit.extend(audit_country(row))

    if not all_audit:
        log.error("Audit produced no rows. Check REFERENCE table.")
        sys.exit(1)

    # 3. SQL only mode
    if mode_sql:
        print(generate_sql(all_audit))
        return

    # 4. JSON mode (Railway cron — minimal output)
    if mode_json:
        counts = {
            "✅": sum(1 for r in all_audit if r["Estado"] == "✅"),
            "⚠️": sum(1 for r in all_audit if r["Estado"] == "⚠️"),
            "❌": sum(1 for r in all_audit if r["Estado"] == "❌"),
        }
        print(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "countries": len(rows),
            "total_indicators": len(all_audit),
            **counts,
            "errors": [
                {"pais": r["País"], "indicador": r["Indicador"],
                 "dashboard": r["Valor Dashboard"], "oficial": r["Valor Oficial"]}
                for r in all_audit if r["Estado"] == "❌"
            ],
        }, ensure_ascii=False, indent=2))
        return

    # 5. Full mode: console + CSV + SQL file
    counts = print_report(all_audit)

    # CSV output
    date_tag  = datetime.now().strftime("%Y%m%d")
    csv_path  = Path.home() / "Desktop" / f"AUDITORÍA_COMPLETA_18PAÍSES_{date_tag}.csv"
    sql_path  = Path(__file__).parent / "corrections.sql"

    fieldnames = list(all_audit[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_audit)
    log.info("CSV  → %s", csv_path)

    # SQL corrections file
    sql_text = generate_sql(all_audit)
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write(sql_text)
    log.info("SQL  → %s", sql_path)

    # Append to JSONL log
    write_log_entry(counts, len(all_audit), str(csv_path))

    print(f"  CSV  → {csv_path}")
    print(f"  SQL  → {sql_path}")
    print(f"  LOG  → {LOG_FILE}")
    print("═" * 76)


if __name__ == "__main__":
    main()
