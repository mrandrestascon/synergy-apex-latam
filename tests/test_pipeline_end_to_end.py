"""
End-to-end pipeline test — dry run, no Supabase writes.
Uses mock Supabase data to verify the full flow.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.data_pipeline.metrics import cagr_pct, recalculate_market_shares, deposit_total


MOCK_ACTORS = [
    {"country": "TestLand", "nombre_actor": "Bank A", "depositos_vista": 1000, "depositos_plazo": 2000, "acm": 3000, "cuota_mercado": None, "cagr": None},
    {"country": "TestLand", "nombre_actor": "Bank B", "depositos_vista": 500,  "depositos_plazo": 1000, "acm": 1500, "cuota_mercado": None, "cagr": None},
    {"country": "TestLand", "nombre_actor": "Bank C", "depositos_vista": 500,  "depositos_plazo": 1000, "acm": 1500, "cuota_mercado": None, "cagr": None},
]

MOCK_COUNTRY_ROW = {
    "country": "TestLand",
    "pib": 100.0, "pib_crecimiento": 3.0, "inflacion": 4.0,
    "tasa_bc": 5.0, "desempleo": 5.0, "poblacion": 5_000_000,
    "bancarizacion": 60.0,
}


class TestDepositAggregation:
    def test_deposit_totals_correct(self):
        totals = deposit_total(MOCK_ACTORS, "TestLand")
        assert totals["depositos_vista"] == 2000
        assert totals["depositos_plazo"] == 4000
        assert totals["acm"] == 6000

    def test_market_shares_sum_to_100(self):
        actors = [a.copy() for a in MOCK_ACTORS]
        recalculate_market_shares(actors)
        total = sum(a["cuota_mercado"] for a in actors)
        assert abs(total - 100.0) < 0.01

    def test_bank_a_gets_50_percent(self):
        actors = [a.copy() for a in MOCK_ACTORS]
        recalculate_market_shares(actors)
        bank_a = next(a for a in actors if a["nombre_actor"] == "Bank A")
        assert bank_a["cuota_mercado"] == pytest.approx(50.0)


class TestProvenance:
    def test_provenance_record_has_value(self):
        from src.data_pipeline.provenance import ProvenanceRecord
        p = ProvenanceRecord.from_reference(9.0, "banxico_sf61745", "Banxico", 2025, "percent")
        assert p.value == 9.0
        assert p.fetch_method == "reference"
        assert p.is_estimated is True

    def test_missing_provenance(self):
        from src.data_pipeline.provenance import ProvenanceRecord
        p = ProvenanceRecord.missing("unknown", "Unknown source")
        assert p.value is None
        assert p.confidence == "low"

    def test_to_dict_is_json_serialisable(self):
        import json
        from src.data_pipeline.provenance import ProvenanceRecord
        p = ProvenanceRecord.from_reference(5.5, "test", "Test", 2024)
        d = p.to_dict()
        json.dumps(d)  # must not raise


class TestCagrInContext:
    def test_mexico_deposits_cagr(self):
        # Realistic México deposit growth scenario
        plazo_2021 = 1_800_000  # million MXN
        plazo_2026 = 2_303_600
        r = cagr_pct(plazo_2021, plazo_2026, 5)
        assert r is not None
        assert 4.0 <= r <= 10.0, f"Unexpected CAGR: {r}%"

    def test_argentina_high_inflation_cagr(self):
        # Argentina deposits in ARS grow fast due to inflation
        start, end = 10_000_000, 47_373_000
        r = cagr_pct(start, end, 5)
        assert r is not None
        assert r > 20.0  # Expected high nominal CAGR in ARS


class TestValidatorIntegration:
    def test_full_validation_run_clean_data(self):
        from src.data_pipeline.validators import run_all_validations, summarise
        actors = [a.copy() for a in MOCK_ACTORS]
        recalculate_market_shares(actors)
        results = run_all_validations("TestLand", MOCK_COUNTRY_ROW, actors)
        s = summarise(results)
        assert s["failed"] == 0, f"Unexpected failures: {s['errors']}"

    def test_full_validation_catches_bad_data(self):
        from src.data_pipeline.validators import run_all_validations, summarise
        bad_row = {**MOCK_COUNTRY_ROW, "inflacion": -99.0}
        results = run_all_validations("TestLand", bad_row, MOCK_ACTORS)
        s = summarise(results)
        assert s["failed"] > 0
