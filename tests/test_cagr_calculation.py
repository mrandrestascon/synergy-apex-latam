"""Tests for CAGR calculation — verifies mathematical correctness."""
import pytest
import math
from src.data_pipeline.metrics import cagr, cagr_pct, cagr_series


class TestCagrFormula:
    def test_known_value(self):
        # 100 * 1.04930^10 = 161.807 → 4.93% CAGR
        result = cagr(100, 161.807, 10)
        assert result is not None
        assert abs(result - 0.04930) < 0.0001

    def test_flat_growth(self):
        assert cagr(100, 100, 5) == pytest.approx(0.0)

    def test_double_in_5_years(self):
        # 100 → 200 in 5 years ≈ 14.87%
        result = cagr(100, 200, 5)
        assert result is not None
        assert abs(result - 0.14870) < 0.0001

    def test_returns_none_for_zero_start(self):
        assert cagr(0, 100, 5) is None

    def test_returns_none_for_negative_start(self):
        assert cagr(-50, 100, 5) is None

    def test_returns_none_for_none_inputs(self):
        assert cagr(None, 100, 5) is None
        assert cagr(100, None, 5) is None

    def test_raises_for_invalid_years(self):
        with pytest.raises(ValueError):
            cagr(100, 200, 0)
        with pytest.raises(ValueError):
            cagr(100, 200, -1)

    def test_cagr_pct_rounding(self):
        result = cagr_pct(100, 200, 5, decimals=2)
        assert result == pytest.approx(14.87, abs=0.01)

    def test_cagr_pct_returns_none_on_bad_input(self):
        assert cagr_pct(0, 100, 5) is None

    def test_cagr_series_basic(self):
        # Series going 100 → 200 over 5 steps → CAGR ~14.87%
        series = [100, 120, 140, 160, 180, 200]
        result = cagr_series(series)
        assert result is not None
        assert abs(result - 14.87) < 0.1

    def test_cagr_series_skips_none(self):
        series = [100, None, None, None, None, 200]
        result = cagr_series(series)
        assert result is not None

    def test_cagr_series_too_short(self):
        assert cagr_series([100]) is None
        assert cagr_series([]) is None

    def test_formula_inverse(self):
        # If CAGR = r, then start * (1+r)^n should equal end
        start, end, years = 50.0, 133.8, 7
        r = cagr(start, end, years)
        reconstructed = start * (1 + r) ** years
        assert abs(reconstructed - end) < 0.01
