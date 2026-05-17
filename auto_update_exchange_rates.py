"""
Daily exchange rate updater for 18 LATAM currencies.
Fetches from free official sources, stores in Supabase.

Sources (in priority order):
  1. open.er-api.com   — free, daily updates, no API key
  2. frankfurter.app   — free, ECB-backed, no API key
  3. Banxico (Mexico)  — free official API, USD/MXN
  4. BCRP  (Peru)      — free official API, USD/PEN
  5. BCB   (Brazil)    — free official API, USD/BRL

Run daily. Schedule: 0 12 * * * UTC (7am America/Guayaquil).

Supabase table required — run once in SQL editor:
  CREATE TABLE IF NOT EXISTS exchange_rates (
      currency_code TEXT PRIMARY KEY,
      rate_usd      NUMERIC(20, 6) NOT NULL,
      source        TEXT,
      last_updated  TIMESTAMPTZ DEFAULT NOW()
  );
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ISO 4217 code → country name (USD-based economies omitted)
CURRENCIES = {
    "MXN": "México",
    "CLP": "Chile",
    "COP": "Colombia",
    "BRL": "Brasil",
    "ARS": "Argentina",
    "PEN": "Perú",
    "BOB": "Bolivia",
    "PYG": "Paraguay",
    "UYU": "Uruguay",
    "VES": "Venezuela",
    "GTQ": "Guatemala",
    "HNL": "Honduras",
    "NIO": "Nicaragua",
    "CRC": "Costa Rica",
    "DOP": "Rep. Dominicana",
}


# ── Source 1: open.er-api.com (primary) ────────────────────────────────
def fetch_openexchange():
    r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=12)
    j = r.json()
    if j.get("result") == "success":
        return j["rates"], "open.er-api.com"
    return None, None


# ── Source 2: Frankfurter / ECB (fallback) ─────────────────────────────
def fetch_frankfurter():
    r = requests.get("https://api.frankfurter.app/latest?from=USD", timeout=12)
    j = r.json()
    if "rates" in j:
        return j["rates"], "frankfurter.app (ECB)"
    return None, None


# ── Source 3: Banxico official API — USD/MXN ──────────────────────────
def fetch_banxico_mxn():
    url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno"
    headers = {"Bmx-Token": "dummy"}   # public series requires token; fallback only
    try:
        r = requests.get(url, headers=headers, timeout=10)
        j = r.json()
        datos = j["bmx"]["series"][0]["datos"]
        rate = float(datos[-1]["dato"])
        return rate, "Banxico (SF43718)"
    except Exception:
        return None, None


# ── Source 4: BCRP official API — USD/PEN ─────────────────────────────
def fetch_bcrp_pen():
    url = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/PD04647PD/json"
    try:
        r = requests.get(url, timeout=10)
        j = r.json()
        periods = j["periods"]
        last = periods[-1]["values"][0]
        return float(last), "BCRP"
    except Exception:
        return None, None


# ── Source 5: BCB Brazil — USD/BRL ────────────────────────────────────
def fetch_bcb_brl():
    url = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{}' &$top=1&$format=json&$select=cotacaoVenda"
    from datetime import date
    today = date.today().strftime("%m-%d-%Y")
    try:
        r = requests.get(
            f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            f"CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{today}'"
            f"&$top=1&$format=json&$select=cotacaoVenda",
            timeout=10,
        )
        j = r.json()
        rate = j["value"][0]["cotacaoVenda"]
        return float(rate), "BCB (PTAX)"
    except Exception:
        return None, None


# ── Main ───────────────────────────────────────────────────────────────
def update():
    print("=" * 70)
    print(f"AUTO-UPDATE EXCHANGE RATES — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Fetch bulk rates (sources 1 → 2)
    rates, source = fetch_openexchange()
    if not rates:
        print("  open.er-api unavailable, trying Frankfurter…")
        rates, source = fetch_frankfurter()
    if not rates:
        print("✗ All bulk sources failed — aborting")
        return

    print(f"  Bulk source: {source}")

    # Override with official central-bank rates where available
    overrides = {}
    pen, pen_src = fetch_bcrp_pen()
    if pen:
        overrides["PEN"] = (pen, pen_src)
    brl, brl_src = fetch_bcb_brl()
    if brl:
        overrides["BRL"] = (brl, brl_src)

    now = datetime.now().isoformat()
    ok, fail = [], []

    for code in CURRENCIES:
        if code in overrides:
            rate_val, rate_src = overrides[code]
        else:
            rate_val = rates.get(code)
            rate_src = source

        if not rate_val:
            print(f"  ✗ {code}: not in response")
            fail.append(code)
            continue

        try:
            supabase.table("exchange_rates").upsert(
                {
                    "currency_code": code,
                    "rate_usd": round(float(rate_val), 6),
                    "source": rate_src,
                    "last_updated": now,
                },
                on_conflict="currency_code",
            ).execute()
            print(f"  ✓ {code:<5}  1 USD = {rate_val:>14,.4f}  [{rate_src}]")
            ok.append(code)
        except Exception as e:
            print(f"  ✗ {code}: Supabase error — {e}")
            fail.append(code)

    print("=" * 70)
    print(f"✓ {len(ok)}/{len(CURRENCIES)} currencies saved")
    if fail:
        print(f"✗ Failed: {', '.join(fail)}")
    print("=" * 70)


if __name__ == "__main__":
    update()
