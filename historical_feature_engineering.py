"""Feature engineering and lookahead-proof reconstruction of historical factors."""
import datetime
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any

def get_trading_day_offset(df: pd.DataFrame, base_date: datetime.date, offset: int) -> datetime.date:
    """Get the trading date at a specific index offset from a base date in the DataFrame index.
    
    Positive offsets are forward in time, negative offsets are backward in time.
    """
    if df.empty:
        return None
    
    # Standardize base_date to Timestamp
    base_ts = pd.to_datetime(base_date).tz_localize(None)
    
    # Find matching or nearest preceding trading day index
    indices = df.index.get_indexer([base_ts], method='ffill')
    idx = indices[0]
    
    if idx < 0:
        return None
        
    target_idx = idx + offset
    if 0 <= target_idx < len(df):
        return df.index[target_idx].date()
        
    return None

def compute_historical_return_from_df(df: pd.DataFrame, start_date: datetime.date, end_date: datetime.date, close_col: str = 'Close') -> float:
    """Compute simple return (%) between two dates in prices DataFrame."""
    if df.empty or not start_date or not end_date:
        return None
    
    start_ts = pd.to_datetime(start_date).tz_localize(None)
    end_ts = pd.to_datetime(end_date).tz_localize(None)
    
    if start_ts not in df.index or end_ts not in df.index:
        return None
        
    p_start = df.loc[start_ts, close_col]
    p_end = df.loc[end_ts, close_col]
    
    if isinstance(p_start, pd.Series): p_start = p_start.iloc[0]
    if isinstance(p_end, pd.Series): p_end = p_end.iloc[0]
    
    if pd.notnull(p_start) and pd.notnull(p_end) and p_start > 0:
        return float((p_end - p_start) / p_start * 100.0)
    return None

