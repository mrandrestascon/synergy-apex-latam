"""Tests for data quality validators."""
import pytest
from src.data_pipeline.validators import (
    validate_bounds, validate_no_negative, validate_dollarised_rate,
    validate_market_shares_sum, run_all_validations, summarise,
)


class TestBoundsValidation:
    def test_valid_pib(self):
        r = validate_bounds("México", "pib", 1347.0)
        assert r.passed

    def test_pib_zero_fails(self):
        r = validate_bounds("México", "pib", 0.0)
        assert not r.passed

    def test_pib_none_fails(self):
        r = validate_bounds("México", "pib", None)
        assert not r.passed

    def test_inflation_very_high_still_valid(self):
        # Venezuela can have 200–400%
        r = validate_bounds("Venezuela", "inflacion", 400.0)
        assert r.passed

    def test_inflation_negative_fails(self):
        r = validate_bounds("Ecuador", "inflacion", -10.0)
        assert not r.passed

    def test_population_in_range(self):
        r = validate_bounds("México", "poblacion", 129_000_000)
        assert r.passed

    def test_tasa_bc_none_allowed(self):
        r = validate_bounds("Ecuador", "tasa_bc", None)
        assert r.passed  # allow_none=True for tasa_bc

    def test_unemployment_out_of_range(self):
        r = validate_bounds("Costa Rica", "desempleo", 50.0)
        assert not r.passed


class TestNegativeValues:
    def test_positive_pib_ok(self):
        r = validate_no_negative("Chile", "pib", 335.4)
        assert r.passed

    def test_negative_pib_fails(self):
        r = validate_no_negative("Chile", "pib", -10.0)
        assert not r.passed

    def test_negative_population_fails(self):
        r = validate_no_negative("Brasil", "poblacion", -1)
        assert not r.passed

    def test_negative_deposits_fails(self):
        r = validate_no_negative("México", "depositos_plazo", -5.0)
        assert not r.passed


class TestDollarisedRate:
    def test_ecuador_null_rate_ok(self):
        r = validate_dollarised_rate("Ecuador", None)
        assert r.passed

    def test_ecuador_nonzero_rate_fails(self):
        r = validate_dollarised_rate("Ecuador", 5.0)
        assert not r.passed

    def test_non_dollarised_any_rate_ok(self):
        r = validate_dollarised_rate("México", 9.0)
        assert r.passed

    def test_el_salvador_null_ok(self):
        r = validate_dollarised_rate("El Salvador", None)
        assert r.passed


class TestMarketSharesSum:
    def test_correct_shares_pass(self):
        actors = [
            {"country": "X", "cuota_mercado": 60.0},
            {"country": "X", "cuota_mercado": 40.0},
        ]
        r = validate_market_shares_sum("X", actors)
        assert r.passed

    def test_wrong_sum_fails(self):
        actors = [
            {"country": "X", "cuota_mercado": 60.0},
            {"country": "X", "cuota_mercado": 60.0},
        ]
        r = validate_market_shares_sum("X", actors)
        assert not r.passed

    def test_empty_actors_fail(self):
        r = validate_market_shares_sum("X", [])
        assert not r.passed


class TestSummarize:
    def test_all_pass(self):
        r1 = validate_bounds("México", "pib", 1347.0)
        r2 = validate_bounds("México", "desempleo", 2.8)
        s = summarise([r1, r2])
        assert s["failed"] == 0
        assert s["passed"] == 2

    def test_mixed(self):
        r1 = validate_bounds("México", "pib", 1347.0)
        r2 = validate_bounds("México", "pib", -1.0)
        s = summarise([r1, r2])
        assert s["failed"] == 1
        assert s["passed"] == 1
        assert len(s["errors"]) == 1
