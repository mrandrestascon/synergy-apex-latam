-- ══════════════════════════════════════════════════════════════════════════
-- SynerGy Apex LATAM — Populate countries deposit columns
-- Run in Supabase SQL Editor. All statements are idempotent.
--
-- Source: actors table (146 rows, 18 countries)
-- Columns added: depositos_plazo, depositos_vista, aum
-- fecha_actualizacion already exists — updated by this script.
-- ══════════════════════════════════════════════════════════════════════════


-- ── 1. Add deposit columns (idempotent) ──────────────────────────────────
ALTER TABLE countries
  ADD COLUMN IF NOT EXISTS depositos_plazo  NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS depositos_vista  NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS aum              NUMERIC(20, 2);


-- ── 2. Materialize aggregates from actors ────────────────────────────────
-- aum = total assets under management = sum(acm) per country
-- depositos_vista / depositos_plazo = sum of respective deposit types
UPDATE countries c
SET
  depositos_vista  = a.sum_vista,
  depositos_plazo  = a.sum_plazo,
  aum              = a.sum_acm,
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


-- ── 3. Spot-check: expected totals from 2026-05-18 snapshot ─────────────
-- México  : vista=3,876,300 | plazo=2,303,600 | aum=6,179,900
-- Brasil  : vista=2,058,200 | plazo=1,467,300 | aum=3,525,500
-- Argentina: vista=27,482,000 | plazo=19,891,000 | aum=47,373,000
-- Chile   : vista=87,120    | plazo=100,940   | aum=188,060
-- Colombia: vista=325,100   | plazo=238,000   | aum=563,100
-- Venezuela: vista=793,700  | plazo=574,200   | aum=1,367,900


-- ── 4. Verification SELECT ───────────────────────────────────────────────
SELECT
  country,
  depositos_vista,
  depositos_plazo,
  aum,
  fecha_actualizacion
FROM countries
ORDER BY aum DESC NULLS LAST;