def calculate_pre_event_technicals(df: pd.DataFrame, event_date: datetime.date) -> Dict[str, Any]:
    """Compute price and volume indicators known as of the day before the event (T-1)."""
    res = {
        'Price_T_minus_1': None,
        'RVOL': None,
        'RSI': 50.0,
        'SMA50': None,
        'SMA200': None,
        'ATR_Pct': 0.0,
        'Gap_Frequency': 0.0,
        'Volatility': 0.0,
        'Pre_5D_Return': None,
        'Pre_10D_Return': None,
        'Pre_30D_Return': None,
        'Pre_60D_Return': None,
        'Pre_90D_Return': None,
        'Dist_From_52W_High': None,
        'High_52W': None,
        'T_minus_1_Date': None
    }
    
    if df.empty:
        return res

    # Slice prices strictly before event_date
    event_ts = pd.to_datetime(event_date).tz_localize(None)
    df_pre = df[df.index < event_ts]
    
    if len(df_pre) < 20: # Need at least 20 trading days for basic metrics
        return res
        
    t_1_ts = df_pre.index[-1]
    res['T_minus_1_Date'] = t_1_ts.date()
    
    close_col = 'Close'
    if 'Close' not in df_pre.columns:
        if 'Adj Close' in df_pre.columns:
            close_col = 'Adj Close'
        else:
            return res

    closes = df_pre[close_col].dropna()
    volumes = df_pre['Volume'].dropna() if 'Volume' in df_pre.columns else pd.Series()
    
    if len(closes) < 2:
        return res
        
    current_price = float(closes.iloc[-1])
    res['Price_T_minus_1'] = current_price
    
    # 1. RVOL before event (using 20-day average volume up to T-1)
    if len(volumes) >= 20:
        avg_vol_20d = float(volumes.tail(20).mean())
        t_1_vol = float(volumes.iloc[-1])
        res['RVOL'] = float(t_1_vol / avg_vol_20d) if avg_vol_20d > 0 else 1.0
        
    # 2. RSI (14-period) before event
    if len(closes) >= 15:
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        if len(avg_gain) > 0 and len(avg_loss) > 0:
            last_gain = avg_gain.iloc[-1]
            last_loss = avg_loss.iloc[-1]
            rs = last_gain / (last_loss + 1e-9)
            res['RSI'] = float(100 - (100 / (1 + rs)))
            
    # 3. SMA50 / SMA200 before event
    if len(closes) >= 50:
        res['SMA50'] = float(closes.tail(50).mean())
    if len(closes) >= 200:
        res['SMA200'] = float(closes.tail(200).mean())
        
    # 4. ATR % (14-period) before event
    if len(closes) >= 14 and 'High' in df_pre.columns and 'Low' in df_pre.columns:
        highs = df_pre['High'].tail(15)
        lows = df_pre['Low'].tail(15)
        prev_closes = df_pre[close_col].shift(1).tail(15)
        trs = []
        for idx in range(1, len(highs)):
            h = highs.iloc[idx]
            l = lows.iloc[idx]
            pc = prev_closes.iloc[idx]
            if pd.notnull(pc):
                tr = max(h - l, abs(h - pc), abs(l - pc))
                trs.append(tr)
        if trs:
            atr = np.mean(trs)
            res['ATR_Pct'] = float(atr / current_price * 100) if current_price > 0 else 0.0
            
    # 5. Gap Frequency (%) over prior 250 trading days
    if len(closes) >= 2 and 'Open' in df_pre.columns:
        opens = df_pre['Open'].tail(250)
        prev_closes_250 = df_pre[close_col].shift(1).tail(250)
        gaps = []
        for idx in range(1, len(opens)):
            o = opens.iloc[idx]
            pc = prev_closes_250.iloc[idx]
            if pd.notnull(pc) and pc > 0:
                gaps.append(abs(o - pc) / pc >= 0.015)
        if gaps:
            res['Gap_Frequency'] = float(np.mean(gaps) * 100)
            
    # 6. Volatility (30D daily return standard deviation * sqrt(252) for annualized)
    if len(closes) >= 30:
        rets = closes.tail(30).pct_change().dropna()
        res['Volatility'] = float(rets.std() * np.sqrt(252) * 100)

    # 7. Pre-earnings returns
    t_1_date = t_1_ts.date()
    d_5 = get_trading_day_offset(df, t_1_date, -5)
    d_10 = get_trading_day_offset(df, t_1_date, -10)
    d_30 = get_trading_day_offset(df, t_1_date, -30)
    d_60 = get_trading_day_offset(df, t_1_date, -60)
    d_90 = get_trading_day_offset(df, t_1_date, -90)
    
    res['Pre_5D_Return'] = compute_historical_return_from_df(df, d_5, t_1_date, close_col)
    res['Pre_10D_Return'] = compute_historical_return_from_df(df, d_10, t_1_date, close_col)
    res['Pre_30D_Return'] = compute_historical_return_from_df(df, d_30, t_1_date, close_col)
    res['Pre_60D_Return'] = compute_historical_return_from_df(df, d_60, t_1_date, close_col)
    res['Pre_90D_Return'] = compute_historical_return_from_df(df, d_90, t_1_date, close_col)
    
    # 8. Distance from 52-week High before event (using prior 250 trading days)
    high_col = 'High' if 'High' in df_pre.columns else close_col
    high_52w = float(df_pre[high_col].tail(250).max()) if not df_pre.empty else None
    if high_52w and high_52w > 0:
        res['High_52W'] = high_52w
        res['Dist_From_52W_High'] = float((high_52w - current_price) / high_52w)
        
    return res

