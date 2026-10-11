"""Thread-safe API fetch + telemetry (no Streamlit UI)."""
import copy
import datetime
import socket
import threading
import time
import os
import json
import random

import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# Worker concurrency — kept low to avoid yfinance 401/crumb issues.
# Yahoo Finance crumb sessions are not safe for high concurrency.
# ---------------------------------------------------------------------------
DEFAULT_MAX_CONCURRENT_API_WORKERS = 3
FAST_SCAN_MAX_WORKERS = 1
API_WORKER_OPTIONS = (3, 5, 10, 20, 30)

# ---------------------------------------------------------------------------
# Shared curl_cffi session — ONE session for all threads.
#
# Yahoo Finance (since late 2024) requires a browser-like TLS fingerprint
# (via curl_cffi) and a "crumb" cookie.  If every worker thread creates its
# own yf.Ticker() with no shared session, they race to acquire a crumb and
# can invalidate each other's tokens → 401 "Invalid Crumb" cascade.
#
# Solution: initialise ONE session at module load, protected by a lock so
# only one thread does the handshake; every Ticker() call shares that session.
# ---------------------------------------------------------------------------
_YF_SESSION_LOCK = threading.Lock()
_yf_session = None          # populated lazily by _get_yf_session()


def _get_yf_session():
    """Return (or lazily create) the shared curl_cffi yfinance session."""
    global _yf_session
    if _yf_session is not None:
        return _yf_session
    with _YF_SESSION_LOCK:
        if _yf_session is not None:          # double-checked locking
            return _yf_session
        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate="chrome")
            # Warm up: fetch a crumb so it is cached before workers start
            _yf_session = session
        except Exception:
            # Fall back to plain requests if curl_cffi unavailable
            _yf_session = requests.Session()
    return _yf_session


def reset_yf_session():
    """Force a fresh session on the next Ticker() call (call after 401 errors)."""
    global _yf_session
    with _YF_SESSION_LOCK:
        try:
            if _yf_session is not None:
                _yf_session.close()
        except Exception:
            pass
        _yf_session = None


# ---------------------------------------------------------------------------
# Token-bucket rate limiters for yfinance HTTP calls.
#
# TWO separate limiters:
#   _yf_fundamentals_acquire  — heavy calls: .info, .quarterly_cashflow, etc.
#                               Capped at 5 RPS to stay under Yahoo limits.
#   _yf_earnings_acquire      — lightweight calls: .earnings_dates, .calendar
#                               Capped at 15 RPS (separate quota; much lighter).
# ---------------------------------------------------------------------------
YFINANCE_FUNDAMENTALS_RPS = 5   # heavy yfinance calls
YFINANCE_EARNINGS_RPS = 15      # lightweight earnings/calendar calls
# Legacy alias used by callers that still reference YFINANCE_RPS
YFINANCE_RPS = YFINANCE_FUNDAMENTALS_RPS

_YF_FUND_RATE_LOCK = threading.Lock()
_yf_fund_tokens = float(YFINANCE_FUNDAMENTALS_RPS)
_yf_fund_last_refill = time.monotonic()

_YF_EARN_RATE_LOCK = threading.Lock()
_yf_earn_tokens = float(YFINANCE_EARNINGS_RPS)
_yf_earn_last_refill = time.monotonic()


def _yf_acquire():
    """Block until a fundamentals yfinance rate-limit token is available (5 RPS)."""
    global _yf_fund_tokens, _yf_fund_last_refill
    while True:
        with _YF_FUND_RATE_LOCK:
            now = time.monotonic()
            elapsed = now - _yf_fund_last_refill
            _yf_fund_tokens = min(YFINANCE_FUNDAMENTALS_RPS,
                                  _yf_fund_tokens + elapsed * YFINANCE_FUNDAMENTALS_RPS)
            _yf_fund_last_refill = now
            if _yf_fund_tokens >= 1.0:
                _yf_fund_tokens -= 1.0
                return
        time.sleep(0.05)


# Alias so existing fundamentals call-sites keep working unchanged.
_yf_fundamentals_acquire = _yf_acquire


def _yf_earnings_acquire():
    """Block until an earnings yfinance rate-limit token is available (15 RPS)."""
    global _yf_earn_tokens, _yf_earn_last_refill
    while True:
        with _YF_EARN_RATE_LOCK:
            now = time.monotonic()
            elapsed = now - _yf_earn_last_refill
            _yf_earn_tokens = min(YFINANCE_EARNINGS_RPS,
                                  _yf_earn_tokens + elapsed * YFINANCE_EARNINGS_RPS)
            _yf_earn_last_refill = now
            if _yf_earn_tokens >= 1.0:
                _yf_earn_tokens -= 1.0
                return
        time.sleep(0.03)


