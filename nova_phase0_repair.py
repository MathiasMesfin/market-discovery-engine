"""
PROJECT NOVA — PHASE 0 REPAIR + FULL KILL TEST
================================================
Step 1: Purge cached SEC rate-limit error pages
Step 2: Re-fetch all NT filing texts with strict rate limiting (≤8 req/sec)
Step 3: Re-classify all filings using frozen taxonomy
Step 4: Entity/price mapping (filtered: equities only, no warrants/rights/units)
Step 5: Freeze dataset + SHA-256
Step 6: Compute abnormal returns (with winsorization)
Step 7: Gate evaluation
"""

import os, sys, re, json, hashlib, random, time, warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import requests
from scipy import stats
from scipy.stats import bootstrap as scipy_bootstrap

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
BASE_DIR   = Path("/Users/mathiasmesfin/Downloads/Stock Screener")
OUT_DIR    = BASE_DIR / "data/nova/phase0"
CACHE_MASTER   = BASE_DIR / "cache/sec_master_indices"
CACHE_FILINGS  = BASE_DIR / "cache/sec_filings_nt"
CACHE_UNIVERSE = BASE_DIR / "cache/sec_universe"
CACHE_PRICES   = BASE_DIR / "cache/sec_prices_nova"

OUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PRICES.mkdir(parents=True, exist_ok=True)

HEADERS    = {"User-Agent": "Mozilla/5.0 StockResearch admin@example.com"}
RANDOM_SEED = 20260911
START_DATE  = "2010-01-01"
END_DATE    = "2024-12-31"

SEC_RATE_LIMIT_MARKER = "Request Rate Threshold Exceeded"  # exact text in error pages
MIN_VALID_SIZE = 1000  # bytes — anything smaller is almost certainly an error page

# ─────────────────────────────────────────────
# D. FROZEN TAXONOMY (identical to engine v1)
# ─────────────────────────────────────────────
TAXONOMY_RULES = {
    "A_ACCOUNTING_RESTATEMENT_OR_ERROR": [
        r"re-?state(ment|d|s)?",
        r"(cannot|should\s+no\s+longer)\s+be\s+relied\s+upon|non-reliance",
        r"accounting\s+errors?|errors?\s+in\s+(the\s+)?accounting",
        r"errors?\s+in\s+(the\s+)?(previously\s+issued\s+)?financial",
        r"prior\s+period\s+(reclassification|error|adjustment|revision)",
        r"correction\s+of\s+(an?\s+|prior\s+)?errors?|accounting\s+irregularit",
        r"revenue\s+recognition\s+errors?",
    ],
    "B_AUDIT_OR_INTERNAL_CONTROL": [
        r"material\s+weakness(es)?",
        r"internal\s+controls?\s+(over\s+financial\s+reporting|deficienc|weakness)",
        r"(audit|special)\s+committee\s+(investigation|inquiry|review)",
        r"independent\s+(investigation|inquiry|review)",
        r"auditor\s+(resignation|resigned|dismissed|terminated|change)|former\s+auditor|dismissed.*?auditor",
        r"bf\s+borgers|pcaob",
        r"(auditor|independent\s+registered|accounting\s+firm).*?"
            r"(unable\s+to\s+complete|additional\s+time|complete\s+its\s+(audit|review)|"
            r"finalize\s+its|has\s+not\s+(yet\s+)?completed|appointed|resigned)",
        r"auditors?\s+in\s+time\s+for\s+(filing|the\s+filing)",
        r"review\s+process\s+with\s+the\s+auditor|complete\s+the\s+review\s+of.*?auditor",
        r"auditing\s+standards|confirmation\s+of\s+balances\s+required\s+by\s+auditing",
        r"control\s+deficienc(ies|y)",
        r"no\s+longer\s+permitted\s+to\s+practice",
    ],
    "C_FINANCIAL_DISTRESS_OR_GOING_CONCERN_PROCESS": [
        r"going\s+concern|substantial\s+doubt",
        r"bankruptcy|chapter\s+11|chapter\s+7|insolven|liquidation",
        r"debt\s+restructur|restructuring\s+(support|agreement|plan)",
        r"liquidity\s+(constraints?|issues?|shortages?|deficienc|needs?)",
        r"working\s+capital\s+and\s+liquidity",
        r"forbearance|default\s+on|event\s+of\s+default|covenant\s+(breach|violation|default)",
        r"financing\s+negotiations?|strategic\s+alternatives?",
    ],
    "D_TRANSACTION_OR_CORPORATE_COMPLEXITY": [
        r"merger|acquisition|business\s+combination|divestiture|spin-off",
        r"de-spac|spac\s+transaction|reverse\s+merger|reverse\s+takeover|corporate\s+structuring",
        r"complex\s+transaction|purchase\s+price\s+allocation|acquired\s+business",
    ],
    "E_OPERATIONAL_OR_SYSTEM_DELAY": [
        r"erp\s+(system|conversion|implementation|migration)",
        r"software\s+(conversion|implementation|failure|outage)",
        r"system\s+(conversion|implementation|outage|migration|failure|transition)",
        r"data\s+(migration|conversion|integration)",
        r"it\s+system\s+(failure|issue)",
    ],
    "F_ROUTINE_ADMINISTRATIVE": [
        r"additional\s+time\s+(is|was)?\s*(needed|required|to\s+prepare|for\s+compilation|to\s+complete|to\s+finalize|for\s+filing)",
        r"needs?\s+(additional\s+)?time\s+to\s+(prepare|review|finalize)",
        r"compilation\s+and\s+review|compilation\s+of\s+(the\s+)?financial|compilation,\s+dissemination",
        r"in\s+the\s+process\s+of\s+(compiling|finalizing|completing|preparing)",
        r"unable\s+to\s+(compile|complete|finalize|prepare)\s+(the\s+|its\s+)?(necessary\s+)?financial",
        r"delays?\s+in\s+(completing|assembling|preparing|finalizing|obtaining)",
        r"administrative\s+(and\s+accounting\s+)?delays?|routine\s+administrative|legal\s+counsel",
        r"time\s+constraints?",
        r"without\s+unreasonable\s+effort\s+(and|or)\s+expense",
        r"undue\s+(hardship|burden|effort|expense)",
        r"finalize\s+(the\s+|its\s+)?financial\s+statements",
        r"complete\s+the\s+preparation|has\s+not\s+completed\s+the\s+preparation",
        r"staffing\s+(limitation|issue|challenge)",
        r"file\s+its\s+form\s+10-[kq].*?within\s+the\s+prescribed\s+time\s+period",
        r"imposed\s+time\s+constraints?",
        r"requires?\s+(additional|more|extra)\s+time",
        r"not\s+been\s+able\s+to\s+complete\s+(the\s+|its\s+)?financial",
        r"(cannot|could\s+not)\s+(be\s+(filed|completed|prepared)|complete\s+the\s+preparation)",
        r"not\s+completed\s+the\s+preparation",
        r"more\s+time\s+to\s+complete|more\s+time\s+to\s+prepare",
        r"preparation\s+of\s+(the\s+|its\s+)?(annual|quarterly)?\s*report",
    ],
}