def calculate_post_event_outcomes(df: pd.DataFrame, event_date: datetime.date) -> Dict[str, Any]:
    """Compute actual earnings reaction outcomes (returns and moves) in the days following the event."""
    res = {
        'Price_Close_Event_Day': None,
        'Price_Close_Plus_1': None,
        'Price_Close_Plus_3': None,
        'Price_Close_Plus_5': None,
        'Post_1D_Return': None,
        'Post_3D_Return': None,
        'Post_5D_Return': None,
        'Max_Favorable_Move': 0.0,
        'Max_Adverse_Move': 0.0,
        'Absolute_1D_Move': None,
        'Gap_Percent': None,
        'Volume_Spike_Day_0': None,
        'Volume_Spike_Day_1': None
    }
    
    if df.empty:
        return res
        
    # Standardize event_date
    event_ts = pd.to_datetime(event_date).tz_localize(None)
    
    # Find matching or nearest preceding day before the event
    df_pre = df[df.index < event_ts]
    if df_pre.empty:
        return res
    t_1_ts = df_pre.index[-1]
    t_1_date = t_1_ts.date()
    
    close_col = 'Close' if 'Close' in df.columns else ('Adj Close' if 'Adj Close' in df.columns else None)
    if not close_col:
        return res

    # Retrieve post-event window: from T to T+10
    df_post = df[df.index >= event_ts].head(10)
    if df_post.empty:
        return res
        
    # Event day (T) is the first day in df_post
    t_ts = df_post.index[0]
    res['Price_Close_Event_Day'] = float(df_post.loc[t_ts, close_col])
    
    # T+1, T+3, T+5 dates
    t_plus_1 = get_trading_day_offset(df, t_1_date, 2) # Offset +2 from T-1 is T+1 (since T is +1)
    t_plus_3 = get_trading_day_offset(df, t_1_date, 4) # Offset +4 is T+3
    t_plus_5 = get_trading_day_offset(df, t_1_date, 6) # Offset +6 is T+5
    
    p_t_1 = float(df.loc[t_1_ts, close_col])
    
    if t_plus_1 and pd.to_datetime(t_plus_1) in df.index:
        p_1 = float(df.loc[pd.to_datetime(t_plus_1), close_col])
        res['Price_Close_Plus_1'] = p_1
        res['Post_1D_Return'] = float((p_1 - p_t_1) / p_t_1 * 100)
        res['Absolute_1D_Move'] = abs(res['Post_1D_Return'])
        
    if t_plus_3 and pd.to_datetime(t_plus_3) in df.index:
        p_3 = float(df.loc[pd.to_datetime(t_plus_3), close_col])
        res['Price_Close_Plus_3'] = p_3
        res['Post_3D_Return'] = float((p_3 - p_t_1) / p_t_1 * 100)
        
    if t_plus_5 and pd.to_datetime(t_plus_5) in df.index:
        p_5 = float(df.loc[pd.to_datetime(t_plus_5), close_col])
        res['Price_Close_Plus_5'] = p_5
        res['Post_5D_Return'] = float((p_5 - p_t_1) / p_t_1 * 100)
        
    # Gap Percent on Event Day
    if 'Open' in df_post.columns:
        o_t = float(df_post.loc[t_ts, 'Open'])
        res['Gap_Percent'] = float((o_t - p_t_1) / p_t_1 * 100)
        
    # Max Favorable / Adverse Move in [T, T+5] window
    df_window = df_post.head(6) # Event Day (T) + 5 days
    if not df_window.empty and 'High' in df_window.columns and 'Low' in df_window.columns:
        highs = df_window['High'].dropna()
        lows = df_window['Low'].dropna()
        if not highs.empty and not lows.empty:
            max_high = float(highs.max())
            min_low = float(lows.min())
            
            favorable_move_up = (max_high - p_t_1) / p_t_1 * 100
            adverse_move_up = (min_low - p_t_1) / p_t_1 * 100
            
            favorable_move_down = (p_t_1 - min_low) / p_t_1 * 100
            adverse_move_down = (p_t_1 - max_high) / p_t_1 * 100
            
            # Since we look at it directionally:
            # Let's define Max Favorable Move as the peak percentage move in the direction of the 1D return,
            # or simply record both upward-biased moves or absolute maximums.
            # To be simple and robust:
            # Max Favorable Move = max(favorable_move_up, 0)
            # Max Adverse Move = min(adverse_move_up, 0)
            # Let's check 1D return direction:
            r1 = res['Post_1D_Return']
            if r1 is not None and r1 >= 0:
                res['Max_Favorable_Move'] = favorable_move_up
                res['Max_Adverse_Move'] = adverse_move_up
            elif r1 is not None and r1 < 0:
                res['Max_Favorable_Move'] = favorable_move_down
                res['Max_Adverse_Move'] = adverse_move_down
            else:
                res['Max_Favorable_Move'] = max(favorable_move_up, 0.0)
                res['Max_Adverse_Move'] = min(adverse_move_up, 0.0)

    # Volume Spike on Event Day (T) and T+1
    if 'Volume' in df.columns:
        volumes_pre = df_pre['Volume'].dropna()
        if len(volumes_pre) >= 20:
            avg_vol_20d = float(volumes_pre.tail(20).mean())
            if avg_vol_20d > 0:
                vol_t = float(df_post.loc[t_ts, 'Volume'])
                res['Volume_Spike_Day_0'] = float(vol_t / avg_vol_20d)
                if len(df_post) > 1:
                    vol_t1 = float(df_post.iloc[1]['Volume'])
                    res['Volume_Spike_Day_1'] = float(vol_t1 / avg_vol_20d)
                    
    return res