# Caps outbound SEC requests to at most SEC_RPS per second (SEC limit is 10/sec).
# ---------------------------------------------------------------------------
SEC_RPS = 8
_SEC_RATE_LOCK = threading.Lock()
_sec_tokens = float(SEC_RPS)
_sec_last_refill = time.monotonic()


def _sec_acquire():
    """Block until a SEC rate-limit token is available."""
    global _sec_tokens, _sec_last_refill
    while True:
        with _SEC_RATE_LOCK:
            now = time.monotonic()
            elapsed = now - _sec_last_refill
            _sec_tokens = min(SEC_RPS, _sec_tokens + elapsed * SEC_RPS)
            _sec_last_refill = now
            if _sec_tokens >= 1.0:
                _sec_tokens -= 1.0
                return
        time.sleep(0.08)


# Retry settings for yfinance 401/429 errors
_YF_MAX_RETRIES = 2
_YF_BACKOFF_BASE = 1.0   # seconds; doubles each attempt with jitter


def _is_auth_or_rate_error(exc_str):
    """True when the error string looks like a 401 crumb or 429 rate-limit."""
    return any(k in exc_str for k in (
        "too many requests", "rate limit", "429",
        "401", "unauthorized", "invalid crumb", "crumb",
    ))

_TELEMETRY_CACHE_LOCK = threading.Lock()
_FUNDAMENTALS_DATA_CACHE = {}
_EARNINGS_DATA_CACHE = {}
_SEC_DATA_CACHE = {}
TTL_FUNDAMENTALS_SEC = 86400 * 14  # 14 days
TTL_EARNINGS_SEC = 86400 * 3      # 3 days
TTL_SEC_SEC = 86400 * 7           # 7 days

_API_SERVICE_KEYS = (
    "finnhub_fundamentals",
    "finnhub_earnings",
    "sec_edgar",
    "yfinance_fundamentals",
    "yfinance_earnings",
)


def _empty_api_service_metrics(include_sec_skip=False):
    metrics = {
        "attempted": 0,
        "success": 0,
        "failure": 0,
        "rate_limit_429": 0,
        "cache_hit": 0,
        "cache_miss": 0,
        "errors": [],
    }
    if include_sec_skip:
        metrics["skipped_no_cik"] = 0
    return metrics


def _empty_error_categories():
    return {
        "dns_failures": 0,
        "thread_creation_failures": 0,
        "http_failures": 0,
        "rate_limit_429": 0,
    }


def build_concurrency_snapshot(api_workers=None):
    """Document ThreadPoolExecutor settings and estimated peak concurrent HTTP."""
    workers = int(api_workers if api_workers is not None else DEFAULT_MAX_CONCURRENT_API_WORKERS)
    return {
        "max_concurrent_api_workers": workers,
        "fast_scan_max_workers": FAST_SCAN_MAX_WORKERS,
        "fundamentals_fetch_max_workers": workers,
        "earnings_fetch_max_workers": workers,
        "sec_fetch_max_workers": workers,
        "stage3_executor_max_workers": workers,
        "max_simultaneous_http_fast_scan": FAST_SCAN_MAX_WORKERS,
        "max_simultaneous_http_deep_scan": workers,
    }


def is_dns_failure(exc):
    """True when exception indicates DNS / hostname resolution failure."""
    if exc is None:
        return False
    if isinstance(exc, socket.gaierror):
        return True
    checked = exc
    seen = set()
    while checked is not None and id(checked) not in seen:
        seen.add(id(checked))
        if isinstance(checked, socket.gaierror):
            return True
        checked = getattr(checked, "__cause__", None) or getattr(checked, "__context__", None)
    msg = str(exc).lower()
    markers = (
        "getaddrinfo",
        "name or service not known",
        "nodename nor servname",
        "failed to resolve",
        "name resolution",
        "temporary failure in name resolution",
        "dns",
    )
    return any(m in msg for m in markers)


def is_thread_pool_failure(exc):
    """True when thread pool / worker scheduling failed."""
    if exc is None:
        return False
    if isinstance(exc, RuntimeError):
        msg = str(exc).lower()
        return any(
            token in msg
            for token in ("thread", "interpreter shutdown", "cannot schedule new futures", "pool")
        )
    msg = str(exc).lower()
    return isinstance(exc, (MemoryError, OSError)) and "thread" in msg


def record_thread_creation_failure(delta):
    delta["error_categories"]["thread_creation_failures"] += 1
    delta["last_errors"].insert(0, "ThreadPoolExecutor: worker creation or scheduling failed")


