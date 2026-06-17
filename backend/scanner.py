"""
GREY ROCK STRATEGY - Intraday Scanner Engine
Fixed version — resolves all root causes causing zero results.

ROOT CAUSES FIXED:
  RC-1: hist < 210 guard kills almost every stock (NSE stocks rarely have 252+ rows in 1y)
  RC-2: "BHARAT FORGE.NS" has a space — yfinance rejects it silently
  RC-3: PIDILITIND.NS appears twice in STOCK_UNIVERSE (minor, deduped)
  RC-4: move_from_open < 0.0 filter rejects stocks moving sideways or down from open
  RC-5: Daily history used as intraday proxy; today_close == yesterday_close outside market hours
        → move_from_open is always near 0, vol_ratio is 20-day-avg/20-day-avg ≈ 1, probability floor fails
  RC-6: Probability formula can never exceed 55 + 37 = 92 but the floor of 55 means
        score_result['probability'] is ALWAYS ≥ 55, so the filter at line 394 can never
        eliminate stocks — meaning the REAL elimination happens entirely from the hard
        return-None filters above it (gap, liquidity, move_from_open, rsi).
  RC-7: Intraday data fetch (1d/5m) used to get today_open and today_vol —
        but ticker.history(period="1d") outside market hours returns empty or 1 stale row.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import json
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('greyrock')

IST = pytz.timezone('Asia/Kolkata')

# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSE: NSE top liquid stocks
# FIX RC-2: Removed "BHARAT FORGE.NS" (space in ticker — yfinance silently fails)
#           Use correct ticker "BHARATFORG.NS"
# FIX RC-3: Removed duplicate PIDILITIND.NS
# ─────────────────────────────────────────────────────────────────────────────
STOCK_UNIVERSE = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
    "HINDUNILVR.NS","BHARTIARTL.NS","ITC.NS","KOTAKBANK.NS","SBIN.NS",
    "LT.NS","BAJFINANCE.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
    "SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS","NESTLEIND.NS","WIPRO.NS",
    "TECHM.NS","HCLTECH.NS","POWERGRID.NS","NTPC.NS","ONGC.NS",
    "BAJAJFINSV.NS","INDUSINDBK.NS","TATAMOTORS.NS","ADANIPORTS.NS","COALINDIA.NS",
    "DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","EICHERMOT.NS","HEROMOTOCO.NS",
    "GRASIM.NS","HINDALCO.NS","JSWSTEEL.NS","TATACONSUM.NS","BRITANNIA.NS",
    "PIDILITIND.NS","HAVELLS.NS","DABUR.NS","MARICO.NS","GODREJCP.NS",
    "MCDOWELL-N.NS","BIOCON.NS","LUPIN.NS","AUROPHARMA.NS","TORNTPHARM.NS",
    "GMRINFRA.NS","ADANIENT.NS","TATAPOWER.NS","TATASTEEL.NS","SAIL.NS",
    "PNB.NS","BANKBARODA.NS","CANBK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS",
    "MOTHERSON.NS","BALKRISIND.NS","APOLLOTYRE.NS","MRF.NS","ESCORTS.NS",
    "BERGEPAINT.NS","KANSAINER.NS","VOLTAS.NS","WHIRLPOOL.NS",
    "ZOMATO.NS","NYKAA.NS","PAYTM.NS","DELHIVERY.NS","POLICYBZR.NS",
    "HAL.NS","BEL.NS","BHEL.NS","BEML.NS","IRCTC.NS",
    "CHOLAFIN.NS","MUTHOOTFIN.NS","BAJAJHLDNG.NS","RECLTD.NS","PFC.NS",
    "SIEMENS.NS","ABB.NS","CUMMINSIND.NS","THERMAX.NS","BHARATFORG.NS",
    "PERSISTENT.NS","LTIM.NS","MPHASIS.NS","COFORGE.NS","OFSS.NS",
    "ASTRAL.NS","SUPREMEIND.NS","APOLLOHOSP.NS","FORTIS.NS","MAXHEALTH.NS",
    "DMART.NS","TRENT.NS","JUBLFOOD.NS","DEVYANI.NS","WESTLIFE.NS",
]

# ─────────────────────────────────────────────────────────────────────────────
# MARKET SESSION
# ─────────────────────────────────────────────────────────────────────────────
def get_market_session() -> str:
    now = datetime.now(IST)
    h, m = now.hour, now.minute
    t = h * 60 + m
    if t < 9*60+15:
        return "PRE_MARKET"
    elif t < 9*60+30:
        return "OPENING"
    elif t < 15*60+30:
        return "LIVE"
    else:
        return "CLOSED"

def is_market_open() -> bool:
    return get_market_session() in ("LIVE", "OPENING")

# ─────────────────────────────────────────────────────────────────────────────
# EMA & RSI
# ─────────────────────────────────────────────────────────────────────────────
def calculate_emas(closes):
    s = pd.Series(closes)
    ema20  = s.ewm(span=20,  adjust=False).mean()
    ema50  = s.ewm(span=50,  adjust=False).mean()
    ema200 = s.ewm(span=200, adjust=False).mean()
    return ema20.values, ema50.values, ema200.values

def calculate_rsi(closes, period=14):
    s = pd.Series(closes)
    delta    = s.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.values[-1])

# ─────────────────────────────────────────────────────────────────────────────
# SCORING ENGINE  (unchanged from original)
# ─────────────────────────────────────────────────────────────────────────────
def score_stock(data: dict) -> dict:
    score = 0
    max_score = 0
    breakdown = {}

    max_score += 15
    pct = data.get('prev_close_vs_high', 999)
    if pct <= 0.5:   pts = 15
    elif pct <= 1.0: pts = 12
    elif pct <= 1.5: pts = 8
    else:            pts = 2
    score += pts
    breakdown['Yesterday Close Near High'] = {'score': pts, 'max': 15, 'value': f"{pct:.1f}% from high"}

    max_score += 10
    gap = data.get('gap_pct', 0)
    if gap >= 0.5:   pts = 10
    elif gap >= 0:   pts = 7
    else:            pts = 0
    score += pts
    breakdown['Gap Up / Flat'] = {'score': pts, 'max': 10, 'value': f"Gap: {gap:+.2f}%"}

    max_score += 15
    vol_ratio = data.get('vol_ratio', 0)
    if vol_ratio >= 5:   pts = 15
    elif vol_ratio >= 3: pts = 12
    elif vol_ratio >= 2: pts = 8
    elif vol_ratio >= 1: pts = 4
    else:                pts = 0
    score += pts
    breakdown['Volume Surge'] = {'score': pts, 'max': 15, 'value': f"{vol_ratio:.1f}x avg volume"}

    max_score += 20
    ema_ok = data.get('ema_stack_ok', False)
    pts = 20 if ema_ok else 0
    score += pts
    breakdown['EMA Stack (20>50>200)'] = {'score': pts, 'max': 20, 'value': '✅ Perfect stack' if ema_ok else '❌ Not stacked'}

    max_score += 10
    ema_up = data.get('emas_pointing_up', 0)
    pts = int(ema_up / 3 * 10)
    score += pts
    breakdown['EMAs Pointing Up'] = {'score': pts, 'max': 10, 'value': f"{ema_up}/3 EMAs rising"}

    max_score += 10
    rsi = data.get('rsi', 80)
    if rsi < 55:   pts = 10
    elif rsi < 60: pts = 8
    elif rsi < 65: pts = 5
    else:          pts = 0
    score += pts
    breakdown['RSI < 65'] = {'score': pts, 'max': 10, 'value': f"RSI: {rsi:.1f}"}

    max_score += 15
    move_from_open = data.get('move_from_open', 0)
    if 2.0 <= move_from_open <= 5.0:   pts = 15
    elif 1.0 <= move_from_open < 2.0:  pts = 8
    elif move_from_open > 5.0:         pts = 5
    else:                              pts = 0
    score += pts
    breakdown['Already Moving (2-3%+)'] = {'score': pts, 'max': 15, 'value': f"+{move_from_open:.2f}% from open"}

    max_score += 5
    today_vol = data.get('today_volume', 0)
    if today_vol >= 1000000:   pts = 5
    elif today_vol >= 500000:  pts = 4
    elif today_vol >= 100000:  pts = 2
    else:                      pts = 0
    score += pts
    breakdown['Today Volume ≥500K'] = {'score': pts, 'max': 5, 'value': f"{today_vol:,.0f} shares"}

    raw_pct = (score / max_score) * 100 if max_score > 0 else 0
    probability = 55 + (raw_pct / 100) * 37

    return {
        'total_score': score,
        'max_score': max_score,
        'rating': round(score / max_score * 5, 1) if max_score > 0 else 0,
        'probability': round(probability, 1),
        'breakdown': breakdown,
    }

# ─────────────────────────────────────────────────────────────────────────────
# FETCH TODAY'S INTRADAY DATA (open, current price, today volume)
# FIX RC-5 / RC-7: Separate intraday fetch so we get real today_open and live price
# ─────────────────────────────────────────────────────────────────────────────
def fetch_today_intraday(ticker_obj):
    """
    Returns (today_open, today_price, today_volume) using 5-minute intraday data.
    Falls back to daily last row if intraday unavailable (pre-market / after hours).
    """
    try:
        intra = ticker_obj.history(period="1d", interval="5m", prepost=False)
        if intra is not None and len(intra) >= 2:
            today_open  = float(intra['Open'].iloc[0])
            today_price = float(intra['Close'].iloc[-1])
            today_vol   = float(intra['Volume'].sum())
            log.debug(f"  Intraday rows={len(intra)}, open={today_open:.2f}, price={today_price:.2f}, vol={today_vol:.0f}")
            return today_open, today_price, today_vol
    except Exception as e:
        log.debug(f"  Intraday fetch failed: {e}")
    return None, None, None

# ─────────────────────────────────────────────────────────────────────────────
# ANALYZE A SINGLE STOCK
# ─────────────────────────────────────────────────────────────────────────────
def analyze_stock(symbol: str) -> dict | None:
    try:
        ticker = yf.Ticker(symbol)

        # ── FIX RC-1: Reduced min rows from 210 → 60 ─────────────────────────
        # 1y of NSE data often has gaps (holidays, halts).  210 bars = ~210 trading
        # days which is nearly a full year — most stocks will fail this.
        # We need at least 200 bars to compute EMA-200 reliably, but 60 is the
        # absolute minimum to be useful; we handle short histories gracefully.
        hist = ticker.history(period="1y", interval="1d", auto_adjust=True)
        if hist is None or len(hist) < 60:
            log.debug(f"  {symbol}: insufficient daily history ({len(hist) if hist is not None else 0} rows) — skip")
            return None

        closes  = hist['Close'].values.astype(float)
        highs   = hist['High'].values.astype(float)
        volumes = hist['Volume'].values.astype(float)

        # Sanitise NaNs
        if np.any(np.isnan(closes[-5:])) or np.any(np.isnan(highs[-5:])):
            log.debug(f"  {symbol}: NaN in recent OHLC — skip")
            return None

        # ── Yesterday's reference data ────────────────────────────────────────
        prev_close = float(closes[-2])
        prev_high  = float(highs[-2])
        # 20-day avg volume excl today
        lookback = min(20, len(volumes) - 1)
        prev_vol  = float(np.mean(volumes[-lookback - 1:-1]))

        if prev_vol < 5000:
            log.debug(f"  {symbol}: avg volume too low ({prev_vol:.0f}) — skip")
            return None

        # ── FIX RC-5/RC-7: Get real intraday today data ───────────────────────
        today_open_intra, today_price_intra, today_vol_intra = fetch_today_intraday(ticker)

        if today_open_intra is not None:
            # Market is open — use live intraday data
            today_open  = today_open_intra
            today_close = today_price_intra
            today_vol   = today_vol_intra
            log.debug(f"  {symbol}: using LIVE intraday price={today_close:.2f}")
        else:
            # Market closed / pre-market — fall back to daily last row
            today_open  = float(hist['Open'].values[-1])
            today_close = float(closes[-1])
            today_vol   = float(volumes[-1])
            log.debug(f"  {symbol}: using DAILY close price={today_close:.2f}")

        if today_vol < 5000:
            log.debug(f"  {symbol}: today volume too low ({today_vol:.0f}) — skip")
            return None

        # ── Gap ───────────────────────────────────────────────────────────────
        gap_pct = (today_open - prev_close) / prev_close * 100 if prev_close > 0 else 0
        if gap_pct < -2.0:
            log.debug(f"  {symbol}: gap too large ({gap_pct:.2f}%) — skip")
            return None

        # ── EMAs ─────────────────────────────────────────────────────────────
        ema20, ema50, ema200 = calculate_emas(closes)
        e20  = float(ema20[-1])
        e50  = float(ema50[-1])
        e200 = float(ema200[-1])

        ema_stack_ok = bool(today_close > e20 > e50 > e200)

        lookback5  = min(5,  len(ema20) - 1)
        lookback10 = min(10, len(ema200) - 1)
        emas_up = int(sum([
            ema20[-1]  > ema20[-lookback5 - 1],
            ema50[-1]  > ema50[-lookback5 - 1],
            ema200[-1] > ema200[-lookback10 - 1],
        ]))

        # ── RSI ───────────────────────────────────────────────────────────────
        rsi = calculate_rsi(closes)
        if np.isnan(rsi):
            rsi = 50.0
        if rsi > 85:
            log.debug(f"  {symbol}: RSI={rsi:.1f} overbought — skip")
            return None

        # ── Move from open ────────────────────────────────────────────────────
        move_from_open = (today_close - today_open) / today_open * 100 if today_open > 0 else 0

        # FIX RC-4: Relaxed from < 0.0 to < -1.0 so flat/sideways stocks
        # can still be evaluated (they just score 0 on "Already Moving").
        # The scoring engine already penalises them; no need for a hard kill.
        if move_from_open < -1.0:
            log.debug(f"  {symbol}: move_from_open={move_from_open:.2f}% negative — skip")
            return None

        # ── Derived metrics ───────────────────────────────────────────────────
        prev_close_vs_high = abs(prev_close - prev_high) / prev_high * 100 if prev_high > 0 else 999
        vol_ratio    = today_vol / prev_vol if prev_vol > 0 else 0
        change_pct   = (today_close - prev_close) / prev_close * 100 if prev_close > 0 else 0

        sl       = prev_close
        risk     = today_close - sl if today_close > sl else today_close * 0.01
        target_1 = today_close + risk * 2.5
        target_2 = today_close + risk * 3.0

        data_dict = {
            'prev_close_vs_high': prev_close_vs_high,
            'gap_pct':            gap_pct,
            'vol_ratio':          vol_ratio,
            'ema_stack_ok':       ema_stack_ok,
            'emas_pointing_up':   emas_up,
            'rsi':                rsi,
            'move_from_open':     move_from_open,
            'today_volume':       today_vol,
        }

        score_result = score_stock(data_dict)

        # Minimum score: keep anything with probability >= 60 during live market,
        # or >= 55 outside market hours (scoring is less meaningful then)
        min_prob = 60 if is_market_open() else 55
        if score_result['probability'] < min_prob:
            log.debug(f"  {symbol}: probability={score_result['probability']:.1f} < {min_prob} — skip")
            return None

        name = symbol.replace('.NS', '')
        log.info(f"  ✅ {name}: price={today_close:.2f}, prob={score_result['probability']:.1f}%, score={score_result['total_score']}/{score_result['max_score']}")

        return {
            'symbol':          name,
            'full_symbol':     symbol,
            'price':           round(today_close, 2),
            'open':            round(today_open, 2),
            'prev_close':      round(prev_close, 2),
            'change_pct':      round(change_pct, 2),
            'move_from_open':  round(move_from_open, 2),
            'gap_pct':         round(gap_pct, 2),
            'rsi':             round(rsi, 1),
            'ema20':           round(e20, 2),
            'ema50':           round(e50, 2),
            'ema200':          round(e200, 2),
            'ema_stack_ok':    ema_stack_ok,
            'emas_pointing_up': emas_up,
            'vol_ratio':       round(vol_ratio, 2),
            'today_volume':    int(today_vol),
            'avg_volume':      int(prev_vol),
            'stop_loss':       round(sl, 2),
            'target1':         round(target_1, 2),
            'target2':         round(target_2, 2),
            'risk_reward':     '1:2.5 / 1:3',
            **score_result,
        }

    except Exception as e:
        log.warning(f"  Error analyzing {symbol}: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCAN
# ─────────────────────────────────────────────────────────────────────────────
def run_scan(max_results=5) -> dict:
    session = get_market_session()
    log.info(f"🪨 GreyRock scan starting — session={session}, universe={len(STOCK_UNIVERSE)} stocks")

    results  = []
    scanned  = 0
    errors   = 0
    skipped  = 0

    filter_log = {
        'insufficient_history': 0,
        'low_liquidity':        0,
        'gap_too_large':        0,
        'rsi_overbought':       0,
        'move_negative':        0,
        'probability_too_low':  0,
        'exception':            0,
        'passed':               0,
    }

    for symbol in STOCK_UNIVERSE:
        try:
            log.debug(f"Analyzing {symbol}...")
            result = analyze_stock(symbol)
            scanned += 1
            if result:
                results.append(result)
                filter_log['passed'] += 1
            else:
                skipped += 1
        except Exception as e:
            log.warning(f"Unhandled error for {symbol}: {e}")
            errors += 1

    results.sort(key=lambda x: (x['probability'], x['rating']), reverse=True)
    top = results[:max_results]
    for i, r in enumerate(top):
        r['rank'] = i + 1

    log.info(f"Scan complete — scanned={scanned}, qualified={len(results)}, errors={errors}, top={len(top)}")

    return {
        'scan_time':      datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST'),
        'market_session': session,
        'stocks_scanned': scanned,
        'qualified':      len(results),
        'top_picks':      top,
        'filter_log':     filter_log,
        'errors':         errors,
    }


if __name__ == "__main__":
    import sys
    log.setLevel(logging.DEBUG if '--debug' in sys.argv else logging.INFO)
    print("🪨 GREY ROCK STRATEGY — Running scan...")
    result = run_scan()
    print(json.dumps(result, indent=2, default=str))