def parse_quarterly_sec_concept(facts_json: dict, concept: str, event_date: datetime.date) -> Dict[Tuple[int, str], float]:
    """Extract quarterly values for a concept from SEC companyfacts JSON.
    
    Groups facts filed before event_date by fiscal year/period, selects the latest filing,
    and de-accumulates YTD figures into true quarterly values.
    
    Returns a dictionary of {(fy, fp): value}
    """
    if not facts_json or 'facts' not in facts_json:
        return {}
        
    concepts = facts_json['facts'].get('us-gaap', {})
    if concept not in concepts:
        # Try dei namespace
        concepts = facts_json['facts'].get('dei', {})
        if concept not in concepts:
            return {}
            
    units = concepts[concept].get('units', {})
    raw_entries = []
    for unit_list in units.values():
        raw_entries.extend(unit_list)
        
    if not raw_entries:
        return {}
        
    # Standardize event_date string for comparison
    event_str = event_date.strftime("%Y-%m-%d")
    
    # 1. Filter to facts filed BEFORE event_date
    valid_entries = []
    for entry in raw_entries:
        filed = entry.get('filed')
        fy = entry.get('fy')
        fp = entry.get('fp')
        val = entry.get('val')
        if filed and filed < event_str and fy is not None and fp and val is not None:
            # Filter standard fiscal quarters/periods (ignore Q1YTD, Q2YTD, etc. if not needed)
            if fp in ['Q1', 'Q2', 'Q3', 'FY', 'Q4']:
                valid_entries.append(entry)
                
    if not valid_entries:
        return {}
        
    # 2. Group by (fy, fp) and select the latest filed entry
    latest_by_period = {}
    for entry in valid_entries:
        fy = int(entry['fy'])
        fp = str(entry['fp'])
        filed = str(entry['filed'])
        key = (fy, fp)
        
        if key not in latest_by_period:
            latest_by_period[key] = entry
        else:
            # Keep the one filed latest, or if filed same day, the one with more details
            existing_filed = latest_by_period[key]['filed']
            if filed > existing_filed:
                latest_by_period[key] = entry
                
    # 3. Separate flow variables and check for YTD vs quarterly
    # Flow variables have a 'start' and 'end'.
    # If the interval is around 3 months, it is quarterly. If more, it's YTD.
    # Standard YTD de-accumulation:
    # Q1 quarterly = Q1 YTD
    # Q2 quarterly = Q2 YTD - Q1 YTD
    # Q3 quarterly = Q3 YTD - Q2 YTD
    # Q4/FY quarterly = FY YTD - Q3 YTD
    #
    # Let's map YTD values for each year
    ytd_vals = {} # fy -> fp -> val
    for (fy, fp), entry in latest_by_period.items():
        val = float(entry['val'])
        start = entry.get('start')
        end = entry.get('end')
        
        # Check duration
        is_quarterly = False
        if start and end:
            try:
                dt_start = datetime.datetime.strptime(start, "%Y-%m-%d")
                dt_end = datetime.datetime.strptime(end, "%Y-%m-%d")
                days = (dt_end - dt_start).days
                if days <= 105: # approx 3 months
                    is_quarterly = True
            except Exception:
                pass
                
        # If it is point-in-time (Balance Sheet like Assets/Cash), start is None, and it's already point-in-time
        if not start:
            is_quarterly = True
            
        ytd_vals.setdefault(fy, {})[fp] = (val, is_quarterly)
        
    # 4. De-accumulate
    quarterly_vals = {}
    for fy, periods in ytd_vals.items():
        # Get YTD values if available
        q1_ytd, q1_is_q = periods.get('Q1', (None, False))
        q2_ytd, q2_is_q = periods.get('Q2', (None, False))
        q3_ytd, q3_is_q = periods.get('Q3', (None, False))
        fy_ytd, fy_is_q = periods.get('FY', periods.get('Q4', (None, False)))
        
        # Q1
        if q1_ytd is not None:
            quarterly_vals[(fy, 'Q1')] = q1_ytd
            
        # Q2
        if q2_ytd is not None:
            if q2_is_q:
                quarterly_vals[(fy, 'Q2')] = q2_ytd
            else:
                # Need to de-accumulate
                if q1_ytd is not None:
                    quarterly_vals[(fy, 'Q2')] = q2_ytd - q1_ytd
                else:
                    quarterly_vals[(fy, 'Q2')] = q2_ytd / 2.0 # Approximation fallback
                    
        # Q3
        if q3_ytd is not None:
            if q3_is_q:
                quarterly_vals[(fy, 'Q3')] = q3_ytd
            else:
                # Need to de-accumulate
                if q2_ytd is not None:
                    quarterly_vals[(fy, 'Q3')] = q3_ytd - q2_ytd
                elif q1_ytd is not None:
                    quarterly_vals[(fy, 'Q3')] = q3_ytd - q1_ytd # Approximation fallback
                else:
                    quarterly_vals[(fy, 'Q3')] = q3_ytd / 3.0 # Approximation fallback
                    
        # Q4 / FY
        if fy_ytd is not None:
            if fy_is_q:
                quarterly_vals[(fy, 'Q4')] = fy_ytd
            else:
                # Need to de-accumulate
                if q3_ytd is not None:
                    quarterly_vals[(fy, 'Q4')] = fy_ytd - q3_ytd
                else:
                    quarterly_vals[(fy, 'Q4')] = fy_ytd / 4.0 # Approximation fallback
                    
    return quarterly_vals

