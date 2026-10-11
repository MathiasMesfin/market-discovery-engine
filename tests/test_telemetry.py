"""Verify API telemetry survives ThreadPoolExecutor (main-thread merge)."""
import concurrent.futures
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Stub streamlit before importing app helpers
class SessionStateFake:
    def __init__(self):
        self._data = {"api_telemetry": None}
    def __contains__(self, item):
        return item in self._data
    def __getattr__(self, name):
        if name == "api_telemetry":
            return self._data.get("api_telemetry")
        return self._data.get(name, MagicMock())
    def __getitem__(self, key):
        return self._data.get(key, MagicMock())
    def __setitem__(self, key, val):
        self._data[key] = val
    def get(self, key, default=None):
        return self._data.get(key, default)
    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name] = value

st_mock = MagicMock()
st_mock.session_state = SessionStateFake()
st_mock.cache_data = lambda **kwargs: (lambda fn: fn)
st_mock.tabs.side_effect = lambda tabs_list: tuple(MagicMock() for _ in range(len(tabs_list)))
st_mock.columns.side_effect = lambda n: tuple(MagicMock() for _ in range(n) if isinstance(n, int)) or (MagicMock(), MagicMock())
st_mock.button.return_value = False
st_mock.checkbox.return_value = False
st_mock.radio.return_value = "Gap Monster Mode"
sys.modules["streamlit"] = st_mock

import api_fetch
from api_fetch import (  # noqa: E402
    clear_telemetry_data_caches,
    fetch_cached_fundamentals_24h,
    merge_api_telemetry_delta,
    new_api_telemetry_delta,
)
import app
from app import init_api_telemetry  # noqa: E402


@pytest.fixture(autouse=True)
def reset_caches():
    clear_telemetry_data_caches()
    yield
    clear_telemetry_data_caches()


def _mock_fundamentals_pure(ticker, finnhub_key=None):
    delta = new_api_telemetry_delta()
    delta["finnhub_fundamentals"]["attempted"] = 1
    delta["finnhub_fundamentals"]["success"] = 1
    delta["yfinance_fundamentals"]["attempted"] = 1
    delta["yfinance_fundamentals"]["success"] = 1
    return {
        "market_cap": 1_000_000_000,
        "long_name": ticker,
        "float_shares": 100_000_000,
        "shares_short": None,
        "short_percent": None,
        "analysts": None,
        "business_summary": "",
        "is_operating": True,
    }, delta


def test_thread_pool_merges_api_attempts():
    init_api_telemetry(force_reset=True)
    api_fetch.clear_telemetry_data_caches()
    tickers = [f"T{i}" for i in range(49)]

    with patch("api_fetch._load_from_disk", return_value=None), \
         patch("api_fetch._save_to_disk", return_value=None), \
         patch("api_fetch._fetch_fundamentals_pure", side_effect=_mock_fundamentals_pure):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(fetch_cached_fundamentals_24h, t, "fake-key")
                for t in tickers
            ]
            for fut in concurrent.futures.as_completed(futures):
                _, delta = fut.result()
                merge_api_telemetry_delta(app.st.session_state.api_telemetry, delta)

    telem = app.st.session_state.api_telemetry
    total_attempts = (
        telem["finnhub_fundamentals"]["attempted"]
        + telem["yfinance_fundamentals"]["attempted"]
    )
    assert total_attempts == 49 * 2
    assert telem["cache_miss_fundamentals"] == 49
    assert telem["cache_hit_fundamentals"] == 0

    # Second pass should be all cache hits, zero new API attempts
    with patch("api_fetch._fetch_fundamentals_pure", side_effect=_mock_fundamentals_pure):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(fetch_cached_fundamentals_24h, t, "fake-key")
                for t in tickers
            ]
            for fut in concurrent.futures.as_completed(futures):
                _, delta = fut.result()
                merge_api_telemetry_delta(app.st.session_state.api_telemetry, delta)

    assert telem["cache_hit_fundamentals"] == 49
    assert total_attempts == 49 * 2  # unchanged — no extra API calls
