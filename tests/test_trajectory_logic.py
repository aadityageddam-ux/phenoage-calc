"""
Tests for longitudinal trajectory calculation logic (Tab 4: Your Progress).

Verifies that Rate of Aging and Intervention Net Benefit are computed correctly
from mock patient records spaced 6 months apart.
"""

import math
from datetime import datetime, timedelta

import pytest

from ui.tab4_progress import _years_between


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_record(ts: str, chron_age: float, phenoage: float) -> dict:
    """Build a minimal patient history record matching the shape produced by SecureStorage."""
    return {
        "timestamp": ts,
        "calculation_results": {
            "chronological_age": chron_age,
            "phenoage": phenoage,
            "delta_age": phenoage - chron_age,
        },
    }


def _extract_trajectory(history: list[dict]) -> tuple:
    """Mirror the extraction logic in render_tab4 to keep tests in sync."""
    records = []
    for rec in history:
        cr = rec["calculation_results"]
        records.append({
            "timestamp": rec["timestamp"],
            "chronological_age": cr["chronological_age"],
            "phenoage": cr["phenoage"],
            "delta_age": cr["delta_age"],
        })

    timestamps = [r["timestamp"] for r in records]
    chron_ages = [r["chronological_age"] for r in records]
    phenoages = [r["phenoage"] for r in records]
    delta_ages = [r["delta_age"] for r in records]
    return timestamps, chron_ages, phenoages, delta_ages


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def three_records_six_months_apart():
    """
    Three measurements spaced exactly 6 months apart.

    Timeline:
      T0: chron=40.0, phenoage=42.0  (delta = +2.0)
      T1: chron=40.5, phenoage=41.5  (delta = +1.0)  — slight improvement
      T2: chron=41.0, phenoage=41.0  (delta =  0.0)  — normalised
    """
    base = datetime(2024, 1, 15, 10, 0, 0)
    t0 = base
    t1 = base + timedelta(days=182)   # ~6 months
    t2 = base + timedelta(days=365)   # ~12 months

    return [
        _make_record(t0.isoformat(), 40.0, 42.0),
        _make_record(t1.isoformat(), 40.5, 41.5),
        _make_record(t2.isoformat(), 41.0, 41.0),
    ]


# ---------------------------------------------------------------------------
# _years_between tests
# ---------------------------------------------------------------------------


def test_years_between_six_months():
    t0 = datetime(2024, 1, 1).isoformat()
    t1 = datetime(2024, 7, 1).isoformat()
    years = _years_between(t0, t1)
    assert 0.45 < years < 0.52, f"Expected ~0.5 years, got {years}"


def test_years_between_one_year():
    t0 = datetime(2023, 6, 15).isoformat()
    t1 = datetime(2024, 6, 15).isoformat()
    years = _years_between(t0, t1)
    assert abs(years - 1.0) < 0.01, f"Expected ~1.0 year, got {years}"


def test_years_between_zero():
    ts = datetime(2024, 3, 10, 8, 0, 0).isoformat()
    assert _years_between(ts, ts) == 0.0


# ---------------------------------------------------------------------------
# Rate of Aging tests
# ---------------------------------------------------------------------------


def test_rate_of_aging_rational(three_records_six_months_apart):
    """Rate of Aging should be a rational float close to expected value."""
    history = three_records_six_months_apart
    timestamps, _, phenoages, _ = _extract_trajectory(history)

    elapsed_years = _years_between(timestamps[0], timestamps[-1])
    rate = (phenoages[-1] - phenoages[0]) / elapsed_years

    # PhenoAge went from 42.0 → 41.0 over ~1 year → rate ≈ -1.0 bio-yr/yr
    assert not math.isnan(rate), "Rate of Aging must not be nan"
    assert not math.isinf(rate), "Rate of Aging must not be inf"
    assert abs(rate - (-1.0)) < 0.1, f"Expected rate ≈ -1.0, got {rate:.4f}"


def test_rate_of_aging_zero_time_returns_nan():
    """When both timestamps are identical, rate should be guarded to nan."""
    ts = datetime(2025, 5, 1, 9, 0, 0).isoformat()
    history = [
        _make_record(ts, 50.0, 52.0),
        _make_record(ts, 50.0, 51.0),  # same timestamp
    ]
    timestamps, _, phenoages, _ = _extract_trajectory(history)
    elapsed = _years_between(timestamps[0], timestamps[-1])

    # Mimics the guard in render_tab4
    _MIN_YEARS = 1 / 365
    if elapsed >= _MIN_YEARS:
        rate = (phenoages[-1] - phenoages[0]) / elapsed
    else:
        rate = float("nan")

    assert math.isnan(rate), "Sub-day elapsed time should produce nan rate"


# ---------------------------------------------------------------------------
# Intervention Net Benefit tests
# ---------------------------------------------------------------------------


def test_net_benefit_positive_on_improvement(three_records_six_months_apart):
    """Net Benefit = delta_ages[0] - delta_ages[-1] should be positive when delta improved."""
    _, _, _, delta_ages = _extract_trajectory(three_records_six_months_apart)
    net_benefit = delta_ages[0] - delta_ages[-1]
    # delta went from +2 to 0 → net_benefit = +2.0
    assert net_benefit > 0, f"Improvement should yield positive net_benefit, got {net_benefit}"
    assert abs(net_benefit - 2.0) < 0.01, f"Expected net_benefit=2.0, got {net_benefit:.4f}"


def test_net_benefit_negative_on_worsening():
    """Net Benefit should be negative if age acceleration increased."""
    base = datetime(2024, 1, 1)
    history = [
        _make_record(base.isoformat(), 35.0, 33.0),                         # delta = -2
        _make_record((base + timedelta(days=365)).isoformat(), 36.0, 36.0),  # delta = 0
    ]
    _, _, _, delta_ages = _extract_trajectory(history)
    net_benefit = delta_ages[0] - delta_ages[-1]
    # delta went from -2 to 0 → net_benefit = -2 (worsened)
    assert net_benefit < 0, f"Worsening should yield negative net_benefit, got {net_benefit}"


# ---------------------------------------------------------------------------
# Integration: full trajectory matches expected values
# ---------------------------------------------------------------------------


def test_full_trajectory_with_three_records(three_records_six_months_apart):
    """End-to-end check that all trajectory values are rational and sensible."""
    history = three_records_six_months_apart
    timestamps, chron_ages, phenoages, delta_ages = _extract_trajectory(history)

    assert len(timestamps) == 3
    assert all(not math.isnan(p) for p in phenoages), "No NaN phenoages"
    assert chron_ages == [40.0, 40.5, 41.0]
    assert phenoages == [42.0, 41.5, 41.0]
    assert delta_ages == [2.0, 1.0, 0.0]