def reconstruct_point_in_time_fundamentals(facts_json: dict, event_date: datetime.date) -> Dict[str, Any]:
    """Reconstruct quarterly financials and TTM values filed before event_date.
    
    Avoids lookahead bias using only SEC filed dates < event_date.
    """
    res = {
        'Latest_Quarterly_FCF': None,
        'Prior_Quarterly_FCF': None,
        'TTM_FCF': None,
        'Quarterly_FCF_History': [],
        'Revenue_Trend': 'Unknown',
        'Gross_Margin_Trend': 'Unknown',
        'Net_Income_Trend': 'Unknown',
        'Latest_Cash': None,
        'Latest_Debt': None,
        'SEC_Data_Quality': 'Low',
        'Filing_Proxy_Used': False
    }
    
    if not facts_json or 'facts' not in facts_json or 'error' in facts_json:
        return res

    # 1. Extract Cash Flow concepts
    # FCF = Operating Cash Flow - Capital Expenditures
    ocf_dict = parse_quarterly_sec_concept(facts_json, 'NetCashProvidedByUsedInOperatingActivities', event_date)
    
    # Try different Capex concepts
    capex_dict = parse_quarterly_sec_concept(facts_json, 'PaymentsToAcquirePropertyPlantAndEquipment', event_date)
    if not capex_dict:
        capex_dict = parse_quarterly_sec_concept(facts_json, 'CapitalExpenditures', event_date)
        
    # Compile quarterly FCF
    all_periods = sorted(list(set(ocf_dict.keys())))
    q_fcf = {}
    for key in all_periods:
        ocf = ocf_dict[key]
        capex = capex_dict.get(key, 0.0) # Assume 0 if Capex details missing
        # SEC Capex is usually reported as positive outflows or negative.
        # Check standard convention (usually positive in Cash Flows section under PaymentsToAcquire...)
        # We subtract Capex from OCF to get FCF
        q_fcf[key] = ocf - abs(capex)
        
    # Sort chronologically
    sorted_fcf_periods = sorted(list(q_fcf.keys()), key=lambda x: (x[0], x[1]))
    fcf_history = [q_fcf[p] for p in sorted_fcf_periods]
    res['Quarterly_FCF_History'] = fcf_history
    
    if len(fcf_history) >= 1:
        res['Latest_Quarterly_FCF'] = fcf_history[-1]
        res['SEC_Data_Quality'] = 'Medium'
    if len(fcf_history) >= 2:
        res['Prior_Quarterly_FCF'] = fcf_history[-2]
        
    # TTM FCF (sum of last 4 quarters)
    if len(fcf_history) >= 4:
        res['TTM_FCF'] = sum(fcf_history[-4:])
        res['SEC_Data_Quality'] = 'High'
    elif len(fcf_history) > 0:
        # Annualized proxy if less than 4 quarters
        res['TTM_FCF'] = sum(fcf_history) * (4.0 / len(fcf_history))

    # 2. Revenue Trend
    rev_dict = parse_quarterly_sec_concept(facts_json, 'Revenues', event_date)
    if not rev_dict:
        rev_dict = parse_quarterly_sec_concept(facts_json, 'RevenueFromContractWithCustomerExcludingAssessedTax', event_date)
    if not rev_dict:
        rev_dict = parse_quarterly_sec_concept(facts_json, 'SalesRevenueNet', event_date)
        
    if rev_dict:
        sorted_rev_periods = sorted(list(rev_dict.keys()), key=lambda x: (x[0], x[1]))
        if len(sorted_rev_periods) >= 2:
            r_latest = rev_dict[sorted_rev_periods[-1]]
            r_prior = rev_dict[sorted_rev_periods[-2]]
            if r_latest > r_prior:
                res['Revenue_Trend'] = 'Improving'
            elif r_latest < r_prior:
                res['Revenue_Trend'] = 'Declining'
            else:
                res['Revenue_Trend'] = 'Stable'

    # 3. Net Income Trend
    ni_dict = parse_quarterly_sec_concept(facts_json, 'NetIncomeLoss', event_date)
    if ni_dict:
        sorted_ni_periods = sorted(list(ni_dict.keys()), key=lambda x: (x[0], x[1]))
        if len(sorted_ni_periods) >= 2:
            ni_latest = ni_dict[sorted_ni_periods[-1]]
            ni_prior = ni_dict[sorted_ni_periods[-2]]
            if ni_latest > ni_prior:
                res['Net_Income_Trend'] = 'Improving'
            elif ni_latest < ni_prior:
                res['Net_Income_Trend'] = 'Declining'
            else:
                res['Net_Income_Trend'] = 'Stable'

    # 4. Gross Margin Trend
    gp_dict = parse_quarterly_sec_concept(facts_json, 'GrossProfit', event_date)
    if rev_dict and gp_dict:
        sorted_gp_periods = sorted(list(gp_dict.keys()), key=lambda x: (x[0], x[1]))
        # Match periods
        common_periods = sorted(list(set(rev_dict.keys()) & set(gp_dict.keys())), key=lambda x: (x[0], x[1]))
        if len(common_periods) >= 2:
            gm_latest = gp_dict[common_periods[-1]] / (rev_dict[common_periods[-1]] + 1e-9)
            gm_prior = gp_dict[common_periods[-2]] / (rev_dict[common_periods[-2]] + 1e-9)
            if gm_latest > gm_prior + 0.005:
                res['Gross_Margin_Trend'] = 'Improving'
            elif gm_latest < gm_prior - 0.005:
                res['Gross_Margin_Trend'] = 'Declining'
            else:
                res['Gross_Margin_Trend'] = 'Stable'

    # 5. Balance Sheet - Cash and Debt (Point in time)
    # Cash
    cash_dict = parse_quarterly_sec_concept(facts_json, 'CashAndCashEquivalentsAtCarryingValue', event_date)
    if cash_dict:
        sorted_cash_periods = sorted(list(cash_dict.keys()), key=lambda x: (x[0], x[1]))
        res['Latest_Cash'] = cash_dict[sorted_cash_periods[-1]]
        
    # Debt (Current + Non-current)
    lt_debt = parse_quarterly_sec_concept(facts_json, 'LongTermDebtNoncurrent', event_date)
    st_debt = parse_quarterly_sec_concept(facts_json, 'LongTermDebtCurrent', event_date)
    if not st_debt:
        st_debt = parse_quarterly_sec_concept(facts_json, 'ShortTermBorrowings', event_date)
        
    # Calculate latest debt
    all_debt_periods = sorted(list(set(lt_debt.keys()) | set(st_debt.keys())), key=lambda x: (x[0], x[1]))
    if all_debt_periods:
        latest_d_period = all_debt_periods[-1]
        d_val = lt_debt.get(latest_d_period, 0.0) + st_debt.get(latest_d_period, 0.0)
        res['Latest_Debt'] = d_val
    else:
        # Fallback to general LongTermDebt
        lt_debt_gen = parse_quarterly_sec_concept(facts_json, 'LongTermDebt', event_date)
        if lt_debt_gen:
            sorted_lt_gen = sorted(list(lt_debt_gen.keys()), key=lambda x: (x[0], x[1]))
            res['Latest_Debt'] = lt_debt_gen[sorted_lt_gen[-1]]

    return res

