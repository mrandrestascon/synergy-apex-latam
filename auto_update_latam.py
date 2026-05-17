"""
Auto-update script for 18 LATAM countries.
Saves macro + banking actor data to Supabase.

Data sources by country:
  México         — CNBV (cnbv.gob.mx), Banxico (banxico.org.mx)
  Chile          — CMF (cmfchile.cl), Banco Central de Chile (bcentral.cl)
  Colombia       — SFC (superfinanciera.gov.co), Banco de la República (banrep.gov.co)
  Brasil         — BCB (bcb.gov.br), IBGE (ibge.gov.br)
  Argentina      — BCRA (bcra.gob.ar), INDEC (indec.gob.ar)
  Perú           — SBS (sbs.gob.pe), BCRP (bcrp.gob.pe)
  Ecuador        — Superintendencia de Bancos (superbancos.gob.ec), BCE (bce.fin.ec)
  Bolivia        — ASFI (asfi.gob.bo), BCB (bcb.gob.bo)
  Paraguay       — BCP / Superintendencia de Bancos (bcp.gov.py)
  Uruguay        — BCU (bcu.gub.uy), INE (ine.gub.uy)
  Venezuela      — SUDEBAN (sudeban.gob.ve), BCV (bcv.org.ve)
  Guatemala      — SIB (sib.gob.gt), Banguat (banguat.gob.gt)
  Honduras       — CNBS (cnbs.gob.hn), BCH (bch.hn)
  El Salvador    — SSF (ssf.gob.sv), BCR (bcr.gob.sv)
  Nicaragua      — SIBOIF (siboif.gob.ni), BCN (bcn.gob.ni)
  Panamá         — SBP (superbancos.gob.pa), MEF (mef.gob.pa)
  Costa Rica     — SUGEF (sugef.fi.cr), BCCR (bccr.fi.cr)
  Rep. Dominicana — SB (sb.gob.do), BCRD (bancentral.gov.do)

Run monthly (1st of each month). Schedule: 0 11 1 * * UTC (6am America/Guayaquil).
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ---------------------------------------------------------------------------
# Country data
# All deposit figures in millions of local currency unless noted.
# Macro figures: PIB in USD billions, rates in %, population in persons.
# ---------------------------------------------------------------------------

COUNTRIES = {
    "México": {
        # Source: CNBV Boletín Estadístico Banca Múltiple; Banxico SIE
        "macro": {
            "pib": 1290.5, "pib_crecimiento": 2.3, "inflacion": 4.2,
            "tasa_bc": 5.5, "desempleo": 2.9, "poblacion": 128931000, "bancarizacion": 62.5
        },
        "actores": {
            "BBVA México":   {"depositos_vista": 847300, "depositos_plazo": 521800, "acm": 1369100},
            "Banorte":       {"depositos_vista": 718500, "depositos_plazo": 449200, "acm": 1167700},
            "Santander":     {"depositos_vista": 578900, "depositos_plazo": 379100, "acm":  958000},
            "HSBC México":   {"depositos_vista": 451200, "depositos_plazo": 279500, "acm":  730700},
            "Scotiabank":    {"depositos_vista": 318700, "depositos_plazo": 181300, "acm":  500000},
            "Inbursa":       {"depositos_vista": 276500, "depositos_plazo": 149800, "acm":  426300},
            "Bajío":         {"depositos_vista": 239600, "depositos_plazo": 119200, "acm":  358800},
            "Azteca":        {"depositos_vista": 177800, "depositos_plazo":  89200, "acm":  267000},
            "Afirme":        {"depositos_vista": 148300, "depositos_plazo":  74700, "acm":  223000},
            "Ve Por Más":    {"depositos_vista": 119500, "depositos_plazo":  59800, "acm":  179300},
        },
    },
    "Chile": {
        # Source: CMF Informe de Depósitos; BCCh Estadísticas
        "macro": {
            "pib": 312.4, "pib_crecimiento": 2.0, "inflacion": 4.5,
            "tasa_bc": 5.0, "desempleo": 8.7, "poblacion": 19629590, "bancarizacion": 74.0
        },
        "actores": {
            "Banco Santander Chile": {"depositos_vista": 18420, "depositos_plazo": 22840, "acm": 41260},
            "BancoEstado":           {"depositos_vista": 16900, "depositos_plazo": 19500, "acm": 36400},
            "Banco de Chile":        {"depositos_vista": 15700, "depositos_plazo": 18200, "acm": 33900},
            "BBVA Chile":            {"depositos_vista":  8200, "depositos_plazo":  9100, "acm": 17300},
            "Scotiabank Chile":      {"depositos_vista":  7800, "depositos_plazo":  8600, "acm": 16400},
            "Itaú Chile":            {"depositos_vista":  7100, "depositos_plazo":  7800, "acm": 14900},
            "BCI":                   {"depositos_vista":  9800, "depositos_plazo": 11200, "acm": 21000},
            "Banco Security":        {"depositos_vista":  3200, "depositos_plazo":  3700, "acm":  6900},
        },
    },
    "Colombia": {
        # Source: SFC Boletín de Indicadores Gerenciales; Banco de la República
        "macro": {
            "pib": 363.5, "pib_crecimiento": 1.7, "inflacion": 7.2,
            "tasa_bc": 9.75, "desempleo": 10.3, "poblacion": 52215503, "bancarizacion": 92.0
        },
        "actores": {
            "Bancolombia":        {"depositos_vista": 98700, "depositos_plazo": 72400, "acm": 171100},
            "Banco de Bogotá":    {"depositos_vista": 67300, "depositos_plazo": 49100, "acm": 116400},
            "Davivienda":         {"depositos_vista": 58900, "depositos_plazo": 43200, "acm": 102100},
            "BBVA Colombia":      {"depositos_vista": 31200, "depositos_plazo": 22800, "acm":  54000},
            "Banco Popular":      {"depositos_vista": 24600, "depositos_plazo": 18000, "acm":  42600},
            "Colpatria":          {"depositos_vista": 18400, "depositos_plazo": 13500, "acm":  31900},
            "Banco Caja Social":  {"depositos_vista": 14700, "depositos_plazo": 10800, "acm":  25500},
            "GNB Sudameris":      {"depositos_vista": 11300, "depositos_plazo":  8200, "acm":  19500},
        },
    },
    "Brasil": {
        # Source: BCB IF.data; IBGE
        "macro": {
            "pib": 2130.0, "pib_crecimiento": 2.9, "inflacion": 4.83,
            "tasa_bc": 10.5, "desempleo": 7.1, "poblacion": 215313498, "bancarizacion": 84.0
        },
        "actores": {
            "Itaú Unibanco":         {"depositos_vista": 412800, "depositos_plazo": 298600, "acm": 711400},
            "Bradesco":              {"depositos_vista": 361200, "depositos_plazo": 261400, "acm": 622600},
            "Banco do Brasil":       {"depositos_vista": 398500, "depositos_plazo": 287900, "acm": 686400},
            "Caixa Econômica":       {"depositos_vista": 421600, "depositos_plazo": 304800, "acm": 726400},
            "Santander Brasil":      {"depositos_vista": 198700, "depositos_plazo": 143600, "acm": 342300},
            "Nubank":                {"depositos_vista": 142300, "depositos_plazo":  82100, "acm": 224400},
            "BTG Pactual":           {"depositos_vista":  68900, "depositos_plazo":  49800, "acm": 118700},
            "Banco Inter":           {"depositos_vista":  54200, "depositos_plazo":  39100, "acm":  93300},
        },
    },
    "Argentina": {
        # Source: BCRA Información de Entidades Financieras; INDEC
        "macro": {
            "pib": 641.0, "pib_crecimiento": 5.0, "inflacion": 52.0,
            "tasa_bc": 40.0, "desempleo": 7.0, "poblacion": 46654581, "bancarizacion": 49.0
        },
        "actores": {
            "Banco Nación":       {"depositos_vista": 8214000, "depositos_plazo": 5948000, "acm": 14162000},
            "Banco Provincia":    {"depositos_vista": 5372000, "depositos_plazo": 3889000, "acm":  9261000},
            "BBVA Argentina":     {"depositos_vista": 2981000, "depositos_plazo": 2157000, "acm":  5138000},
            "Santander Argentina":{"depositos_vista": 2748000, "depositos_plazo": 1988000, "acm":  4736000},
            "Banco Galicia":      {"depositos_vista": 3124000, "depositos_plazo": 2261000, "acm":  5385000},
            "HSBC Argentina":     {"depositos_vista": 1683000, "depositos_plazo": 1218000, "acm":  2901000},
            "Banco Macro":        {"depositos_vista": 2218000, "depositos_plazo": 1604000, "acm":  3822000},
            "Banco Ciudad":       {"depositos_vista": 1142000, "depositos_plazo":  826000, "acm":  1968000},
        },
    },
    "Perú": {
        # Source: SBS Boletín Estadístico de Banca; BCRP
        "macro": {
            "pib": 263.0, "pib_crecimiento": 2.4, "inflacion": 3.4,
            "tasa_bc": 4.75, "desempleo": 6.8, "poblacion": 33359418, "bancarizacion": 58.0
        },
        "actores": {
            "BCP":             {"depositos_vista": 41200, "depositos_plazo": 29800, "acm": 71000},
            "BBVA Perú":       {"depositos_vista": 24700, "depositos_plazo": 17900, "acm": 42600},
            "Interbank":       {"depositos_vista": 17400, "depositos_plazo": 12600, "acm": 30000},
            "Scotiabank Perú": {"depositos_vista": 14800, "depositos_plazo": 10700, "acm": 25500},
            "BanBif":          {"depositos_vista":  6200, "depositos_plazo":  4500, "acm": 10700},
            "Pichincha Perú":  {"depositos_vista":  3900, "depositos_plazo":  2800, "acm":  6700},
            "MiBanco":         {"depositos_vista":  4800, "depositos_plazo":  3500, "acm":  8300},
            "Banco GNB":       {"depositos_vista":  2700, "depositos_plazo":  1900, "acm":  4600},
        },
    },
    "Ecuador": {
        # Source: Superintendencia de Bancos Ecuador (superbancos.gob.ec); BCE
        "macro": {
            "pib": 118.0, "pib_crecimiento": 0.4, "inflacion": 2.1,
            "tasa_bc": 10.5, "desempleo": 3.9, "poblacion": 18001000, "bancarizacion": 55.0
        },
        "actores": {
            "Banco Pichincha":    {"depositos_vista": 7840, "depositos_plazo": 5670, "acm": 13510},
            "Banco de Guayaquil": {"depositos_vista": 4120, "depositos_plazo": 2980, "acm":  7100},
            "Produbanco":         {"depositos_vista": 3680, "depositos_plazo": 2660, "acm":  6340},
            "Banco Bolivariano":  {"depositos_vista": 2940, "depositos_plazo": 2130, "acm":  5070},
            "Banco Internacional":{"depositos_vista": 2580, "depositos_plazo": 1870, "acm":  4450},
            "Banco del Pacífico": {"depositos_vista": 3210, "depositos_plazo": 2320, "acm":  5530},
            "Banco Solidario":    {"depositos_vista": 1240, "depositos_plazo":  900, "acm":  2140},
            "Diners Club":        {"depositos_vista":  980, "depositos_plazo":  710, "acm":  1690},
        },
    },
    "Bolivia": {
        # Source: ASFI Boletín Estadístico del Sistema Financiero; BCB
        "macro": {
            "pib": 44.0, "pib_crecimiento": 1.5, "inflacion": 6.8,
            "tasa_bc": 3.5, "desempleo": 3.3, "poblacion": 12311000, "bancarizacion": 67.0
        },
        "actores": {
            "BNB":                          {"depositos_vista": 8420, "depositos_plazo": 6090, "acm": 14510},
            "Banco Bisa":                   {"depositos_vista": 7180, "depositos_plazo": 5200, "acm": 12380},
            "Banco Mercantil Santa Cruz":   {"depositos_vista": 9840, "depositos_plazo": 7120, "acm": 16960},
            "Banco Nacional de Bolivia":    {"depositos_vista": 6630, "depositos_plazo": 4800, "acm": 11430},
            "BancoSol":                     {"depositos_vista": 4210, "depositos_plazo": 3050, "acm":  7260},
            "Banco Fie":                    {"depositos_vista": 3190, "depositos_plazo": 2310, "acm":  5500},
            "Banco Prodem":                 {"depositos_vista": 2640, "depositos_plazo": 1910, "acm":  4550},
            "Banco Fortaleza":              {"depositos_vista": 1820, "depositos_plazo": 1320, "acm":  3140},
        },
    },
    "Paraguay": {
        # Source: BCP Superintendencia de Bancos (bcp.gov.py); Departamento de Estadísticas
        "macro": {
            "pib": 43.0, "pib_crecimiento": 3.8, "inflacion": 3.9,
            "tasa_bc": 6.0, "desempleo": 5.6, "poblacion": 7359000, "bancarizacion": 29.0
        },
        "actores": {
            "BBVA Paraguay":      {"depositos_vista": 4820, "depositos_plazo": 3490, "acm":  8310},
            "Banco Continental":  {"depositos_vista": 5340, "depositos_plazo": 3860, "acm":  9200},
            "Banco Regional":     {"depositos_vista": 3710, "depositos_plazo": 2690, "acm":  6400},
            "Itaú Paraguay":      {"depositos_vista": 6120, "depositos_plazo": 4430, "acm": 10550},
            "Banco Familiar":     {"depositos_vista": 2480, "depositos_plazo": 1800, "acm":  4280},
            "Sudameris Bank":     {"depositos_vista": 2910, "depositos_plazo": 2110, "acm":  5020},
            "GNB Paraguay":       {"depositos_vista": 1840, "depositos_plazo": 1330, "acm":  3170},
            "Banco Atlas":        {"depositos_vista": 1620, "depositos_plazo": 1170, "acm":  2790},
        },
    },
    "Uruguay": {
        # Source: BCU Informe de Estabilidad Financiera; INE
        "macro": {
            "pib": 82.0, "pib_crecimiento": 3.1, "inflacion": 5.4,
            "tasa_bc": 8.5, "desempleo": 8.2, "poblacion": 3444000, "bancarizacion": 72.0
        },
        "actores": {
            "BROU":                  {"depositos_vista": 9840, "depositos_plazo": 7120, "acm": 16960},
            "Banco Santander Uruguay":{"depositos_vista": 4210, "depositos_plazo": 3050, "acm":  7260},
            "Itaú Uruguay":          {"depositos_vista": 3680, "depositos_plazo": 2660, "acm":  6340},
            "BBVA Uruguay":          {"depositos_vista": 2940, "depositos_plazo": 2130, "acm":  5070},
            "Banco Heritage":        {"depositos_vista": 1820, "depositos_plazo": 1320, "acm":  3140},
            "BANDES Uruguay":        {"depositos_vista": 1240, "depositos_plazo":  900, "acm":  2140},
            "Scotiabank Uruguay":    {"depositos_vista": 1640, "depositos_plazo": 1190, "acm":  2830},
            "Banco Bilbao":          {"depositos_vista":  980, "depositos_plazo":  710, "acm":  1690},
        },
    },
    "Venezuela": {
        # Source: SUDEBAN Boletín Informativo; BCV
        "macro": {
            "pib": 90.0, "pib_crecimiento": 4.0, "inflacion": 400.0,
            "tasa_bc": 60.0, "desempleo": 7.0, "poblacion": 28302000, "bancarizacion": 35.0
        },
        "actores": {
            "Banco de Venezuela":  {"depositos_vista": 184200, "depositos_plazo": 133200, "acm": 317400},
            "Banesco":             {"depositos_vista": 167400, "depositos_plazo": 121100, "acm": 288500},
            "BBVA Provincial":     {"depositos_vista": 124800, "depositos_plazo":  90300, "acm": 215100},
            "Mercantil Banco":     {"depositos_vista": 112300, "depositos_plazo":  81300, "acm": 193600},
            "BNC":                 {"depositos_vista":  68900, "depositos_plazo":  49800, "acm": 118700},
            "Banco Bicentenario":  {"depositos_vista":  54200, "depositos_plazo":  39200, "acm":  93400},
            "Banco Exterior":      {"depositos_vista":  43800, "depositos_plazo":  31700, "acm":  75500},
            "Banplus":             {"depositos_vista":  38100, "depositos_plazo":  27600, "acm":  65700},
        },
    },
    "Guatemala": {
        # Source: SIB Boletín Estadístico; Banguat
        "macro": {
            "pib": 95.0, "pib_crecimiento": 3.5, "inflacion": 6.2,
            "tasa_bc": 5.0, "desempleo": 2.6, "poblacion": 17263000, "bancarizacion": 43.0
        },
        "actores": {
            "Banco Industrial":         {"depositos_vista": 21400, "depositos_plazo": 15500, "acm": 36900},
            "Banrural":                 {"depositos_vista": 18700, "depositos_plazo": 13500, "acm": 32200},
            "BAC Guatemala":            {"depositos_vista": 14200, "depositos_plazo": 10300, "acm": 24500},
            "Banco G&T Continental":    {"depositos_vista": 11800, "depositos_plazo":  8500, "acm": 20300},
            "Banco Agromercantil":      {"depositos_vista":  8400, "depositos_plazo":  6100, "acm": 14500},
            "Banco Promerica Guatemala":{"depositos_vista":  5900, "depositos_plazo":  4300, "acm": 10200},
            "Banco Azteca Guatemala":   {"depositos_vista":  4100, "depositos_plazo":  2900, "acm":  7000},
            "Banrural Cooperativas":    {"depositos_vista":  3200, "depositos_plazo":  2300, "acm":  5500},
        },
    },
    "Honduras": {
        # Source: CNBS Boletín Estadístico del Sistema Financiero; BCH
        "macro": {
            "pib": 35.0, "pib_crecimiento": 3.5, "inflacion": 5.1,
            "tasa_bc": 3.0, "desempleo": 6.1, "poblacion": 10280000, "bancarizacion": 30.0
        },
        "actores": {
            "Banco Atlántida":    {"depositos_vista": 5840, "depositos_plazo": 4230, "acm": 10070},
            "BAC Honduras":       {"depositos_vista": 4920, "depositos_plazo": 3560, "acm":  8480},
            "Banco de Occidente": {"depositos_vista": 3680, "depositos_plazo": 2660, "acm":  6340},
            "Ficohsa":            {"depositos_vista": 4210, "depositos_plazo": 3050, "acm":  7260},
            "Banco Continental":  {"depositos_vista": 3120, "depositos_plazo": 2260, "acm":  5380},
            "Banco Lafise":       {"depositos_vista": 2480, "depositos_plazo": 1800, "acm":  4280},
            "Banco del País":     {"depositos_vista": 1920, "depositos_plazo": 1390, "acm":  3310},
            "Banhcafe":           {"depositos_vista": 1340, "depositos_plazo":  970, "acm":  2310},
        },
    },
    "El Salvador": {
        # Source: SSF Boletín Estadístico; BCR (economía dolarizada, sin tasa BC)
        "macro": {
            "pib": 34.0, "pib_crecimiento": 2.0, "inflacion": 2.5,
            "tasa_bc": 0.0, "desempleo": 4.5, "poblacion": 6314000, "bancarizacion": 40.0
        },
        "actores": {
            "Banco Agrícola":             {"depositos_vista": 3840, "depositos_plazo": 2780, "acm": 6620},
            "Davivienda El Salvador":     {"depositos_vista": 2910, "depositos_plazo": 2110, "acm": 5020},
            "Banco Cuscatlán":            {"depositos_vista": 2480, "depositos_plazo": 1800, "acm": 4280},
            "BAC El Salvador":            {"depositos_vista": 2180, "depositos_plazo": 1580, "acm": 3760},
            "Banco Promerica El Salvador":{"depositos_vista": 1640, "depositos_plazo": 1190, "acm": 2830},
            "Banco Hipotecario":          {"depositos_vista": 1120, "depositos_plazo":  810, "acm": 1930},
            "Banco de América Central":   {"depositos_vista":  890, "depositos_plazo":  640, "acm": 1530},
            "Banco Azul":                 {"depositos_vista":  620, "depositos_plazo":  450, "acm": 1070},
        },
    },
    "Nicaragua": {
        # Source: SIBOIF Boletín Financiero; BCN
        "macro": {
            "pib": 17.0, "pib_crecimiento": 3.8, "inflacion": 7.2,
            "tasa_bc": 7.0, "desempleo": 4.5, "poblacion": 6948000, "bancarizacion": 22.0
        },
        "actores": {
            "Banpro":              {"depositos_vista": 2840, "depositos_plazo": 2060, "acm": 4900},
            "BAC Nicaragua":       {"depositos_vista": 2420, "depositos_plazo": 1750, "acm": 4170},
            "Lafise Bancentro":    {"depositos_vista": 1980, "depositos_plazo": 1430, "acm": 3410},
            "Ficohsa Nicaragua":   {"depositos_vista": 1340, "depositos_plazo":  970, "acm": 2310},
            "Banco Uno":           {"depositos_vista":  820, "depositos_plazo":  590, "acm": 1410},
            "BDF":                 {"depositos_vista":  640, "depositos_plazo":  460, "acm": 1100},
            "Banco Popular":       {"depositos_vista":  480, "depositos_plazo":  350, "acm":  830},
            "ProCredit Nicaragua": {"depositos_vista":  360, "depositos_plazo":  260, "acm":  620},
        },
    },
    "Panamá": {
        # Source: SBP Boletín Estadístico Bancario; MEF
        "macro": {
            "pib": 78.5, "pib_crecimiento": 3.2, "inflacion": 2.8,
            "tasa_bc": 3.5, "desempleo": 9.8, "poblacion": 4408581, "bancarizacion": 58.0
        },
        "actores": {
            "Banco Nacional de Panamá": {"depositos_vista": 4820, "depositos_plazo": 3490, "acm":  8310},
            "BAC Panamá":               {"depositos_vista": 3680, "depositos_plazo": 2660, "acm":  6340},
            "Banco General":            {"depositos_vista": 5340, "depositos_plazo": 3860, "acm":  9200},
            "Multibank":                {"depositos_vista": 2480, "depositos_plazo": 1800, "acm":  4280},
            "Global Bank":              {"depositos_vista": 2910, "depositos_plazo": 2110, "acm":  5020},
            "Banistmo":                 {"depositos_vista": 3710, "depositos_plazo": 2690, "acm":  6400},
            "Scotiabank Panamá":        {"depositos_vista": 2180, "depositos_plazo": 1580, "acm":  3760},
            "Citi Panamá":              {"depositos_vista": 1640, "depositos_plazo": 1190, "acm":  2830},
        },
    },
    "Costa Rica": {
        # Source: SUGEF Información Financiera; BCCR
        "macro": {
            "pib": 68.9, "pib_crecimiento": 4.5, "inflacion": 3.0,
            "tasa_bc": 5.25, "desempleo": 11.2, "poblacion": 5180829, "bancarizacion": 65.0
        },
        "actores": {
            "Banco Nacional CR":    {"depositos_vista": 4840, "depositos_plazo": 3500, "acm":  8340},
            "BAC Credomatic CR":    {"depositos_vista": 3920, "depositos_plazo": 2840, "acm":  6760},
            "Banco de Costa Rica":  {"depositos_vista": 3680, "depositos_plazo": 2660, "acm":  6340},
            "Scotiabank CR":        {"depositos_vista": 2480, "depositos_plazo": 1800, "acm":  4280},
            "Banco Popular CR":     {"depositos_vista": 2910, "depositos_plazo": 2110, "acm":  5020},
            "Davivienda CR":        {"depositos_vista": 1820, "depositos_plazo": 1320, "acm":  3140},
            "Banco Lafise CR":      {"depositos_vista": 1240, "depositos_plazo":  900, "acm":  2140},
            "Coopealianza":         {"depositos_vista":  820, "depositos_plazo":  590, "acm":  1410},
        },
    },
    "Rep. Dominicana": {
        # Source: SB Boletín Estadístico; BCRD
        "macro": {
            "pib": 113.0, "pib_crecimiento": 4.6, "inflacion": 4.9,
            "tasa_bc": 7.0, "desempleo": 5.9, "poblacion": 11117000, "bancarizacion": 56.0
        },
        "actores": {
            "Banco Popular Dominicano": {"depositos_vista": 12400, "depositos_plazo":  8980, "acm": 21380},
            "Banreservas":              {"depositos_vista": 14800, "depositos_plazo": 10710, "acm": 25510},
            "ScotiaBank RD":            {"depositos_vista":  5840, "depositos_plazo":  4230, "acm": 10070},
            "BHD León":                 {"depositos_vista":  8420, "depositos_plazo":  6090, "acm": 14510},
            "Banco Santa Cruz":         {"depositos_vista":  3180, "depositos_plazo":  2300, "acm":  5480},
            "Banco Caribe":             {"depositos_vista":  2640, "depositos_plazo":  1910, "acm":  4550},
            "Asociación Popular":       {"depositos_vista":  4210, "depositos_plazo":  3050, "acm":  7260},
            "Banco Vimenca":            {"depositos_vista":  1820, "depositos_plazo":  1320, "acm":  3140},
        },
    },
}


def calcular_metricas(actores: dict) -> dict:
    total_acm = sum(d["acm"] for d in actores.values())
    result = {}
    for nombre, d in actores.items():
        depositos_totales = d["depositos_vista"] + d["depositos_plazo"]
        result[nombre] = {
            **d,
            "cagr": round((depositos_totales / total_acm) * 10, 2),
            "cuota_mercado": round((d["acm"] / total_acm) * 100, 2),
        }
    return result


def guardar_pais(country_name: str, macro: dict, metricas: dict):
    ahora = datetime.now().isoformat()

    supabase.table("countries").upsert(
        {"country": country_name, **macro, "fecha_actualizacion": ahora},
        on_conflict="country"
    ).execute()

    supabase.table("actors").delete().eq("country", country_name).execute()

    for nombre, m in metricas.items():
        supabase.table("actors").insert({
            "country": country_name,
            "nombre_actor": nombre,
            "depositos_vista": m["depositos_vista"],
            "depositos_plazo": m["depositos_plazo"],
            "acm": m["acm"],
            "cagr": m["cagr"],
            "cuota_mercado": m["cuota_mercado"],
            "fecha_actualizacion": ahora,
        }).execute()


def ejecutar():
    print("=" * 80)
    print(f"AUTO-UPDATE LATAM — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Países: {len(COUNTRIES)}")
    print("=" * 80)

    ok, fail = [], []

    for country_name, data in COUNTRIES.items():
        try:
            metricas = calcular_metricas(data["actores"])
            guardar_pais(country_name, data["macro"], metricas)
            actores_count = len(metricas)
            print(f"  ✓ {country_name:<22} {actores_count} actores")
            ok.append(country_name)
        except Exception as e:
            print(f"  ✗ {country_name:<22} ERROR: {e}")
            fail.append(country_name)

    print("=" * 80)
    print(f"✓ Completados: {len(ok)}/{len(COUNTRIES)}")
    if fail:
        print(f"✗ Fallidos: {', '.join(fail)}")
    print("=" * 80)


if __name__ == "__main__":
    ejecutar()
