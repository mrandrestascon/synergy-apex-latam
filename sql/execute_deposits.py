"""
Execute populate_countries_deposits.sql against Supabase.

Requires ONE of these in .env:
  DATABASE_URL=postgresql://postgres:<password>@db.bnpfxaxswmmxzxiggywz.supabase.co:5432/postgres
  SUPABASE_SERVICE_KEY=eyJ...   (from Supabase dashboard → Settings → API → service_role key)
"""
from __future__ import annotations
import os, sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for _env in [_ROOT / ".env", _ROOT.parent / ".env"]:
    if _env.exists():
        from dotenv import load_dotenv
        load_dotenv(_env)
        break

DATABASE_URL     = os.getenv("DATABASE_URL")
SERVICE_KEY      = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_URL     = os.getenv("SUPABASE_URL", "https://bnpfxaxswmmxzxiggywz.supabase.co")
ANON_KEY         = os.getenv("SUPABASE_KEY")
PROJECT_REF      = "bnpfxaxswmmxzxiggywz"

DDL = """
ALTER TABLE countries
  ADD COLUMN IF NOT EXISTS depositos_plazo  NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS depositos_vista  NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS aum              NUMERIC(20, 2);
"""

UPDATE_SQL = """
UPDATE countries c
SET
  depositos_vista     = a.sum_vista,
  depositos_plazo     = a.sum_plazo,
  aum                 = a.sum_acm,
  fecha_actualizacion = NOW()
FROM (
  SELECT
    country,
    SUM(depositos_vista)  AS sum_vista,
    SUM(depositos_plazo)  AS sum_plazo,
    SUM(acm)              AS sum_acm
  FROM actors
  WHERE acm > 0
  GROUP BY country
) a
WHERE c.country = a.country;
"""

VERIFY_SQL = """
SELECT country, depositos_vista, depositos_plazo, aum
FROM countries
ORDER BY aum DESC NULLS LAST;
"""


def run_via_psycopg2(db_url: str) -> None:
    import psycopg2
    print(f"Connecting via psycopg2 …")
    with psycopg2.connect(db_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            print("  → ALTER TABLE (add columns if missing) …")
            cur.execute(DDL)
            print("  → UPDATE countries from actors aggregates …")
            cur.execute(UPDATE_SQL)
            print(f"     {cur.rowcount} rows updated")
            print("  → Verifying …")
            cur.execute(VERIFY_SQL)
            rows = cur.fetchall()
            print(f"\n{'Country':<20} {'vista':>14} {'plazo':>14} {'aum':>14}")
            print("-" * 66)
            for r in rows:
                print(f"{r[0]:<20} {r[1] or 0:>14,.0f} {r[2] or 0:>14,.0f} {r[3] or 0:>14,.0f}")
    print("\n✅  Done — countries.depositos_vista/plazo/aum populated.")


def run_via_management_api(service_key: str) -> None:
    import urllib.request, json
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
    }
    base = f"{SUPABASE_URL}/rest/v1/rpc"

    for label, sql in [("DDL", DDL), ("UPDATE", UPDATE_SQL)]:
        print(f"  → {label} via Management API …")
        payload = json.dumps({"query": sql}).encode()
        req = urllib.request.Request(
            f"https://api.supabase.com/v1/projects/{PROJECT_REF}/database/query",
            data=payload,
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                body = json.loads(resp.read())
                print(f"     OK: {body}")
        except Exception as exc:
            print(f"     FAILED: {exc}")
            raise


def main() -> None:
    if DATABASE_URL:
        run_via_psycopg2(DATABASE_URL)
    elif SERVICE_KEY:
        run_via_management_api(SERVICE_KEY)
    else:
        print(
            "\n❌  Cannot execute: no DATABASE_URL or SUPABASE_SERVICE_KEY found in .env\n\n"
            "Add ONE of the following to .env:\n\n"
            "  Option A — Direct Postgres (recommended, fastest):\n"
            "    DATABASE_URL=postgresql://postgres.<password>@aws-0-us-east-1.pooler.supabase.com:6543/postgres\n"
            "    (Supabase dashboard → Settings → Database → Connection string → URI)\n\n"
            "  Option B — Service role key:\n"
            "    SUPABASE_SERVICE_KEY=eyJ...\n"
            "    (Supabase dashboard → Settings → API → service_role key)\n\n"
            "Then re-run:  python3 sql/execute_deposits.py\n\n"
            "Alternatively, paste sql/populate_countries_deposits.sql directly\n"
            "into the Supabase SQL Editor — it is fully idempotent.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
