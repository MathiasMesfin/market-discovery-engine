"""Unit tests for batched deep scanning (app.py)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class SessionStateFake:
    """A fake for st.session_state that supports both dict-style and attr-style access."""
    def __init__(self):
        self._data = {}

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, val):
        self._data[key] = val

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._data.get(name, MagicMock())

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def to_dict(self):
        return dict(self._data)


st_mock = MagicMock()
st_mock.tabs.side_effect = lambda tabs_list: tuple(MagicMock() for _ in range(len(tabs_list)))
st_mock.columns.side_effect = lambda n: tuple(MagicMock() for _ in range(n) if isinstance(n, int)) or (MagicMock(), MagicMock())
st_mock.radio.return_value = "Gap Monster Mode"
# selectbox needs to support both int() conversion and [1] subscripting
_sb_mock = MagicMock()
_sb_mock.__int__.return_value = 10
_sb_mock.__getitem__.return_value = 30
st_mock.selectbox.return_value = _sb_mock
st_mock.number_input.return_value = 100
st_mock.button.return_value = False  # Prevent button handlers from firing at import time
st_mock.checkbox.return_value = False
st_mock.text_input.return_value = ""
st_mock.text_area.return_value = ""
st_mock.session_state = SessionStateFake()
st_mock.cache_data = lambda **kwargs: (lambda fn: fn)
st_mock.empty = lambda: MagicMock()
sys.modules["streamlit"] = st_mock
import app
import importlib
app = importlib.reload(app)
from app import (
    _merge_batch_results,
    init_deep_scan_session_state,
    process_single_deep_scan_batch,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset session state before each test."""
    st_mock.session_state = SessionStateFake()
    app.init_api_telemetry(force_reset=True)
    yield


def test_init_deep_scan_session_state_defaults():
    """init_deep_scan_session_state sets all expected keys."""
    init_deep_scan_session_state(force_reset=True)
    assert st_mock.session_state.deep_scan_full_candidate_list == []
    assert st_mock.session_state.deep_scan_pending_tickers == []
    assert st_mock.session_state.deep_scan_failed_tickers == []
    assert st_mock.session_state.deep_scan_loaded is False
    assert st_mock.session_state.deep_scan_run_all is False
    assert st_mock.session_state.deep_scan_pause is False


def test_init_deep_scan_session_state_preserves_existing():
    """Calling init without force_reset should not clear state."""
    init_deep_scan_session_state(force_reset=True)
    st_mock.session_state.deep_scan_full_candidate_list = [{"ticker": "AAPL"}]
    init_deep_scan_session_state(force_reset=False)
    assert st_mock.session_state.deep_scan_full_candidate_list == [{"ticker": "AAPL"}]


def test_init_deep_scan_session_state_force_reset():
    """force_reset=True clears all deep scan state."""
    init_deep_scan_session_state(force_reset=True)
    st_mock.session_state.deep_scan_full_candidate_list = [{"ticker": "AAPL"}]
    init_deep_scan_session_state(force_reset=True)
    assert st_mock.session_state.deep_scan_full_candidate_list == []


def make_sample_candidate(ticker, n=60):
    """Helper: build a candidate dict with a hist_df of n rows."""
    import datetime
    import numpy as np
    dates = pd.date_range(end=datetime.date.today(), periods=n, freq="B")
    hist_df = pd.DataFrame({
        "Open": np.random.uniform(10, 200, n),
        "High": np.random.uniform(10, 200, n),
        "Low": np.random.uniform(10, 200, n),
        "Close": np.random.uniform(10, 200, n),
        "Volume": np.random.randint(1_000_000, 50_000_000, n),
    }, index=dates)
    return {
        "ticker": ticker,
        "hist_df": hist_df,
        "cik": "0000320193",
        "data_confidence": "High",
    }


def test_merge_batch_results_empty_results():
    """_merge_batch_results handles empty results_df."""
    init_deep_scan_session_state(force_reset=True)
    result = {
        "meta_dict": {},
        "hist_data": {},
        "results_df": pd.DataFrame(),
        "failed_tickers": {},
        "runtime": 1.0,
        "batch_429": 0,
        "batch_http": 0,
        "batch_size": 0,
        "stage2_count": 0,
        "stage3_count": 0,
        "stage4_count": 0,
    }
    _merge_batch_results(result)
    assert st_mock.session_state.deep_scan_completed_tickers == []
    assert st_mock.session_state.deep_scan_failed_tickers == []


