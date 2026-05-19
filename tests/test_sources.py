"""
Tests for source accessibility — probes the 3 free APIs with no auth.
Marked as integration tests; skipped in offline/CI environments.

Run:  pytest tests/test_sources.py -v -m integration
Skip: pytest tests/ -m "not integration"
"""
import pytest
from src.data_pipeline import fetchers, parsers


pytestmark = pytest.mark.integration


class TestBCRPPeru:
    """BCRP Peru — free, no auth, stable API."""

    def test_fetch_tasa_bc(self):
        raw = fetchers.fetch_bcrp("PD04706PD", n_periods=2)
        assert raw is not None, "BCRP API unreachable"
        assert "periods" in raw

    def test_parse_tasa_bc(self):
        raw = fetchers.fetch_bcrp("PD04706PD", n_periods=2)
        if not raw:
            pytest.skip("BCRP unreachable")
        val, asof = parsers.parse_bcrp_serie(raw)
        assert val is not None
        assert 0.5 <= val <= 20.0, f"Unexpected rate: {val}"
        assert asof != ""

    def test_fetch_inflacion(self):
        raw = fetchers.fetch_bcrp("PD39462PD", n_periods=2)
        if not raw:
            pytest.skip("BCRP unreachable")
        val, _ = parsers.parse_bcrp_serie(raw)
        assert val is not None
        assert -5.0 <= val <= 20.0


class TestBCBBrazil:
    """BCB Brazil SGS — free, no auth."""

    def test_fetch_selic(self):
        raw = fetchers.fetch_bcb_sgs(432, n_periods=1)
        assert raw is not None, "BCB SGS unreachable"
        assert isinstance(raw, list)
        assert len(raw) >= 1

    def test_parse_selic(self):
        raw = fetchers.fetch_bcb_sgs(432, n_periods=1)
        if not raw:
            pytest.skip("BCB unreachable")
        val, asof = parsers.parse_bcb_sgs(raw)
        assert val is not None
        assert 5.0 <= val <= 25.0, f"Unexpected Selic: {val}"

    def test_fetch_ipca(self):
        raw = fetchers.fetch_bcb_sgs(13522, n_periods=1)
        if not raw:
            pytest.skip("BCB unreachable")
        val, _ = parsers.parse_bcb_sgs(raw)
        assert val is not None
        assert 0.0 <= val <= 20.0


class TestExchangeRates:
    """open.er-api.com — free, no auth."""

    def test_fetch_rates(self):
        raw = fetchers.fetch_exchange_rates()
        assert raw is not None, "open.er-api unreachable"
        assert raw.get("result") == "success"

    def test_parse_rates(self):
        raw = fetchers.fetch_exchange_rates()
        if not raw:
            pytest.skip("open.er-api unreachable")
        rates, date = parsers.parse_exchange_rates(raw)
        assert rates is not None
        assert "MXN" in rates
        assert "BRL" in rates
        assert "CLP" in rates
        # Sanity: MXN should be 10–25 per USD
        assert 10.0 <= rates["MXN"] <= 30.0, f"Suspicious MXN rate: {rates['MXN']}"


class TestParserFallbacks:
    """Parsers must return (None, '') on bad input — never raise."""

    def test_banxico_none_input(self):
        val, d = parsers.parse_banxico_serie(None)
        assert val is None
        assert d == ""

    def test_bcb_empty_list(self):
        val, d = parsers.parse_bcb_sgs([])
        assert val is None

    def test_bcrp_empty_periods(self):
        val, d = parsers.parse_bcrp_serie({"periods": []})
        assert val is None

    def test_ibge_bad_structure(self):
        val, d = parsers.parse_ibge_sidra(None)
        assert val is None