def record_http_status(delta, service_metrics, ticker, status_code):
    """Non-2xx HTTP response (429 tracked separately)."""
    if status_code == 429:
        delta["error_categories"]["rate_limit_429"] += 1
        service_metrics["rate_limit_429"] += 1
    else:
        delta["error_categories"]["http_failures"] += 1
    service_metrics["failure"] += 1
    error_msg = f"{ticker}: HTTP {status_code}"
    service_metrics["errors"].append(error_msg)
    delta["last_errors"].append(error_msg)


def record_request_exception(delta, service_metrics, ticker, exc):
    """requests / network layer failure."""
    if is_dns_failure(exc):
        delta["error_categories"]["dns_failures"] += 1
    else:
        delta["error_categories"]["http_failures"] += 1
    service_metrics["failure"] += 1
    error_msg = f"{ticker}: {exc}"
    service_metrics["errors"].append(error_msg)
    delta["last_errors"].append(error_msg)


def record_yfinance_exception(delta, service_metrics, ticker, exc):
    """yfinance / underlying HTTP failures."""
    exc_str = str(exc).lower()
    if "too many requests" in exc_str or "rate limit" in exc_str or "429" in exc_str:
        delta["error_categories"]["rate_limit_429"] += 1
        service_metrics["rate_limit_429"] += 1
        service_metrics["failure"] += 1
        error_msg = f"{ticker}: Rate limited (yfinance)"
    elif is_dns_failure(exc):
        delta["error_categories"]["dns_failures"] += 1
        service_metrics["failure"] += 1
        error_msg = f"{ticker}: {exc}"
    else:
        delta["error_categories"]["http_failures"] += 1
        service_metrics["failure"] += 1
        error_msg = f"{ticker}: {exc}"
    service_metrics["errors"].append(error_msg)
    delta["last_errors"].append(error_msg)


def new_api_telemetry_delta():
    """Thread-safe telemetry increment bundle returned from worker fetch calls."""
    return {
        "finnhub_fundamentals": _empty_api_service_metrics(),
        "finnhub_earnings": _empty_api_service_metrics(),
        "sec_edgar": _empty_api_service_metrics(include_sec_skip=True),
        "yfinance_fundamentals": _empty_api_service_metrics(),
        "yfinance_earnings": _empty_api_service_metrics(),
        "error_categories": _empty_error_categories(),
        "cache_hit_fundamentals": 0,
        "cache_miss_fundamentals": 0,
        "cache_hit_earnings": 0,
        "cache_miss_earnings": 0,
        "cache_hit_sec": 0,
        "cache_miss_sec": 0,
        "last_errors": [],
    }


def clear_telemetry_data_caches():
    with _TELEMETRY_CACHE_LOCK:
        _FUNDAMENTALS_DATA_CACHE.clear()
        _EARNINGS_DATA_CACHE.clear()
        _SEC_DATA_CACHE.clear()


def merge_api_telemetry_delta(target, delta):
    """Merge a worker-thread telemetry delta into session_state on the main thread."""
    if not delta:
        return
    err_src = delta.get("error_categories", {})
    err_dst = target.setdefault("error_categories", _empty_error_categories())
    for key in err_dst:
        err_dst[key] = err_dst.get(key, 0) + err_src.get(key, 0)

    for key in (
        "cache_hit_fundamentals",
        "cache_miss_fundamentals",
        "cache_hit_earnings",
        "cache_miss_earnings",
        "cache_hit_sec",
        "cache_miss_sec",
    ):
        target[key] = target.get(key, 0) + delta.get(key, 0)
    for service in _API_SERVICE_KEYS:
        src = delta.get(service, {})
        dst = target[service]
        for metric in ("attempted", "success", "failure", "rate_limit_429", "cache_hit", "cache_miss"):
            dst[metric] = dst.get(metric, 0) + src.get(metric, 0)
        if service == "sec_edgar":
            dst["skipped_no_cik"] = dst.get("skipped_no_cik", 0) + src.get("skipped_no_cik", 0)
        dst["errors"].extend(src.get("errors", []))
    if "last_errors" not in target:
        target["last_errors"] = []
    for error_msg in delta.get("last_errors", []):
        target["last_errors"].insert(0, error_msg)
    target["last_errors"] = target["last_errors"][:10]


DISK_CACHE_DIR = "/Users/mathiasmesfin/Downloads/Stock Screener/cache/disk_cache"


def _evict_expired_cache_files():
    """
    Background startup task: delete any disk cache files whose expiry has passed
    OR whose data is empty/invalid (poisoned entries from failed API fetches).
    Runs in a daemon thread — never blocks the main app startup.
    """
    now = time.time()
    for cat in ("fundamentals", "earnings", "sec"):
        d = os.path.join(DISK_CACHE_DIR, cat)
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(d, fname)
            try:
                with open(path, "r") as f:
                    entry = json.load(f)
                expired = entry.get("expiry", 0) <= now
                data = entry.get("data", {})
                if cat == "earnings":
                    data = _deserialize_earnings(data)
                invalid = not _is_valid_data(cat, data)
                if expired or invalid:
                    os.remove(path)
            except Exception:
                try:
                    os.remove(path)
                except Exception:
                    pass