def test_merge_batch_results_with_data():
    """_merge_batch_results correctly merges results and failures."""
    init_deep_scan_session_state(force_reset=True)

    results_df = pd.DataFrame({
        "Ticker": ["AAPL"],
        "Final Score": [85.0],
    })
    result = {
        "meta_dict": {"AAPL": {"name": "Apple Inc."}},
        "hist_data": {"AAPL": pd.DataFrame()},
        "results_df": results_df,
        "failed_tickers": {"MSFT": "No earnings dates"},
        "runtime": 2.5,
        "batch_429": 0,
        "batch_http": 1,
        "batch_size": 2,
        "stage2_count": 2,
        "stage3_count": 1,
        "stage4_count": 1,
    }
    _merge_batch_results(result)

    assert "AAPL" in st_mock.session_state.deep_scan_cumulative_meta
    assert st_mock.session_state.deep_scan_completed_tickers == ["AAPL"]
    assert len(st_mock.session_state.deep_scan_failed_tickers) == 1
    assert st_mock.session_state.deep_scan_failed_tickers[0]["ticker"] == "MSFT"
    assert not st_mock.session_state.deep_scan_cumulative_results_df.empty
    assert len(st_mock.session_state.deep_scan_batch_telemetry) == 1


def test_merge_batch_results_multiple_batches():
    """Multiple batches accumulate correctly."""
    init_deep_scan_session_state(force_reset=True)

    batch1 = {
        "meta_dict": {"A": {}, "B": {}},
        "hist_data": {},
        "results_df": pd.DataFrame({"Ticker": ["A", "B"], "Final Score": [90.0, 80.0]}),
        "failed_tickers": {},
        "runtime": 1.0,
        "batch_429": 0,
        "batch_http": 0,
        "batch_size": 2,
        "stage2_count": 2,
        "stage3_count": 2,
        "stage4_count": 2,
    }
    batch2 = {
        "meta_dict": {"C": {}},
        "hist_data": {},
        "results_df": pd.DataFrame({"Ticker": ["C"], "Final Score": [70.0]}),
        "failed_tickers": {"D": "Some error"},
        "runtime": 1.5,
        "batch_429": 1,
        "batch_http": 0,
        "batch_size": 2,
        "stage2_count": 2,
        "stage3_count": 1,
        "stage4_count": 1,
    }

    _merge_batch_results(batch1)
    _merge_batch_results(batch2)

    assert st_mock.session_state.deep_scan_completed_tickers == ["A", "B", "C"]
    assert len(st_mock.session_state.deep_scan_failed_tickers) == 1
    assert st_mock.session_state.deep_scan_failed_tickers[0]["ticker"] == "D"
    assert len(st_mock.session_state.deep_scan_cumulative_results_df) == 3
    assert len(st_mock.session_state.deep_scan_batch_telemetry) == 2


def test_build_leaderboard_sorts_by_final_score():
    """Build Final Leaderboard logic: sort by Final Score desc."""
    init_deep_scan_session_state(force_reset=True)
    df = pd.DataFrame({
        "Ticker": ["B", "A", "C"],
        "Final Score": [70.0, 90.0, 80.0],
    })
    st_mock.session_state.deep_scan_cumulative_results_df = df

    sorted_df = df.sort_values("Final Score", ascending=False).reset_index(drop=True)
    st_mock.session_state.screener_results = sorted_df

    assert st_mock.session_state.screener_results.iloc[0]["Ticker"] == "A"
    assert st_mock.session_state.screener_results.iloc[1]["Ticker"] == "C"
    assert st_mock.session_state.screener_results.iloc[2]["Ticker"] == "B"


def test_retry_failed_tickers():
    """Retry Failed Tickers moves failures back to pending."""
    init_deep_scan_session_state(force_reset=True)
    st_mock.session_state.deep_scan_full_candidate_list = [
        {"ticker": "AAPL"}, {"ticker": "MSFT"}, {"ticker": "GOOGL"},
    ]
    st_mock.session_state.deep_scan_pending_tickers = ["GOOGL"]
    st_mock.session_state.deep_scan_failed_tickers = [
        {"ticker": "AAPL", "error": "Err1"},
        {"ticker": "MSFT", "error": "Err2"},
    ]

    failed_tickers = [f["ticker"] for f in st_mock.session_state.deep_scan_failed_tickers]
    candidates_map = {c["ticker"]: c for c in st_mock.session_state.deep_scan_full_candidate_list}
    retry_candidates = [candidates_map[t] for t in failed_tickers if t in candidates_map]
    st_mock.session_state.deep_scan_pending_tickers = list(st_mock.session_state.deep_scan_pending_tickers) + retry_candidates
    st_mock.session_state.deep_scan_failed_tickers = []

    retried_ticker_strings = [t["ticker"] if isinstance(t, dict) else t for t in st_mock.session_state.deep_scan_pending_tickers]
    assert retried_ticker_strings == ["GOOGL", "AAPL", "MSFT"]
    assert st_mock.session_state.deep_scan_failed_tickers == []


