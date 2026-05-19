"""
Unified HTTP fetcher layer.
All network calls go through here — timeout, retry, error handling in one place.
"""
from __future__ import annotations
import os
import time
import logging
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
MAX_RETRIES     = 3
BACKOFF_FACTOR  = 1.5


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://",  HTTPAdapter(max_retries=retry))
    return s


# ── Generic GET ────────────────────────────────────────────────────────────

def fetch_json(url: str, headers: Optional[dict] = None, params: Optional[dict] = None) -> Optional[dict | list]:
    try:
        r = _session().get(url, headers=headers or {}, params=params or {}, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning("fetch_json FAIL [%s]: %s", url[:80], exc)
        return None


def fetch_text(url: str, headers: Optional[dict] = None) -> Optional[str]:
    try:
        r = _session().get(url, headers=headers or {}, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        log.warning("fetch_text FAIL [%s]: %s", url[:80], exc)
        return None


def fetch_bytes(url: str) -> Optional[bytes]:
    try:
        r = _session().get(url, timeout=30)
        r.raise_for_status()
        return r.content
    except Exception as exc:
        log.warning("fetch_bytes FAIL [%s]: %s", url[:80], exc)
        return None


# ── Source-specific fetchers ───────────────────────────────────────────────

def fetch_banxico(serie_id: str, token: Optional[str] = None) -> Optional[dict]:
    """
    Banxico SIE REST API — latest value for a series.
    Requires Bmx-Token (free, register at banxico.org.mx).
    Falls back gracefully when token missing.
    """
    token = token or os.getenv("BANXICO_TOKEN", "")
    if not token:
        log.info("BANXICO_TOKEN not set — Banxico sources will use reference values")
        return None
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{serie_id}/datos/oportuno"
    return fetch_json(url, headers={"Bmx-Token": token})


def fetch_bcb_sgs(serie_id: int, n_periods: int = 1) -> Optional[list]:
    """BCB SGS (Sistema Gerenciador de Séries Temporais) — free, no key."""
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados/ultimos/{n_periods}?formato=json"
    return fetch_json(url)


def fetch_bcrp(serie_id: str, n_periods: int = 4) -> Optional[dict]:
    """BCRP estadísticas API — free, no key required."""
    url = f"https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{serie_id}/json"
    return fetch_json(url)


def fetch_ibge_sidra(agregado: str, variavel: str, periodos: str = "-1") -> Optional[dict]:
    """IBGE SIDRA API v3 — free, no key."""
    url = (
        f"https://servicodados.ibge.gov.br/api/v3/agregados/{agregado}"
        f"/periodos/{periodos}/variaveis/{variavel}?localidades=N1[all]"
    )
    return fetch_json(url)


def fetch_exchange_rates() -> Optional[dict]:
    """open.er-api.com — free exchange rates, USD base."""
    return fetch_json("https://open.er-api.com/v6/latest/USD")