def _get_cache_filepath(category, ticker):
    # Ensure safe filename
    safe_ticker = "".join(c for c in ticker if c.isalnum() or c in ('-', '_')).upper()
    return os.path.join(DISK_CACHE_DIR, category, f"{safe_ticker}.json")

def _serialize_earnings(data):
    ser = copy.deepcopy(data)
    if ser.get('next_earnings_date'):
        if hasattr(ser['next_earnings_date'], 'isoformat'):
            ser['next_earnings_date'] = ser['next_earnings_date'].isoformat()
    if ser.get('last_earnings_date'):
        if hasattr(ser['last_earnings_date'], 'isoformat'):
            ser['last_earnings_date'] = ser['last_earnings_date'].isoformat()
    if ser.get('hist_earnings_dates'):
        res_dates = []
        for d in ser['hist_earnings_dates']:
            if d:
                res_dates.append(d.isoformat() if hasattr(d, 'isoformat') else str(d))
        ser['hist_earnings_dates'] = res_dates
    return ser

def _deserialize_earnings(ser):
    data = copy.deepcopy(ser)
    if data.get('next_earnings_date') and isinstance(data['next_earnings_date'], str):
        try:
            data['next_earnings_date'] = datetime.datetime.strptime(data['next_earnings_date'][:10], '%Y-%m-%d').date()
        except Exception:
            pass
    if data.get('last_earnings_date') and isinstance(data['last_earnings_date'], str):
        try:
            data['last_earnings_date'] = datetime.datetime.strptime(data['last_earnings_date'][:10], '%Y-%m-%d').date()
        except Exception:
            pass
    if data.get('hist_earnings_dates'):
        res_dates = []
        for d_str in data['hist_earnings_dates']:
            if isinstance(d_str, str):
                try:
                    res_dates.append(datetime.datetime.strptime(d_str[:10], '%Y-%m-%d').date())
                except Exception:
                    pass
            else:
                res_dates.append(d_str)
        data['hist_earnings_dates'] = res_dates
    return data

def _is_valid_data(category, data):
    """Returns True if data contains valid non-empty fields for its category."""
    if not isinstance(data, dict):
        return False
    if category == "earnings":
        return bool(data.get('next_earnings_date') or data.get('last_earnings_date') or data.get('hist_earnings_dates'))
    if category == "fundamentals":
        return bool(data.get('market_cap') or data.get('sector') or data.get('long_name'))
    return True

def _load_from_disk(category, ticker):
    filepath = _get_cache_filepath(category, ticker)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r') as f:
            entry = json.load(f)
            if isinstance(entry, dict) and "expiry" in entry and "data" in entry:
                if entry["expiry"] > time.time():
                    data = _deserialize_earnings(entry["data"]) if category == "earnings" else entry["data"]
                    if _is_valid_data(category, data):
                        return data
                    else:
                        # Auto-delete invalid/empty poisoned cache file
                        try:
                            os.remove(filepath)
                        except Exception:
                            pass
    except Exception:
        pass
    return None

def _save_to_disk(category, ticker, expiry, data):
    if not _is_valid_data(category, data):
        return
    filepath = _get_cache_filepath(category, ticker)
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        to_save = _serialize_earnings(data) if category == "earnings" else data
        temp_filepath = filepath + ".tmp"
        with open(temp_filepath, 'w') as f:
            json.dump({"expiry": expiry, "data": to_save}, f)
        os.replace(temp_filepath, filepath)
    except Exception:
        pass


# Kick off eviction in a daemon thread so it never blocks app startup.
# Placed here so all helper functions (_deserialize_earnings, _is_valid_data, etc.) are defined.
threading.Thread(target=_evict_expired_cache_files, daemon=True, name="cache-evict").start()


