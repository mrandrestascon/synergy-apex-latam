-- ══════════════════════════════════════════════════════════════════════════
-- SynerGy Apex LATAM — Add & Populate Deposit Columns in countries table
-- Generated: 2026-05-19
-- Source: Aggregated from actors table (SUM per country)
--
-- Column definitions:
--   depositos_plazo     = SUM(actors.depositos_plazo)           per country
--   depositos_inversion = SUM(actors.depositos_vista +
--                             actors.depositos_plazo)           per country
--   aum                 = SUM(actors.acm)                       per country
--
-- Units: same as actors table (millions of local currency, or USD for
--        dollarised economies). Dashboard converts to B USD at render time.
-- ══════════════════════════════════════════════════════════════════════════


-- ── STEP 1: Verify current schema ────────────────────────────────────────
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'countries'
ORDER BY ordinal_position;


-- ── STEP 2: Add columns (safe — IF NOT EXISTS) ───────────────────────────
ALTER TABLE countries
  ADD COLUMN IF NOT EXISTS depositos_plazo      NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS depositos_inversion  NUMERIC(20, 2),
  ADD COLUMN IF NOT EXISTS aum                  NUMERIC(20, 2);


-- ── STEP 3: Populate from actors (pre-computed aggregates) ────────────────
-- Values come from: SELECT country, SUM(depositos_vista), SUM(depositos_plazo), SUM(acm)
-- FROM actors GROUP BY country  (run 2026-05-19, 146 actors, 18 countries)

UPDATE countries SET
  depositos_plazo     =   2303600,
  depositos_inversion =   6179900,
  aum                 =   6179900
WHERE country = 'México';

UPDATE countries SET
  depositos_plazo     =   1467300,
  depositos_inversion =   3525500,
  aum                 =   3525500
WHERE country = 'Brasil';

UPDATE countries SET
  depositos_plazo     =    100940,
  depositos_inversion =    188060,
  aum                 =    188060
WHERE country = 'Chile';

UPDATE countries SET
  depositos_plazo     =    238000,
  depositos_inversion =    563100,
  aum                 =    563100
WHERE country = 'Colombia';

UPDATE countries SET
  depositos_plazo     =  19891000,
  depositos_inversion =  47373000,
  aum                 =  47373000
WHERE country = 'Argentina';

UPDATE countries SET
  depositos_plazo     =     83700,
  depositos_inversion =    199400,
  aum                 =    199400
WHERE country = 'Perú';

UPDATE countries SET
  depositos_plazo     =     19240,
  depositos_inversion =     45830,
  aum                 =     45830
WHERE country = 'Ecuador';

UPDATE countries SET
  depositos_plazo     =     31800,
  depositos_inversion =     75730,
  aum                 =     75730
WHERE country = 'Bolivia';

UPDATE countries SET
  depositos_plazo     =     20880,
  depositos_inversion =     49720,
  aum                 =     49720
WHERE country = 'Paraguay';

UPDATE countries SET
  depositos_plazo     =     19080,
  depositos_inversion =     45430,
  aum                 =     45430
WHERE country = 'Uruguay';

UPDATE countries SET
  depositos_plazo     =    574200,
  depositos_inversion =   1367900,
  aum                 =   1367900
WHERE country = 'Venezuela';

UPDATE countries SET
  depositos_plazo     =     63400,
  depositos_inversion =    151100,
  aum                 =    151100
WHERE country = 'Guatemala';

UPDATE countries SET
  depositos_plazo     =     19920,
  depositos_inversion =     47430,
  aum                 =     47430
WHERE country = 'Honduras';

UPDATE countries SET
  depositos_plazo     =     11360,
  depositos_inversion =     27040,
  aum                 =     27040
WHERE country = 'El Salvador';

UPDATE countries SET
  depositos_plazo     =      7870,
  depositos_inversion =     18750,
  aum                 =     18750
WHERE country = 'Nicaragua';

UPDATE countries SET
  depositos_plazo     =     19380,
  depositos_inversion =     46140,
  aum                 =     46140
WHERE country = 'Panamá';

UPDATE countries SET
  depositos_plazo     =     15720,
  depositos_inversion =     37430,
  aum                 =     37430
WHERE country = 'Costa Rica';

UPDATE countries SET
  depositos_plazo     =     38590,
  depositos_inversion =     91900,
  aum                 =     91900
WHERE country = 'Rep. Dominicana';


-- ── STEP 4: One-liner alternative using actors JOIN ───────────────────────
-- (idempotent — safe to run again to refresh from actors)
UPDATE countries c
SET
  depositos_plazo     = a.sum_plazo,
  depositos_inversion = a.sum_total,
  aum                 = a.sum_acm,
  fecha_actualizacion = NOW()
FROM (
  SELECT
    country,
    SUM(depositos_plazo)                       AS sum_plazo,
    SUM(depositos_vista + depositos_plazo)     AS sum_total,
    SUM(acm)                                   AS sum_acm
  FROM actors
  GROUP BY country
) a
WHERE c.country = a.country;


-- ── STEP 5: Verification SELECT ──────────────────────────────────────────
SELECT
  country,
  depositos_plazo,
  depositos_inversion,
  aum,
  ROUND(aum / 1000000.0, 2)          AS aum_trillones,
  fecha_actualizacion
FROM countries
ORDER BY aum DESC NULLS LAST;
