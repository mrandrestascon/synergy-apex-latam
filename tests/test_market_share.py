"""Tests for market share — guarantees sum-to-100% and documented denominator."""
import pytest
from src.data_pipeline.metrics import market_share, recalculate_market_shares, verify_shares_sum_to_100


ACTORS_MX = [
    {"country": "México", "nombre_actor": "BBVA", "acm": 600},
    {"country": "México", "nombre_actor": "Banorte", "acm": 400},
    {"country": "México", "nombre_actor": "Santander", "acm": 200},
    {"country": "Brasil", "nombre_actor": "Itaú", "acm": 1000},
]


class TestMarketShare:
    def test_basic_share(self):
        result = market_share(600, ACTORS_MX, country="México")
        # 600 / (600+400+200) = 50%
        assert result == pytest.approx(50.0, abs=0.01)

    def test_shares_sum_to_100(self):
        actors = [a for a in ACTORS_MX if a["country"] == "México"]
        recalculate_market_shares(actors)
        total = sum(a["cuota_mercado"] for a in actors)
        assert abs(total - 100.0) < 0.1

    def test_country_isolation(self):
        # Brasil actor should not affect México shares
        share = market_share(1000, ACTORS_MX, country="Brasil")
        assert share == pytest.approx(100.0)

    def test_zero_total_returns_none(self):
        zero_actors = [{"country": "X", "acm": 0}, {"country": "X", "acm": 0}]
        assert market_share(0, zero_actors, country="X") is None

    def test_recalculate_does_not_lose_any_actor(self):
        actors = [a.copy() for a in ACTORS_MX if a["country"] == "México"]
        result = recalculate_market_shares(actors)
        assert len(result) == 3

    def test_recalculate_sets_none_for_zero_total(self):
        actors = [{"country": "Y", "acm": 0, "nombre_actor": "BankA"}]
        recalculate_market_shares(actors)
        assert actors[0]["cuota_mercado"] is None

    def test_verify_shares_sum_passes(self):
        actors = [a.copy() for a in ACTORS_MX if a["country"] == "México"]
        recalculate_market_shares(actors)
        assert verify_shares_sum_to_100(actors, "México") is True

    def test_verify_shares_sum_fails_with_bad_data(self):
        actors = [
            {"country": "Z", "cuota_mercado": 60.0},
            {"country": "Z", "cuota_mercado": 60.0},  # sums to 120
        ]
        assert verify_shares_sum_to_100(actors, "Z") is False

    def test_single_bank_gets_100_percent(self):
        actors = [{"country": "A", "acm": 999}]
        recalculate_market_shares(actors)
        assert actors[0]["cuota_mercado"] == pytest.approx(100.0)