def _fetch_fundamentals_pure(ticker, finnhub_key=None):
    """Fetch fundamentals only (no session_state). Returns (data, telemetry_delta)."""
    delta = new_api_telemetry_delta()
    res = {
        'market_cap': None,
        'long_name': ticker,
        'float_shares': None,
        'shares_short': None,
        'short_percent': None,
        'analysts': None,
        'business_summary': "",
        'is_operating': True,
        'sector': None,
        'industry': None,
        'forward_pe': None,
        'trailing_pe': None,
        'price_to_sales': None,
        'revenue_growth': None,
        'short_ratio': None,
        'ttm_levered_fcf': None,
        'quarterly_fcf': []
    }
    fh = delta["finnhub_fundamentals"]
    yf_f = delta["yfinance_fundamentals"]

    if finnhub_key:
        fh["attempted"] += 1
        try:
            url = f'https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={finnhub_key}'
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                fh["success"] += 1
                p = r.json()
                if p:
                    res['long_name'] = p.get('name', ticker)
                    mc = p.get('marketCapitalization')
                    if mc:
                        res['market_cap'] = mc * 1000000
                    so = p.get('shareOutstanding')
                    if so:
                        res['float_shares'] = so * 1000000
            else:
                record_http_status(delta, fh, ticker, r.status_code)
        except requests.exceptions.RequestException as e:
            record_request_exception(delta, fh, ticker, e)

    yf_f["attempted"] += 1
    last_exc = None
    for attempt in range(_YF_MAX_RETRIES):
        try:
            _yf_acquire()  # honour global rate limit
            t = yf.Ticker(ticker, session=_get_yf_session())
            info = t.info or {}

            # Check if yfinance returned an empty dict (auth/rate issue)
            if isinstance(info, dict) and not info:
                raise RuntimeError("yfinance returned empty info (auth or rate limit)")

            if not res['market_cap']:
                res['market_cap'] = info.get('marketCap')
            if not res['float_shares']:
                res['float_shares'] = info.get('floatShares')
            res['shares_short'] = info.get('sharesShort')
            res['short_percent'] = info.get('shortPercentOfFloat')
            res['analysts'] = info.get('numberOfAnalystOpinions')
            res['business_summary'] = info.get('longBusinessSummary') or info.get('shortBusinessSummary') or ""
            if res['long_name'] == ticker:
                res['long_name'] = info.get('longName', ticker)
            quote_type = info.get('quoteType', '').upper()
            if quote_type and quote_type not in ['EQUITY']:
                res['is_operating'] = False

            # New fields from info
            res['sector'] = info.get('sector')
            res['industry'] = info.get('industry')
            res['forward_pe'] = info.get('forwardPE')
            res['trailing_pe'] = info.get('trailingPE')
            res['price_to_sales'] = info.get('priceToSalesTrailing12Months')
            res['revenue_growth'] = info.get('revenueGrowth')
            res['short_ratio'] = info.get('shortRatio')
            res['ttm_levered_fcf'] = info.get('freeCashflow')

            # Quarterly Cash Flow
            try:
                _yf_acquire()
                q_cf = t.quarterly_cashflow
                if q_cf is not None and not q_cf.empty:
                    import pandas as pd
                    if 'Free Cash Flow' in q_cf.index:
                        res['quarterly_fcf'] = [float(v) for v in q_cf.loc['Free Cash Flow'].values if pd.notnull(v)]
                    elif 'Operating Cash Flow' in q_cf.index:
                        ocf_row = q_cf.loc['Operating Cash Flow']
                        capex_row = q_cf.loc['Capital Expenditure'] if 'Capital Expenditure' in q_cf.index else None
                        fcf_vals = []
                        for col in q_cf.columns:
                            ocf = ocf_row[col]
                            capex = capex_row[col] if capex_row is not None else 0.0
                            if pd.notnull(ocf):
                                ocf_val = float(ocf)
                                capex_val = float(capex) if pd.notnull(capex) else 0.0
                                # yfinance capex is usually negative, so add it
                                fcf_vals.append(ocf_val + capex_val)
                        res['quarterly_fcf'] = fcf_vals
            except Exception:
                pass

            yf_f["success"] += 1
            return res, delta  # success — exit retry loop

        except Exception as e:
            last_exc = e
            exc_str = str(e).lower()
            if _is_auth_or_rate_error(exc_str) and attempt < _YF_MAX_RETRIES - 1:
                # Reset session on auth failure so next attempt gets fresh crumb
                if "401" in exc_str or "crumb" in exc_str or "unauthorized" in exc_str:
                    reset_yf_session()
                sleep_secs = _YF_BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1.5)
                time.sleep(sleep_secs)
                continue  # retry
            break  # non-retryable error or max retries hit

    record_yfinance_exception(delta, yf_f, ticker, last_exc)
    return res, delta


