"""API fetch telemetry: error categories and concurrency snapshot."""
import socket
import sys
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api_fetch
from api_fetch import (
    API_WORKER_OPTIONS,
    DEFAULT_MAX_CONCURRENT_API_WORKERS,
    build_concurrency_snapshot,
    is_dns_failure,
    merge_api_telemetry_delta,
    new_api_telemetry_delta,
    record_http_status,
    record_request_exception,
)


def test_default_worker_options():
    assert DEFAULT_MAX_CONCURRENT_API_WORKERS == 3
    assert API_WORKER_OPTIONS == (3, 5, 10, 20, 30)


def test_concurrency_snapshot_reflects_setting():
    snap = build_concurrency_snapshot(30)
    assert snap["max_concurrent_api_workers"] == 30
    assert snap["fundamentals_fetch_max_workers"] == 30
    assert snap["fast_scan_max_workers"] == 1
    assert snap["max_simultaneous_http_deep_scan"] == 30


def test_error_categories_merge():
    target = api_fetch.new_api_telemetry_snapshot()
    delta = new_api_telemetry_delta()
    fh = delta["finnhub_fundamentals"]
    record_http_status(delta, fh, "AAA", 429)
    record_http_status(delta, fh, "BBB", 500)
    exc = requests.exceptions.ConnectionError("Failed to resolve 'api.example.com'")
    record_request_exception(delta, fh, "CCC", exc)
    merge_api_telemetry_delta(target, delta)
    cats = target["error_categories"]
    assert cats["rate_limit_429"] == 1
    assert cats["http_failures"] == 1
    assert cats["dns_failures"] == 1


def test_is_dns_failure_socket_gaierror():
    assert is_dns_failure(socket.gaierror(8, "nodename nor servname provided"))


@pytest.mark.parametrize("workers", [3, 5, 10, 20, 30])
def test_concurrency_options(workers):
    assert workers in API_WORKER_OPTIONS
    assert build_concurrency_snapshot(workers)["max_concurrent_api_workers"] == workers