def reconstruct_historical_earnings_reactions(earnings_dates: List[datetime.date], df_prices: pd.DataFrame, event_date: datetime.date) -> Dict[str, Any]:
    """Analyze historical reaction sizes only using events BEFORE the current event date."""
    res = {
        'Historical_Avg_Earnings_Reaction': 0.0,
        'Prior_4_Earnings_Move_Avg': None,
        'Prior_8_Earnings_Move_Avg': None
    }
    
    if df_prices.empty or not earnings_dates:
        return res
        
    # Filter earnings dates strictly before current event_date
    past_dates = sorted([d for d in earnings_dates if d < event_date], reverse=True)
    if not past_dates:
        return res
        
    reactions = []
    
    # Standardize prices index
    df_prices_dates = list(df_prices.index.date)
    close_col = 'Close' if 'Close' in df_prices.columns else ('Adj Close' if 'Adj Close' in df_prices.columns else None)
    if not close_col:
        return res
        
    for ed_date in past_dates:
        # Check if ed_date is in prices index (or nearest day)
        if ed_date in df_prices_dates:
            idx = df_prices_dates.index(ed_date)
            # Make sure we have prior and post price to calculate reaction
            if 0 < idx < len(df_prices) - 1:
                p_prev = float(df_prices[close_col].iloc[idx - 1])
                p_day = float(df_prices[close_col].iloc[idx])
                p_next = float(df_prices[close_col].iloc[idx + 1])
                
                if p_prev > 0 and p_day > 0:
                    day_ret = abs((p_day - p_prev) / p_prev * 100)
                    next_ret = abs((p_next - p_day) / p_day * 100)
                    # Use the maximum of event day and next day reaction (same as screener.py)
                    reactions.append(max(day_ret, next_ret))
                    
    if reactions:
        res['Historical_Avg_Earnings_Reaction'] = float(np.mean(reactions))
        
        # Prior 4 move average
        if len(reactions) >= 4:
            res['Prior_4_Earnings_Move_Avg'] = float(np.mean(reactions[:4]))
        else:
            res['Prior_4_Earnings_Move_Avg'] = float(np.mean(reactions)) # Use what's available
            
        # Prior 8 move average
        if len(reactions) >= 8:
            res['Prior_8_Earnings_Move_Avg'] = float(np.mean(reactions[:8]))
        else:
            res['Prior_8_Earnings_Move_Avg'] = float(np.mean(reactions)) # Use what's available
            
    return res

def get_shares_outstanding_on_date(facts_json: dict, run_date: datetime.date) -> float:
    """Extract common stock shares outstanding as of run_date from SEC facts."""
    if not facts_json or 'facts' not in facts_json or 'error' in facts_json:
        return None
    try:
        concepts = facts_json['facts'].get('dei', {})
        if 'EntityCommonStockSharesOutstanding' in concepts:
            units = concepts['EntityCommonStockSharesOutstanding'].get('units', {})
            raw_entries = []
            for unit_list in units.values():
                raw_entries.extend(unit_list)
            
            run_str = run_date.strftime("%Y-%m-%d")
            valid = [e for e in raw_entries if e.get('filed') and e.get('filed') < run_str and e.get('val') is not None]
            if valid:
                valid.sort(key=lambda x: (x.get('filed'), x.get('end', '')), reverse=True)
                return float(valid[0]['val'])
    except Exception:
        pass
    return None