def fetch_cached_fundamentals_24h(ticker, finnhub_key=None):
    """Thread-safe fetch with cache hit/miss telemetry (L1 memory + L2 disk). Returns (data, delta)."""
    delta = new_api_telemetry_delta()
    cache_key = (ticker, finnhub_key or "")
    now = time.time()
    
    # 1. Check L1 Memory Cache
    with _TELEMETRY_CACHE_LOCK:
        entry = _FUNDAMENTALS_DATA_CACHE.get(cache_key)
        if entry and entry[0] > now:
            delta["cache_hit_fundamentals"] = 1
            delta["finnhub_fundamentals"]["cache_hit"] = 1
            delta["yfinance_fundamentals"]["cache_hit"] = 1
            return copy.deepcopy(entry[1]), delta

    # 2. Check L2 Disk Cache
    disk_data = _load_from_disk("fundamentals", ticker)
    if disk_data is not None:
        delta["cache_hit_fundamentals"] = 1
        delta["finnhub_fundamentals"]["cache_hit"] = 1
        delta["yfinance_fundamentals"]["cache_hit"] = 1
        # Store in L1 Memory Cache
        with _TELEMETRY_CACHE_LOCK:
            _FUNDAMENTALS_DATA_CACHE[cache_key] = (now + TTL_FUNDAMENTALS_SEC, copy.deepcopy(disk_data))
        return copy.deepcopy(disk_data), delta

    # 3. Cache Miss: Fetch fresh data
    data, api_delta = _fetch_fundamentals_pure(ticker, finnhub_key)
    merge_api_telemetry_delta(delta, api_delta)
    delta["cache_miss_fundamentals"] = 1
    delta["finnhub_fundamentals"]["cache_miss"] = 1
    delta["yfinance_fundamentals"]["cache_miss"] = 1
    
    # Save to both L1 Memory Cache and L2 Disk Cache — ONLY if data is valid.
    # Skipping invalid/empty data prevents failed API responses from poisoning the cache.
    if _is_valid_data("fundamentals", data):
        expiry = now + TTL_FUNDAMENTALS_SEC
        with _TELEMETRY_CACHE_LOCK:
            _FUNDAMENTALS_DATA_CACHE[cache_key] = (expiry, copy.deepcopy(data))
        _save_to_disk("fundamentals", ticker, expiry, data)
    return data, delta


def _fetch_earnings_pure(ticker, finnhub_key=None):
    """Fetch earnings only (no session_state). Returns (data, telemetry_delta)."""
    delta = new_api_telemetry_delta()
    res = {
        'next_earnings_date': None,
        'last_earnings_date': None,
        'hist_earnings_dates': [],
        'calendar_status': "Not Fetched",
        'earnings_dates_status': "Not Fetched"
    }
    today = datetime.date.today()
    fh = delta["finnhub_earnings"]
    yf_e = delta["yfinance_earnings"]

    if finnhub_key:
        fh["attempted"] += 1
        try:
            _from = today.strftime('%Y-%m-%d')
            _to = (today + datetime.timedelta(days=90)).strftime('%Y-%m-%d')
            earn_res = requests.get(
                f'https://finnhub.io/api/v1/calendar/earnings?from={_from}&to={_to}&symbol={ticker}&token={finnhub_key}',
                timeout=3
            )
            if earn_res.status_code == 200:
                fh["success"] += 1
                earn = earn_res.json().get('earningsCalendar', [])
                if earn:
                    ed_str = earn[0].get('date')
                    if ed_str:
                        res['next_earnings_date'] = datetime.datetime.strptime(ed_str, '%Y-%m-%d').date()
                        res['calendar_status'] = "Found in Finnhub"
            else:
                record_http_status(delta, fh, ticker, earn_res.status_code)
        except requests.exceptions.RequestException as e:
            record_request_exception(delta, fh, ticker, e)

    yf_e["attempted"] += 1
    last_exc = None
    for attempt in range(_YF_MAX_RETRIES):
        try:
            _yf_earnings_acquire()  # lightweight earnings rate limit (15 RPS)
            t = yf.Ticker(ticker, session=_get_yf_session())
            # Try history first, as it contains both past and future dates
            try:
                _yf_earnings_acquire()
                ed = t.earnings_dates
                if ed is not None and not ed.empty:
                    hist_dates = []
                    for d in ed.index:
                        try:
                            hist_dates.append(d.date() if hasattr(d, 'date') else d)
                        except Exception:
                            pass
                    res['hist_earnings_dates'] = hist_dates
                    res['earnings_dates_status'] = f"Found {len(hist_dates)} dates (YF)"
                    past_dates = sorted([d for d in hist_dates if d < today], reverse=True)
                    if past_dates:
                        res['last_earnings_date'] = past_dates[0]
                    future_dates = sorted([d for d in hist_dates if d >= today])
                    if future_dates and not res['next_earnings_date']:
                        res['next_earnings_date'] = future_dates[0]
                        res['calendar_status'] = "Found in YF Earnings History"
                else:
                    res['earnings_dates_status'] = "No Historical Dates (YF)"
            except Exception as e:
                exc_str = str(e).lower()
                if _is_auth_or_rate_error(exc_str):
                    raise  # bubble up so outer retry loop catches it
                # Also retry on transient yfinance structural errors (KeyError/AttributeError)
                # that occur when Yahoo Finance returns unexpected data on a single attempt.
                if isinstance(e, (KeyError, AttributeError)) and attempt < _YF_MAX_RETRIES - 1:
                    raise  # bubble up to trigger retry with backoff
                res['earnings_dates_status'] = f"YF Earnings Error: {e}"

            # Only call t.calendar if t.earnings_dates did not yield a next_earnings_date
            if not res['next_earnings_date']:
                try:
                    _yf_earnings_acquire()
                    cal = t.calendar
                    if isinstance(cal, dict) and 'Earnings Date' in cal:
                        dates = cal['Earnings Date']
                        if isinstance(dates, list) and dates:
                            d = dates[0]
                            res['next_earnings_date'] = d.date() if hasattr(d, 'date') else d
                            res['calendar_status'] = "Found in YF Calendar"
                except Exception as e:
                    exc_str = str(e).lower()
                    if _is_auth_or_rate_error(exc_str):
                        raise  # bubble up so outer retry loop catches it
                    res['calendar_status'] = f"YF Calendar Error: {e}"

            yf_e["success"] += 1
            return res, delta  # success — exit retry loop

        except Exception as e:
            last_exc = e
            exc_str = str(e).lower()
            if _is_auth_or_rate_error(exc_str) and attempt < _YF_MAX_RETRIES - 1:
                if "401" in exc_str or "crumb" in exc_str or "unauthorized" in exc_str:
                    reset_yf_session()
                sleep_secs = _YF_BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1.5)
                time.sleep(sleep_secs)
                continue  # retry
            break  # non-retryable or max retries hit

    record_yfinance_exception(delta, yf_e, ticker, last_exc)
    return res, delta