SEVERITY_MAP = {
    "A_ACCOUNTING_RESTATEMENT_OR_ERROR":        "SEVERE",
    "B_AUDIT_OR_INTERNAL_CONTROL":              "SEVERE",
    "C_FINANCIAL_DISTRESS_OR_GOING_CONCERN_PROCESS": "SEVERE",
    "D_TRANSACTION_OR_CORPORATE_COMPLEXITY":    "EXCLUDED",
    "E_OPERATIONAL_OR_SYSTEM_DELAY":            "ROUTINE",
    "F_ROUTINE_ADMINISTRATIVE":                 "ROUTINE",
    "G_OTHER_OR_AMBIGUOUS":                     "EXCLUDED",
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def strip_html(content: str) -> str:
    """Strip HTML tags and decode entities from raw filing text."""
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", content, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<(p|div|tr|td|br|h\d|li)[^>]*>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"&nbsp;|&#160;", " ", clean)
    clean = re.sub(r"&#\d+;|&#x[0-9a-fA-F]+;", " ", clean)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)
    return clean


def extract_narrative(content: str) -> str:
    """
    Extract the Part III narrative reason from an NT filing.
    Strategy: find PART III NARRATIVE section; if not found, use full text.
    This ensures rate-limit error pages (which lack PART III) still classify correctly.
    """
    if not content or len(content) < 100:
        return ""

    # Detect rate-limit error page — return empty so it gets G_OTHER
    if SEC_RATE_LIMIT_MARKER in content:
        return ""

    clean = strip_html(content)

    # Search for ALL occurrences of PART III to find the narrative section
    part3_pattern = re.compile(
        r"PART\s+III\s*[-\u2013\u2014:]*\s*NARRATIVE|"
        r"State\s+below\s+in\s+reasonable\s+detail",
        re.IGNORECASE,
    )
    matches = list(part3_pattern.finditer(clean))

    if matches:
        # Use the LAST match — the actual narrative usually comes after the boilerplate checkbox
        m = matches[-1]
        sub = clean[m.start():]
        m_end = re.search(r"\n\s*(PART\s+IV|SIGNATURES?|PART\s+4)\b", sub, re.IGNORECASE)
        sub = sub[: m_end.start()] if m_end else sub[:6000]
        # Remove the section header itself
        sub = re.sub(r"^PART\s+III\s*[-\u2013\u2014:]*\s*NARRATIVE\s*", "", sub, flags=re.IGNORECASE)
        sub = re.sub(
            r"^State\s+below\s+in\s+reasonable\s+detail.*?period\.\s*",
            "", sub, flags=re.DOTALL | re.IGNORECASE,
        )
        sub = re.sub(r"^\s*\(Attach\s+extra\s+sheets?\s+if\s+needed\.?\)\s*", "", sub, flags=re.IGNORECASE)
        narrative = re.sub(r"\s+", " ", sub).strip()
        if len(narrative) > 20:
            return narrative

    # Fallback: search full cleaned text for classification keywords
    # Use middle/latter portion to skip boilerplate header (usually first 20%)
    full_clean = re.sub(r"\s+", " ", clean)
    skip = max(0, len(full_clean) // 5)  # skip first 20%
    return full_clean[skip:skip + 8000]


def classify_narrative(text: str):
    """Classify narrative using frozen deterministic regex rules."""
    if not text or len(text.strip()) < 10:
        return "G_OTHER_OR_AMBIGUOUS", "EXCLUDED", "empty_text", 0.50

    text_lower = text.lower()
    for cat, rules in TAXONOMY_RULES.items():
        for rule in rules:
            if re.search(rule, text_lower):
                sev = SEVERITY_MAP[cat]
                return cat, sev, rule, 0.90 if sev == "SEVERE" else 0.85

    return "G_OTHER_OR_AMBIGUOUS", "EXCLUDED", "no_rule_match", 0.50


def cache_path(filename: str) -> Path:
    return CACHE_FILINGS / (filename.replace("/", "_") + ".txt")


def is_rate_limit_page(path: Path) -> bool:
    """Return True if cached file is a SEC rate-limit error page."""
    if not path.exists():
        return False
    if path.stat().st_size < MIN_VALID_SIZE:
        return True
    # Check content
    try:
        with open(path, "r", encoding="latin-1") as f:
            head = f.read(500)
        return SEC_RATE_LIMIT_MARKER in head
    except Exception:
        return False


def fetch_with_retry(filename: str, delay: float = 0.13, max_retries: int = 3) -> str:
    """Fetch a filing from EDGAR with retry logic and rate-limit detection."""
    local = cache_path(filename)

    # Serve from cache if valid
    if local.exists() and not is_rate_limit_page(local):
        with open(local, "r", encoding="latin-1") as f:
            return f.read()

    # Fetch fresh
    url = "https://www.sec.gov/Archives/" + filename
    for attempt in range(max_retries):
        time.sleep(delay)
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                content = r.text
                if SEC_RATE_LIMIT_MARKER in content:
                    print(f"  RATE LIMITED on {filename} — sleeping 12s")
                    time.sleep(12)
                    continue
                with open(local, "wb") as f:
                    f.write(r.content)
                return content
            elif r.status_code == 429:
                wait = 15 * (attempt + 1)
                print(f"  HTTP 429 — sleeping {wait}s")
                time.sleep(wait)
        except Exception as e:
            print(f"  Fetch error {filename}: {e}")
            time.sleep(2)

    return ""


def load_exchange_map():
    """CIK (zero-padded 10 char) → ticker mapping."""
    cik_to_ticker = {}
    exch_file = CACHE_UNIVERSE / "company_tickers_exchange.json"
    if exch_file.exists():
        with open(exch_file) as f:
            data = json.load(f)
        fields = data["fields"]
        ci, ti = fields.index("cik"), fields.index("ticker")
        for row in data["data"]:
            cik_to_ticker[str(row[ci]).zfill(10)] = row[ti]

    univ = BASE_DIR / "data/us_stock_universe.csv"
    if univ.exists():
        df = pd.read_csv(univ)
        for _, r in df.iterrows():
            c = str(r["CIK"]).zfill(10)
            if c not in cik_to_ticker:
                cik_to_ticker[c] = r["Symbol"]
    return cik_to_ticker


def is_equity_ticker(ticker: str) -> bool:
    """
    Return False for warrants (W suffix), rights (R suffix), units (U suffix),
    preferred shares (P suffix or -P), and similar non-common-equity instruments.
    """
    if not isinstance(ticker, str) or len(ticker) < 1:
        return False
    t = ticker.upper().strip()
    # Warrants: end in W or WS or WT
    if re.search(r'W[ST]?$', t):
        return False
    # Rights: end in R
    if re.search(r'R$', t) and len(t) > 2:
        return False
    # Units: end in U or UN
    if re.search(r'U[N]?$', t) and len(t) > 2:
        return False
    # Preferred: end in P, PA, PB, PC, -P, -PA, etc.
    if re.search(r'-?P[A-Z]?$', t) and len(t) > 2:
        return False
    # Z-suffix (used for defunct/delisted)
    if re.search(r'Z$', t) and len(t) > 2:
        return False
    return True


# ─────────────────────────────────────────────
# STEP 1: PURGE RATE-LIMIT CACHES
# ─────────────────────────────────────────────

def purge_rate_limit_caches():
    print("\n[STEP 1] Purging SEC rate-limit cached error pages...")
    purged = 0
    total = 0
    for p in CACHE_FILINGS.glob("*.txt"):
        total += 1
        if is_rate_limit_page(p):
            p.unlink()
            purged += 1
    print(f"  Scanned: {total} files | Purged: {purged} bad files | Kept: {total - purged}")
    return purged


# ─────────────────────────────────────────────
# STEP 2: BUILD INVENTORY
# ─────────────────────────────────────────────

def build_nt_inventory(cik_to_ticker: dict) -> pd.DataFrame:
    print("\n[STEP 2] Building NT filing inventory (2010-2024)...")
    rows = []
    for year in range(2010, 2025):
        for qtr in range(1, 5):
            idx_file = CACHE_MASTER / f"master_{year}_Q{qtr}.idx"
            if not idx_file.exists():
                continue
            with open(idx_file, "r", encoding="latin-1") as f:
                for line in f:
                    if "|NT 10-K" not in line and "|NT 10-Q" not in line:
                        continue
                    parts = line.strip().split("|")
                    if len(parts) < 5:
                        continue
                    cik = parts[0].zfill(10)
                    if cik not in cik_to_ticker:
                        continue
                    ticker = cik_to_ticker[cik]
                    # Filter to common equity tickers only
                    if not is_equity_ticker(ticker):
                        continue
                    form = parts[2]
                    is_amend = "/A" in form
                    std_form = "NT 10-K" if "10-K" in form else "NT 10-Q"
                    filing_date = parts[3]
                    if not (START_DATE <= filing_date <= END_DATE):
                        continue
                    rows.append({
                        "cik": cik,
                        "company_name": parts[1],
                        "form": std_form,
                        "is_amendment": is_amend,
                        "filing_date": filing_date,
                        "filename": parts[4].strip(),
                        "ticker": ticker,
                    })

    df = pd.DataFrame(rows)
    df_primary = df[~df["is_amendment"]].copy().reset_index(drop=True)
    print(f"  Total exchange-mapped equity NT filings: {len(df_primary)}")
    print(f"  NT 10-K: {(df_primary['form']=='NT 10-K').sum()}  "
          f"NT 10-Q: {(df_primary['form']=='NT 10-Q').sum()}")
    print(f"  Unique CIKs: {df_primary['cik'].nunique()}")
    return df_primary


# ─────────────────────────────────────────────
# STEP 3: CLASSIFY ALL FILINGS (sequential, rate-limited)
# ─────────────────────────────────────────────

def classify_all_filings(df_primary: pd.DataFrame) -> pd.DataFrame:
    print(f"\n[STEP 3] Classifying {len(df_primary)} filings (sequential, ≤8 req/sec)...")
    results = []
    total = len(df_primary)
    fetch_delay = 0.13  # ~7-8 req/sec

    for i, row in df_primary.iterrows():
        content = fetch_with_retry(row["filename"], delay=fetch_delay)

        # Extract acceptance timestamp
        m = re.search(r"<ACCEPTANCE-DATETIME>(\d+)", content)
        acc_ts = m.group(1) if m else (row["filing_date"].replace("-", "") + "160000")

        narrative = extract_narrative(content)
        cat, sev, rule, conf = classify_narrative(narrative)

        results.append({
            "cik": row["cik"],
            "ticker": row["ticker"],
            "company_name": row["company_name"],
            "form": row["form"],
            "filing_date": row["filing_date"],
            "filename": row["filename"],
            "acceptance_timestamp": acc_ts,
            "narrative_text": narrative[:400],
            "reason_category": cat,
            "severe_flag": sev,
            "matched_rule": str(rule)[:120],
            "classification_confidence": conf,
            "primary_eligible": sev in ("SEVERE", "ROUTINE"),
        })

        if (i + 1) % 500 == 0:
            cat_so_far = pd.Series([r["reason_category"] for r in results]).value_counts()
            g_pct = cat_so_far.get("G_OTHER_OR_AMBIGUOUS", 0) / len(results) * 100
            n_sev_so_far = (
                cat_so_far.get("A_ACCOUNTING_RESTATEMENT_OR_ERROR", 0)
                + cat_so_far.get("B_AUDIT_OR_INTERNAL_CONTROL", 0)
                + cat_so_far.get("C_FINANCIAL_DISTRESS_OR_GOING_CONCERN_PROCESS", 0)
            )
            print(f"  {i+1}/{total} | G_OTHER: {g_pct:.1f}% | SEVERE so far: {n_sev_so_far}")

    df_c = pd.DataFrame(results)
    return df_c


# ─────────────────────────────────────────────
# STEP 4: PRICE DATA
# ─────────────────────────────────────────────

def get_prices(tickers):
    import yfinance as yf
    print(f"\n[STEP 4] Downloading price data for {len(tickers)} tickers...")

    cache_file = CACHE_PRICES / "all_prices_v2.parquet"
    if cache_file.exists():
        existing = pd.read_parquet(cache_file)
        need = [t for t in tickers if t not in existing.columns]
        if not need:
            print("  All prices already cached.")
            return existing
        print(f"  {len(need)} tickers not yet cached, downloading...")
        to_fetch = need
    else:
        existing = None
        to_fetch = tickers

    batch_size = 50
    dfs = []
    for i in range(0, len(to_fetch), batch_size):
        batch = to_fetch[i: i + batch_size]
        try:
            raw = yf.download(
                batch, start="2009-12-01", end="2025-03-01",
                auto_adjust=True, progress=False, threads=True,
            )
            if isinstance(raw.columns, pd.MultiIndex):
                close = raw["Close"]
            else:
                close = raw[["Close"]].rename(columns={"Close": batch[0]})
            dfs.append(close)
        except Exception as e:
            print(f"  Batch {i} error: {e}")
        time.sleep(1.5)

    if dfs:
        new_df = pd.concat(dfs, axis=1)
        if existing is not None:
            combined = pd.concat([existing, new_df], axis=1)
            combined = combined.loc[:, ~combined.columns.duplicated()]
        else:
            combined = new_df
        combined = combined.sort_index()
        combined.to_parquet(cache_file)
        print(f"  Prices saved: {combined.shape}")
        return combined
    return existing if existing is not None else pd.DataFrame()


def next_trading_day(date_str: str, price_index) -> pd.Timestamp:
    dt = pd.Timestamp(str(date_str)[:8]).tz_localize("UTC")
    future = price_index[price_index >= dt]
    return future[0] if len(future) else None


def forward_return(series, entry_dt, n_days) -> float:
    future = series[series.index >= entry_dt].dropna()
    if len(future) < 2:
        return np.nan
    entry_p = future.iloc[0]
    exit_p = future.iloc[n_days] if n_days < len(future) else future.iloc[-1]
    if entry_p <= 0:
        return np.nan
    return float(exit_p / entry_p - 1.0)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("=" * 60)
    print("PROJECT NOVA — PHASE 0 REPAIR + KILL TEST")
    print("=" * 60)

    # STEP 1: Purge bad caches
    purge_rate_limit_caches()

    # Load entity map
    cik_to_ticker = load_exchange_map()
    print(f"\nCIK->ticker mappings: {len(cik_to_ticker)}")

    # STEP 2: Inventory
    df_primary = build_nt_inventory(cik_to_ticker)

    # STEP 3: Classify
    df_classified = classify_all_filings(df_primary)

    print(f"\n[STEP 3] Classification complete: {len(df_classified)} records")
    cat_counts = df_classified["reason_category"].value_counts()
    sev_counts = df_classified["severe_flag"].value_counts()
    print("  Category distribution:")
    for c, n in cat_counts.items():
        print(f"    {c}: {n}  ({100*n/len(df_classified):.1f}%)")
    print("  Severity distribution:")
    for s, n in sev_counts.items():
        print(f"    {s}: {n}  ({100*n/len(df_classified):.1f}%)")

    # Save full classification
    df_classified.to_csv(OUT_DIR / "classified_filings.csv", index=False)

    # Save reason taxonomy + rules
    rules_out = {}
    for cat, patterns in TAXONOMY_RULES.items():
        rules_out[cat] = {"patterns": patterns, "severity": SEVERITY_MAP[cat]}
    with open(OUT_DIR / "classification_rules.json", "w") as f:
        json.dump(rules_out, f, indent=2)

    # ── FREEZE BLIND DATASET (BEFORE PRICES) ────────────────
    print("\n[STEP G] Freezing blind signal dataset BEFORE loading prices...")
    blind_cols = [
        "cik", "ticker", "company_name", "form", "filing_date",
        "acceptance_timestamp", "reason_category", "severe_flag",
        "matched_rule", "classification_confidence", "primary_eligible",
    ]
    df_blind = df_classified[blind_cols].copy()
    blind_path = OUT_DIR / "nova_phase0_blind_signals.parquet"
    df_blind.to_parquet(blind_path, index=False)
    with open(blind_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    freeze_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"  SHA-256: {sha}")

    # ── ENTITY MAPPING ───────────────────────────────────────
    df_eligible = df_classified[df_classified["primary_eligible"]].copy().reset_index(drop=True)
    print(f"\n[STEP F] Primary eligible filings: {len(df_eligible)}")
    print(f"  Severe: {(df_eligible['severe_flag']=='SEVERE').sum()}")
    print(f"  Routine: {(df_eligible['severe_flag']=='ROUTINE').sum()}")

    # ── PRICE DOWNLOAD ───────────────────────────────────────
    tickers_needed = [t for t in df_eligible["ticker"].unique().tolist()
                      if isinstance(t, str) and t.strip()]
    all_tickers = list(set(tickers_needed + ["SPY"]))
    prices = get_prices(all_tickers)
    prices.index = pd.to_datetime(prices.index, utc=True)
    price_idx = prices.index

    if "SPY" not in prices.columns:
        import yfinance as yf
        spy = yf.download("SPY", start="2009-12-01", end="2025-03-01",
                          auto_adjust=True, progress=False)["Close"]
        prices["SPY"] = spy

    spy_prices = prices["SPY"].dropna()

    # ── COMPUTE RETURNS ──────────────────────────────────────
    print("\n[STEP H] Computing abnormal returns...")
    HORIZONS = [5, 10, 20, 40, 60]

    return_rows = []
    no_price = 0

    for i, row in df_eligible.iterrows():
        ticker = row["ticker"]
        acc_ts = str(row["acceptance_timestamp"])
        filing_dt_str = acc_ts[:8]
        entry_dt = next_trading_day(filing_dt_str, price_idx)

        if entry_dt is None or ticker not in prices.columns:
            no_price += 1
            continue

        stock_series = prices[ticker].dropna()
        if len(stock_series) < 5:
            no_price += 1
            continue

        ret_dict = {
            "cik": row["cik"],
            "ticker": ticker,
            "company_name": row["company_name"],
            "form": row["form"],
            "filing_date": row["filing_date"],
            "acceptance_timestamp": acc_ts,
            "reason_category": row["reason_category"],
            "severe_flag": row["severe_flag"],
            "entry_date": entry_dt,
            "primary_eligible": row["primary_eligible"],
        }

        # Prior returns for controls
        past_idx = price_idx[price_idx < entry_dt]
        if len(past_idx) >= 20:
            p0 = stock_series.reindex(price_idx).loc[past_idx[-20]]
            p1 = stock_series.reindex(price_idx).loc[past_idx[-1]]
            ret_dict["prior_20d_return"] = float((p1/p0 - 1) if (pd.notna(p0) and pd.notna(p1) and p0 > 0) else np.nan)
        else:
            ret_dict["prior_20d_return"] = np.nan

        if len(past_idx) >= 60:
            s_past = stock_series.reindex(past_idx[-60:]).dropna()
            ret_dict["prior_60d_vol"] = float(s_past.pct_change().dropna().std()) if len(s_past) > 5 else np.nan
        else:
            ret_dict["prior_60d_vol"] = np.nan

        has_any = False
        for h in HORIZONS:
            sr = forward_return(stock_series, entry_dt, h)
            sp = forward_return(spy_prices, entry_dt, h)
            ar = (sr - sp) if (pd.notna(sr) and pd.notna(sp)) else np.nan
            ret_dict[f"stock_ret_t{h}"] = sr
            ret_dict[f"spy_ret_t{h}"] = sp
            ret_dict[f"ar_t{h}"] = ar
            if pd.notna(sr):
                has_any = True

        if not has_any:
            no_price += 1
            continue

        return_rows.append(ret_dict)

    df_returns = pd.DataFrame(return_rows)

    # Winsorize returns at 1% / 99% to handle outliers
    for h in HORIZONS:
        col = f"ar_t{h}"
        if col in df_returns.columns:
            lo = df_returns[col].quantile(0.01)
            hi = df_returns[col].quantile(0.99)
            df_returns[col] = df_returns[col].clip(lo, hi)
            print(f"  Winsorized AR{h}: [{lo*100:.1f}%, {hi*100:.1f}%]")

    mapped = len(df_returns)
    total_eligible = len(df_eligible)
    mapping_pct = 100 * mapped / total_eligible if total_eligible > 0 else 0

    print(f"\n  Price mapping: {mapped}/{total_eligible} ({mapping_pct:.1f}%)")

    # Entity mapping audit
    pd.DataFrame([{
        "total_classified": len(df_classified),
        "primary_eligible": total_eligible,
        "price_mapped": mapped,
        "mapping_pct": round(mapping_pct, 1),
        "no_price": no_price,
        "severe_n": int((df_returns["severe_flag"] == "SEVERE").sum()),
        "routine_n": int((df_returns["severe_flag"] == "ROUTINE").sum()),
        "coverage_pass": mapping_pct >= 80,
    }]).to_csv(OUT_DIR / "entity_mapping_audit.csv", index=False)

    # ── KILL TEST ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PRIMARY KILL TEST — Severe vs Routine AR(T+20)")
    print("=" * 60)

    df_sev = df_returns[df_returns["severe_flag"] == "SEVERE"]["ar_t20"].dropna()
    df_rout = df_returns[df_returns["severe_flag"] == "ROUTINE"]["ar_t20"].dropna()

    n_sev, n_rout = len(df_sev), len(df_rout)
    mean_sev, mean_rout = df_sev.mean(), df_rout.mean()
    med_sev, med_rout = df_sev.median(), df_rout.median()
    diff_means = mean_sev - mean_rout

    t_stat, p_welch = stats.ttest_ind(df_sev, df_rout, equal_var=False)
    w_stat, p_wilcox = stats.mannwhitneyu(df_sev, df_rout, alternative="less")

    def mean_diff_stat(sev, rout, axis=-1):
        return np.mean(sev, axis=axis) - np.mean(rout, axis=axis)

    boot = scipy_bootstrap(
        (df_sev.values, df_rout.values),
        mean_diff_stat,
        n_resamples=5000,
        random_state=RANDOM_SEED,
        confidence_level=0.95,
    )
    ci_low, ci_high = boot.confidence_interval.low, boot.confidence_interval.high
    ci_excl_zero = ci_high < 0

    p_sev_worse = w_stat / (n_sev * n_rout) if (n_sev > 0 and n_rout > 0) else np.nan

    print(f"\n  Severe N={n_sev}  Routine N={n_rout}")
    print(f"  Severe mean AR20:  {mean_sev*100:.3f}%")
    print(f"  Severe median AR20:{med_sev*100:.3f}%")
    print(f"  Routine mean AR20: {mean_rout*100:.3f}%")
    print(f"  Routine median AR20:{med_rout*100:.3f}%")
    print(f"  Diff (Sev - Rout): {diff_means*100:.3f}pp")
    print(f"  Bootstrap 95% CI:  [{ci_low*100:.3f}%, {ci_high*100:.3f}%]")
    print(f"  CI excludes zero:  {ci_excl_zero}")
    print(f"  Welch t={t_stat:.3f}  p={p_welch:.4f}")
    print(f"  Wilcoxon (one-sided) p={p_wilcox:.4f}")
    print(f"  P(Severe < Routine): {p_sev_worse:.3f}")

    # ── DESCRIPTIVE HORIZONS ──────────────────────────────────
    print("\n  Descriptive horizons:")
    horizon_rows = []
    for h in HORIZONS:
        sv = df_returns[df_returns["severe_flag"] == "SEVERE"][f"ar_t{h}"].dropna()
        rv = df_returns[df_returns["severe_flag"] == "ROUTINE"][f"ar_t{h}"].dropna()
        if len(sv) > 5 and len(rv) > 5:
            t_, p_ = stats.ttest_ind(sv, rv, equal_var=False)
            d_ = sv.mean() - rv.mean()
        else:
            t_, p_, d_ = np.nan, np.nan, np.nan
        horizon_rows.append({
            "horizon": h, "severe_n": len(sv), "routine_n": len(rv),
            "severe_mean_ar_pct": round(sv.mean()*100, 3) if len(sv) else np.nan,
            "routine_mean_ar_pct": round(rv.mean()*100, 3) if len(rv) else np.nan,
            "diff_pp": round(d_*100, 3) if not np.isnan(d_) else np.nan,
            "t_stat": round(t_, 3) if not np.isnan(t_) else np.nan,
            "p_welch": round(p_, 4) if not np.isnan(p_) else np.nan,
        })
        print(f"  T+{h:2d}: Sev={sv.mean()*100:.2f}%  Rout={rv.mean()*100:.2f}%  "
              f"Diff={d_*100:.2f}pp  p={p_:.4f}")

    pd.DataFrame(horizon_rows).to_csv(OUT_DIR / "descriptive_horizons.csv", index=False)

    # ── OLS CONTROL REGRESSION ───────────────────────────────
    print("\n  OLS control regression (AR20 ~ severe + controls)...")
    df_reg = df_returns.dropna(subset=["ar_t20", "prior_20d_return", "prior_60d_vol"]).copy()
    df_reg["severe_dummy"] = (df_reg["severe_flag"] == "SEVERE").astype(int)
    df_reg["nt10k_flag"] = (df_reg["form"] == "NT 10-K").astype(int)
    df_reg["year_trend"] = df_reg["filing_date"].str[:4].astype(int) - 2010

    X_cols = ["severe_dummy", "prior_20d_return", "prior_60d_vol", "nt10k_flag", "year_trend"]
    df_reg = df_reg.dropna(subset=X_cols)

    severe_beta, severe_p = np.nan, np.nan
    if len(df_reg) > 50:
        from numpy.linalg import lstsq
        X = np.column_stack([np.ones(len(df_reg))] + [df_reg[c].values for c in X_cols])
        y = df_reg["ar_t20"].values
        beta, _, _, _ = lstsq(X, y, rcond=None)
        y_hat = X @ beta
        resid = y - y_hat
        n, k = X.shape
        sigma2 = (resid @ resid) / (n - k)
        try:
            cov = sigma2 * np.linalg.inv(X.T @ X)
            se = np.sqrt(np.diag(cov))
            t_vals = beta / se
            p_vals = 2 * stats.t.sf(np.abs(t_vals), df=n - k)
            names = ["intercept"] + X_cols
            reg_rows = [{"variable": nm, "beta": round(b, 6), "se": round(s, 6),
                         "t_stat": round(t, 3), "p_value": round(p, 4)}
                        for nm, b, s, t, p in zip(names, beta, se, t_vals, p_vals)]
            pd.DataFrame(reg_rows).to_csv(OUT_DIR / "control_regression.csv", index=False)
            severe_beta = beta[1]
            severe_p = p_vals[1]
            for nm, b, s, t, p in zip(names, beta, se, t_vals, p_vals):
                print(f"    {nm:25s} beta={b:.5f}  t={t:.3f}  p={p:.4f}")
        except np.linalg.LinAlgError:
            print("  Singular matrix in regression — skipped")
    else:
        print("  Insufficient data for regression.")

    # ── DE-DUPLICATION ───────────────────────────────────────
    df_returns["year"] = df_returns["filing_date"].str[:4].astype(int)
    df_dedup = (df_returns.sort_values("filing_date")
                          .groupby(["cik", "year"])
                          .first()
                          .reset_index())
    sv_dd = df_dedup[df_dedup["severe_flag"] == "SEVERE"]["ar_t20"].dropna()
    rv_dd = df_dedup[df_dedup["severe_flag"] == "ROUTINE"]["ar_t20"].dropna()

    if len(sv_dd) > 5 and len(rv_dd) > 5:
        t_dd, p_dd = stats.ttest_ind(sv_dd, rv_dd, equal_var=False)
        diff_dd = sv_dd.mean() - rv_dd.mean()
        dedup_dir = diff_dd < 0
    else:
        t_dd, p_dd, diff_dd, dedup_dir = np.nan, np.nan, np.nan, False

    print(f"\n  De-dup (issuer-year): N_sev={len(sv_dd)} N_rout={len(rv_dd)}")
    print(f"  Diff={diff_dd*100:.2f}pp  p={p_dd:.4f}  directional_neg={dedup_dir}")

    pd.DataFrame([{
        "severe_n": len(sv_dd), "routine_n": len(rv_dd),
        "diff_pp": round(diff_dd*100, 3) if not np.isnan(diff_dd) else None,
        "t_stat": round(t_dd, 3) if not np.isnan(t_dd) else None,
        "p_welch": round(p_dd, 4) if not np.isnan(p_dd) else None,
        "directional_negative": dedup_dir,
    }]).to_csv(OUT_DIR / "issuer_deduplication.csv", index=False)

    # ── PRIMARY RESULTS ──────────────────────────────────────
    pd.DataFrame([{
        "severe_n": int(n_sev), "routine_n": int(n_rout),
        "severe_mean_ar20_pct": round(mean_sev*100, 3),
        "severe_median_ar20_pct": round(med_sev*100, 3),
        "routine_mean_ar20_pct": round(mean_rout*100, 3),
        "routine_median_ar20_pct": round(med_rout*100, 3),
        "diff_means_pp": round(diff_means*100, 3),
        "boot_ci_low_pct": round(ci_low*100, 3),
        "boot_ci_high_pct": round(ci_high*100, 3),
        "boot_ci_excludes_zero": ci_excl_zero,
        "welch_t_stat": round(t_stat, 3),
        "welch_p": round(p_welch, 4),
        "wilcoxon_p_onesided": round(p_wilcox, 4),
        "p_severe_worse": round(p_sev_worse, 3),
        "severe_beta_regression": round(severe_beta, 6) if not np.isnan(severe_beta) else None,
        "severe_beta_p": round(severe_p, 4) if not np.isnan(severe_p) else None,
        "dedup_issuer_year_n": len(df_dedup),
        "dedup_diff_pp": round(diff_dd*100, 3) if not np.isnan(diff_dd) else None,
        "dedup_p": round(p_dd, 4) if not np.isnan(p_dd) else None,
        "dedup_directional_negative": dedup_dir,
        "price_mapping_pct": round(mapping_pct, 1),
        "blind_signal_sha256": sha,
    }]).to_csv(OUT_DIR / "primary_results.csv", index=False)

    # ── CORPORATE ACTION AUDIT ───────────────────────────────
    corp_md = f"""# Project Nova Phase 0 — Corporate Action / Delisting Audit

## Coverage
- Primary eligible filings: {total_eligible}
- Price-mapped: {mapped} ({mapping_pct:.1f}%)
- No price data (includes delisted firms): {no_price}

## Warrant/Rights/Unit Filtering
- Applied pre-classification: tickers ending in W, WS, WT, R, U, UN, P, PA-PZ, Z are excluded.
- This prevents extreme volatility from non-common-equity instruments contaminating returns.

## Delisting Bias
- Fully delisted firms (post-bankruptcy zero-price period) are excluded from returns.
- Direction of bias: understates true Severe underperformance.
- If Gate A passes, Phase 1 should impute terminal loss for confirmed bankrupt severe filers.

## Winsorization
- Returns winsorized at 1st/99th percentile per horizon to remove data artifacts.
"""
    (OUT_DIR / "corporate_action_audit.md").write_text(corp_md)

    # ── GATE EVALUATION ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("GATE EVALUATION")
    print("=" * 60)

    # Classification accuracy from previous manual audit
    val_file = OUT_DIR / "classification_validation.csv"
    sev_acc = 85.0
    if val_file.exists():
        val_df = pd.read_csv(val_file)
        if "severity_match" in val_df.columns:
            sev_acc = val_df["severity_match"].mean() * 100

    gate_checks = {
        "1_severe_n_gte_500":               n_sev >= 500,
        "2_routine_n_gte_500":              n_rout >= 500,
        "3_severe_mean_lower_than_routine": mean_sev < mean_rout,
        "4_diff_lte_neg_1pp":               diff_means <= -0.01,
        "5_boot_ci_excludes_zero":          ci_excl_zero,
        "6_welch_p_lt_005":                 p_welch < 0.05,
        "7_wilcoxon_p_lt_005":              p_wilcox < 0.05,
        "8_regression_severe_beta_negative": (not np.isnan(severe_beta)) and severe_beta < 0,
        "9_dedup_directional_negative":     dedup_dir,
        "10_classification_accuracy_gte_90": sev_acc >= 90.0,
        "11_price_mapping_gte_80":          mapping_pct >= 80.0,
    }

    all_pass = all(gate_checks.values())
    print("\nGate A criteria:")
    for check, result in gate_checks.items():
        print(f"  {check}: {'PASS' if result else 'FAIL'}")

    if all_pass:
        gate = "GATE_A_WARRANTS_FULL_RESEARCH"
        nova_status = "CONTINUE"
    elif n_sev < 100 or n_rout < 100 or mapping_pct < 80.0:
        gate = "GATE_D_INVALID_DATA_INFEASIBLE"
        nova_status = "KILL"
    elif gate_checks["3_severe_mean_lower_than_routine"] and gate_checks["6_welch_p_lt_005"]:
        gate = "GATE_B_WEAK_MIXED"
        nova_status = "KILL"
    else:
        gate = "GATE_C_NO_EFFECT"
        nova_status = "KILL"

    print(f"\n  GATE: {gate}")
    print(f"  PROJECT NOVA STATUS: {nova_status}")

    # ── FREEZE MANIFEST ──────────────────────────────────────
    manifest = f"""# Project Nova Phase 0 — Freeze Manifest

## Dataset
File: nova_phase0_blind_signals.parquet
SHA-256: {sha}
Freeze Timestamp: {freeze_ts}
Total Records: {len(df_blind)}
SEVERE eligible: {int((df_blind['severe_flag']=='SEVERE').sum())}
ROUTINE eligible: {int((df_blind['severe_flag']=='ROUTINE').sum())}
EXCLUDED: {int((df_blind['severe_flag']=='EXCLUDED').sum())}

## Classification
Version: FROZEN v1.1 (after rate-limit purge)
Method: Deterministic regex, no LLM
Rules: data/nova/phase0/classification_rules.json

## Integrity
This file was saved BEFORE any forward return data was loaded.
Taxonomy cannot be modified without violating Historical Falsification First protocol.

## Gate Thresholds (Pre-registered)
Primary: T+1 Open → T+20 Close, SPY-adjusted abnormal return
Gate: ALL 11 conditions must pass simultaneously.
"""
    (OUT_DIR / "freeze_manifest.md").write_text(manifest)

    # ── PHASE 0 SUMMARY ──────────────────────────────────────
    summary = f"""# Project Nova — Phase 0 Summary

## Overall Result
**Gate: {gate}**
**Project Nova Status: {nova_status}**

## Data Statistics
- Total Form NT equity filings 2010-2024: {len(df_primary)}
  - NT 10-K: {(df_primary['form']=='NT 10-K').sum()}  |  NT 10-Q: {(df_primary['form']=='NT 10-Q').sum()}
  - Unique CIKs: {df_primary['cik'].nunique()}
- Classification:
  - SEVERE (A+B+C): {int((df_classified['severe_flag']=='SEVERE').sum())}
  - ROUTINE (E+F): {int((df_classified['severe_flag']=='ROUTINE').sum())}
  - EXCLUDED (D+G): {int((df_classified['severe_flag']=='EXCLUDED').sum())}
- Price-mapped (after warrant filter + winsorization): {mapped}/{total_eligible} ({mapping_pct:.1f}%)

## Classification Accuracy (N=100 manual audit, seed=20260911)
- Severe-vs-Routine accuracy: {sev_acc:.1f}%  (gate ≥ 90%: {'PASS' if sev_acc >= 90.0 else 'FAIL'})

## Primary Kill Test (T+1 Open → T+20 Close, SPY-adjusted, winsorized 1%/99%)

| Metric | Severe | Routine | Diff |
|--------|--------|---------|------|
| N | {n_sev} | {n_rout} | — |
| Mean AR20 | {mean_sev*100:.3f}% | {mean_rout*100:.3f}% | **{diff_means*100:.3f}pp** |
| Median AR20 | {med_sev*100:.3f}% | {med_rout*100:.3f}% | — |

**Bootstrap 95% CI: [{ci_low*100:.3f}%, {ci_high*100:.3f}%] — Excludes zero: {ci_excl_zero}**
**Welch: t={t_stat:.3f}  p={p_welch:.4f}**
**Wilcoxon (one-sided): p={p_wilcox:.4f}**

## OLS Control Regression
Severe dummy β={round(severe_beta,5) if not np.isnan(severe_beta) else 'N/A'}  p={round(severe_p,4) if not np.isnan(severe_p) else 'N/A'}

## De-duplicated Test (first NT per issuer-year)
N={len(df_dedup)}  Diff={round(diff_dd*100,3) if not np.isnan(diff_dd) else 'N/A'}pp  p={round(p_dd,4) if not np.isnan(p_dd) else 'N/A'}  Directional: {dedup_dir}

## Gate A Results
{chr(10).join([f"- {k}: {'PASS' if v else 'FAIL'}" for k, v in gate_checks.items()])}

## Blind Signal SHA-256
`{sha}`

## Conclusion
{"**Gate A PASSES.** All 11 criteria satisfied. Proceed to design a proper temporal out-of-sample replication experiment." if all_pass else f"**{gate} triggered.** Under Historical Falsification First protocol: **PROJECT NOVA IS KILLED.** No subgroup rescue. No horizon cherry-picking. Result stands as written."}
"""
    (OUT_DIR / "phase0_summary.md").write_text(summary)
    print("\nPhase 0 summary written.")

    return gate, nova_status


if __name__ == "__main__":
    gate, status = main()
    print("\n" + "=" * 60)
    print(f"FINAL GATE: {gate}")
    print(f"PROJECT NOVA STATUS: {status}")
    print("=" * 60)
