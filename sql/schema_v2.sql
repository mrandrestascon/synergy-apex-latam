-- ══════════════════════════════════════════════════════════════════════════
-- SynerGy Apex LATAM — Schema V2
-- Run in Supabase SQL Editor. All statements are idempotent.
-- ══════════════════════════════════════════════════════════════════════════


-- ── 1. countries: add provenance + deposit columns ───────────────────────
ALTER TABLE countries
  ADD COLUMN IF NOT EXISTS source_meta   JSONB,
  ADD COLUMN IF NOT EXISTS asof_date     DATE,
  ADD COLUMN IF NOT EXISTS currency      TEXT,
  ADD COLUMN IF NOT EXISTS depositos_plazo      NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS depositos_inversion  NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS aum                  NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS cagr5y               NUMERIC(6, 2);


-- ── 2. actors: add provenance columns ────────────────────────────────────
ALTER TABLE actors
  ADD COLUMN IF NOT EXISTS source_meta   JSONB,
  ADD COLUMN IF NOT EXISTS asof_date     DATE,
  ADD COLUMN IF NOT EXISTS currency      TEXT;


-- ── 3. exchange_rates: verify schema ─────────────────────────────────────
-- (already exists, created by auto_update_exchange_rates.py)
CREATE TABLE IF NOT EXISTS exchange_rates (
  currency_code TEXT PRIMARY KEY,
  rate_usd      NUMERIC(20, 6) NOT NULL,
  source        TEXT,
  last_updated  TIMESTAMPTZ DEFAULT NOW()
);


-- ── 4. Populate currency column ──────────────────────────────────────────
UPDATE countries SET currency = 'MXN' WHERE country = 'México';
UPDATE countries SET currency = 'CLP' WHERE country = 'Chile';
UPDATE countries SET currency = 'COP' WHERE country = 'Colombia';
UPDATE countries SET currency = 'BRL' WHERE country = 'Brasil';
UPDATE countries SET currency = 'ARS' WHERE country = 'Argentina';
UPDATE countries SET currency = 'PEN' WHERE country = 'Perú';
UPDATE countries SET currency = 'USD' WHERE country = 'Ecuador';
UPDATE countries SET currency = 'BOB' WHERE country = 'Bolivia';
UPDATE countries SET currency = 'PYG' WHERE country = 'Paraguay';
UPDATE countries SET currency = 'UYU' WHERE country = 'Uruguay';
UPDATE countries SET currency = 'VES' WHERE country = 'Venezuela';
UPDATE countries SET currency = 'GTQ' WHERE country = 'Guatemala';
UPDATE countries SET currency = 'HNL' WHERE country = 'Honduras';
UPDATE countries SET currency = 'USD' WHERE country = 'El Salvador';
UPDATE countries SET currency = 'NIO' WHERE country = 'Nicaragua';
UPDATE countries SET currency = 'USD' WHERE country = 'Panamá';
UPDATE countries SET currency = 'CRC' WHERE country = 'Costa Rica';
UPDATE countries SET currency = 'DOP' WHERE country = 'Rep. Dominicana';


-- ── 5. Populate deposit totals from actors (JOIN) ────────────────────────
UPDATE countries c
SET
  depositos_plazo     = a.sum_plazo,
  depositos_inversion = a.sum_vista + a.sum_plazo,
  aum                 = a.sum_acm,
  fecha_actualizacion = NOW()
FROM (
  SELECT
    country,
    SUM(depositos_plazo)   AS sum_plazo,
    SUM(depositos_vista)   AS sum_vista,
    SUM(acm)               AS sum_acm
  FROM actors
  GROUP BY country
) a
WHERE c.country = a.country;


-- ── 6. Apply data corrections from latest audit ──────────────────────────
-- (from corrections.sql — run AFTER this script)

-- México
UPDATE countries SET
  tasa_bc          = 9.0,
  pib_crecimiento  = 1.5,
  inflacion        = 3.8,
  bancarizacion    = 56.0
WHERE country = 'México';

-- Brasil
UPDATE countries SET
  tasa_bc   = 13.75,
  inflacion = 5.83
WHERE country = 'Brasil';

-- Colombia
UPDATE countries SET inflacion = 5.1  WHERE country = 'Colombia';

-- Perú
UPDATE countries SET
  inflacion        = 1.9,
  pib_crecimiento  = 3.0,
  desempleo        = 5.7
WHERE country = 'Perú';

-- Ecuador
UPDATE countries SET
  pib_crecimiento = -0.2,
  inflacion       = 0.82,
  desempleo       = 3.3,
  poblacion       = 18139000,
  bancarizacion   = 57.0,
  tasa_bc         = NULL
WHERE country = 'Ecuador';

-- Chile
UPDATE countries SET
  pib_crecimiento = 2.5,
  bancarizacion   = 87.0
WHERE country = 'Chile';

-- Guatemala
UPDATE countries SET pib = 103.0 WHERE country = 'Guatemala';

-- Venezuela
UPDATE countries SET inflacion = 200.0 WHERE country = 'Venezuela';

-- Argentina
UPDATE countries SET inflacion = 55.0 WHERE country = 'Argentina';


-- ── 7. Recalculate actor market shares in-database ───────────────────────
UPDATE actors a
SET cuota_mercado = ROUND(
  a.acm / totals.total_acm * 100,
  2
)
FROM (
  SELECT country, SUM(acm) AS total_acm
  FROM actors
  WHERE acm > 0
  GROUP BY country
) totals
WHERE a.country = totals.country
  AND totals.total_acm > 0;


-- ── 8. Verification queries ───────────────────────────────────────────────
-- Run these to confirm everything looks correct.

SELECT
  country,
  currency,
  pib,
  pib_crecimiento,
  inflacion,
  tasa_bc,
  desempleo,
  depositos_plazo,
  aum,
  fecha_actualizacion
FROM countries
ORDER BY pib DESC NULLS LAST;

SELECT
  country,
  COUNT(*)                       AS n_actors,
  ROUND(SUM(cuota_mercado), 1)   AS shares_sum_pct,
  SUM(acm)                       AS total_acm
FROM actors
GROUP BY country
ORDER BY total_acm DESC;