def fetch_cached_earnings_12h(ticker, finnhub_key=None):
    """Thread-safe fetch with cache hit/miss telemetry (L1 memory + L2 disk). Returns (data, delta)."""
    delta = new_api_telemetry_delta()
    cache_key = (ticker, finnhub_key or "")
    now = time.time()
    
    # 1. Check L1 Memory Cache
    with _TELEMETRY_CACHE_LOCK:
        entry = _EARNINGS_DATA_CACHE.get(cache_key)
        if entry and entry[0] > now:
            delta["cache_hit_earnings"] = 1
            delta["finnhub_earnings"]["cache_hit"] = 1
            delta["yfinance_earnings"]["cache_hit"] = 1
            return copy.deepcopy(entry[1]), delta

    # 2. Check L2 Disk Cache
    disk_data = _load_from_disk("earnings", ticker)
    if disk_data is not None:
        delta["cache_hit_earnings"] = 1
        delta["finnhub_earnings"]["cache_hit"] = 1
        delta["yfinance_earnings"]["cache_hit"] = 1
        # Store in L1 Memory Cache
        with _TELEMETRY_CACHE_LOCK:
            _EARNINGS_DATA_CACHE[cache_key] = (now + TTL_EARNINGS_SEC, copy.deepcopy(disk_data))
        return copy.deepcopy(disk_data), delta

    # 3. Cache Miss: Fetch fresh data
    data, api_delta = _fetch_earnings_pure(ticker, finnhub_key)
    merge_api_telemetry_delta(delta, api_delta)
    delta["cache_miss_earnings"] = 1
    delta["finnhub_earnings"]["cache_miss"] = 1
    delta["yfinance_earnings"]["cache_miss"] = 1
    
    # Save to both L1 Memory Cache and L2 Disk Cache — ONLY if data is valid.
    # Skipping invalid/empty data prevents failed API responses from poisoning the cache.
    if _is_valid_data("earnings", data):
        expiry = now + TTL_EARNINGS_SEC
        with _TELEMETRY_CACHE_LOCK:
            _EARNINGS_DATA_CACHE[cache_key] = (expiry, copy.deepcopy(data))
        _save_to_disk("earnings", ticker, expiry, data)
    return data, delta