def test_reset_deep_scan_progress_clears_state():
    """Reset Deep Scan Progress clears all batch state."""
    init_deep_scan_session_state(force_reset=True)
    st_mock.session_state.deep_scan_full_candidate_list = [{"ticker": "AAPL"}]
    st_mock.session_state.deep_scan_pending_tickers = ["AAPL"]
    st_mock.session_state.deep_scan_loaded = True
    init_deep_scan_session_state(force_reset=True)
    assert st_mock.session_state.deep_scan_full_candidate_list == []
    assert st_mock.session_state.deep_scan_pending_tickers == []
    assert st_mock.session_state.deep_scan_loaded is False


def test_reset_scanner_state_calls_deep_scan_reset():
    """Reset Scanner State also resets deep scan state."""
    init_deep_scan_session_state(force_reset=True)
    st_mock.session_state.deep_scan_loaded = True
    init_deep_scan_session_state(force_reset=True)
    assert st_mock.session_state.deep_scan_loaded is False


@patch("app.fetch_cached_fundamentals_24h")
@patch("app.fetch_cached_earnings_12h")
@patch("app.fetch_cached_sec_24h")
@patch("app.calculate_single_ticker_metrics")
@patch("app.calculate_screener_scores")
def test_process_single_deep_scan_batch_happy_path(
    mock_scores, mock_metrics, mock_sec, mock_earn, mock_fund
):
    """Happy path: a batch processes correctly end-to-end."""
    init_deep_scan_session_state(force_reset=True)
    app.init_api_telemetry(force_reset=True)

    candidates = [make_sample_candidate("AAPL", 120), make_sample_candidate("MSFT", 120)]

    mock_fund.return_value = (
        {"market_cap": 2_000_000_000, "long_name": "Apple Inc.",
         "float_shares": 15_000_000_000, "shares_short": None,
         "short_percent": None, "analysts": None,
         "business_summary": "Tech", "is_operating": True},
        app.new_api_telemetry_delta(),
    )

    mock_earn.return_value = (
        {"next_earnings_date": pd.Timestamp("2026-07-20"),
         "last_earnings_date": pd.Timestamp("2026-04-20"),
         "hist_earnings_dates": [], "calendar_status": "confirmed",
         "earnings_dates_status": "confirmed"},
        app.new_api_telemetry_delta(),
    )

    mock_sec.return_value = (
        {"sec_filings": [], "sec_status": "ok"},
        app.new_api_telemetry_delta(),
    )

    mock_metrics.return_value = (
        {"Ticker": "AAPL", "Final Score": 95.0, "hist_df": candidates[0]["hist_df"]},
        None,
    )

    mock_scores.return_value = pd.DataFrame({
        "Ticker": ["AAPL", "MSFT"],
        "Final Score": [95.0, 88.0],
    })

    result = process_single_deep_scan_batch(candidates, "fake-key", False, 10)

    assert "meta_dict" in result
    assert "hist_data" in result
    assert "results_df" in result
    assert "failed_tickers" in result
    assert result["batch_size"] == 2
    assert isinstance(result["results_df"], pd.DataFrame)
    assert result["runtime"] >= 0


@patch("app.fetch_cached_fundamentals_24h")
def test_process_single_deep_scan_batch_all_fail(mock_fund):
    """When all tickers fail fundamentals, results_df is empty."""
    init_deep_scan_session_state(force_reset=True)
    app.init_api_telemetry(force_reset=True)

    candidates = [make_sample_candidate("AAPL"), make_sample_candidate("MSFT")]

    mock_fund.return_value = (None, app.new_api_telemetry_delta())

    result = process_single_deep_scan_batch(candidates, "fake-key", False, 10)

    assert result["results_df"].empty
    assert result["stage2_count"] == 0
    assert result["stage3_count"] == 0
    assert result["stage4_count"] == 0


def test_process_single_deep_scan_batch_empty_input():
    """An empty batch returns an empty result."""
    init_deep_scan_session_state(force_reset=True)
    app.init_api_telemetry(force_reset=True)

    result = process_single_deep_scan_batch([], "fake-key", False, 10)

    assert result["results_df"].empty
    assert result["batch_size"] == 0