def _fetch_sec_pure(ticker, cik=None):
    """Fetch SEC filings only (no session_state). Returns (data, telemetry_delta)."""
    delta = new_api_telemetry_delta()
    res = {
        'sec_filings': [],
        'sec_status': "Not Fetched"
    }
    sec = delta["sec_edgar"]
    if not cik:
        sec["skipped_no_cik"] += 1
        res['sec_status'] = "Skipped (no CIK)"
        return res, delta

    sec["attempted"] += 1
    try:
        _sec_acquire()  # honor SEC rate limit (10/sec)
        headers = {'User-Agent': 'StockScreenerApp admin@example.com'}
        sec_res = requests.get(
            f'https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json',
            headers=headers, timeout=5
        )
        if sec_res.status_code == 200:
            sec["success"] += 1
            sec_data = sec_res.json()
            recent = sec_data.get('filings', {}).get('recent', {})
            forms = recent.get('form', [])
            dates = recent.get('filingDate', [])
            filings = []
            for idx, form in enumerate(forms):
                if form in ['8-K', '10-Q', '10-K', 'S-1', '6-K']:
                    filing_item = {
                        'form': form,
                        'filingDate': dates[idx],
                        'filedAt': dates[idx],
                        'description': recent.get('primaryDocDescription', [f"Recent {form} filing"])[idx] if 'primaryDocDescription' in recent and idx < len(recent['primaryDocDescription']) else f"Recent {form} filing",
                        'primaryDocDescription': recent.get('primaryDocDescription', [f"Recent {form} filing"])[idx] if 'primaryDocDescription' in recent and idx < len(recent['primaryDocDescription']) else f"Recent {form} filing",
                        'acceptanceDateTime': recent.get('acceptanceDateTime', [dates[idx]])[idx] if 'acceptanceDateTime' in recent and idx < len(recent['acceptanceDateTime']) else dates[idx],
                        'accessionNumber': recent.get('accessionNumber', [""])[idx] if 'accessionNumber' in recent and idx < len(recent['accessionNumber']) else ""
                    }
                    filings.append(filing_item)
                    if len(filings) >= 5:
                        break
            res['sec_filings'] = filings
            res['sec_status'] = "Success"
        else:
            res['sec_status'] = f"HTTP {sec_res.status_code}"
            record_http_status(delta, sec, ticker, sec_res.status_code)
    except requests.exceptions.RequestException as e:
        res['sec_status'] = str(e)
        record_request_exception(delta, sec, ticker, e)
    return res, delta


def fetch_cached_sec_24h(ticker, cik=None):
    """Thread-safe fetch with cache hit/miss telemetry (L1 memory + L2 disk). Returns (data, delta)."""
    delta = new_api_telemetry_delta()
    cache_key = (ticker, cik or "")
    now = time.time()
    
    # 1. Check L1 Memory Cache
    with _TELEMETRY_CACHE_LOCK:
        entry = _SEC_DATA_CACHE.get(cache_key)
        if entry and entry[0] > now:
            delta["cache_hit_sec"] = 1
            delta["sec_edgar"]["cache_hit"] = 1
            return copy.deepcopy(entry[1]), delta

    # 2. Check L2 Disk Cache
    disk_data = _load_from_disk("sec", ticker)
    if disk_data is not None:
        delta["cache_hit_sec"] = 1
        delta["sec_edgar"]["cache_hit"] = 1
        # Store in L1 Memory Cache
        with _TELEMETRY_CACHE_LOCK:
            _SEC_DATA_CACHE[cache_key] = (now + TTL_SEC_SEC, copy.deepcopy(disk_data))
        return copy.deepcopy(disk_data), delta

    # 3. Cache Miss: Fetch fresh data
    data, api_delta = _fetch_sec_pure(ticker, cik)
    merge_api_telemetry_delta(delta, api_delta)
    delta["cache_miss_sec"] = 1
    delta["sec_edgar"]["cache_miss"] = 1
    
    # Save to both L1 Memory Cache and L2 Disk Cache
    expiry = now + TTL_SEC_SEC
    with _TELEMETRY_CACHE_LOCK:
        _SEC_DATA_CACHE[cache_key] = (expiry, copy.deepcopy(data))
    _save_to_disk("sec", ticker, expiry, data)
    return data, delta


def new_api_telemetry_snapshot():
    """In-memory telemetry dict (same shape as st.session_state.api_telemetry)."""
    return {
        "finnhub_fundamentals": _empty_api_service_metrics(),
        "finnhub_earnings": _empty_api_service_metrics(),
        "sec_edgar": _empty_api_service_metrics(include_sec_skip=True),
        "yfinance_fundamentals": _empty_api_service_metrics(),
        "yfinance_earnings": _empty_api_service_metrics(),
        "cache_hit_fundamentals": 0,
        "cache_miss_fundamentals": 0,
        "cache_hit_earnings": 0,
        "cache_miss_earnings": 0,
        "cache_hit_sec": 0,
        "cache_miss_sec": 0,
        "deep_scan_candidate_count": 0,
        "total_api_attempts": 0,
        "total_api_failures": 0,
        "rate_limit_failures": 0,
        "candidates_skipped_due_to_missing_fundamentals": 0,
        "candidates_skipped_due_to_missing_earnings": 0,
        "candidates_skipped_due_to_api_failure": 0,
        "error_categories": _empty_error_categories(),
        "concurrency": build_concurrency_snapshot(),
        "last_errors": [],
    }
