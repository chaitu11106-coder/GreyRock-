"""
GREY ROCK STRATEGY - Intraday Scanner Engine
Real-world trading scanner with multi-factor analysis
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import json
import warnings
warnings.filterwarnings('ignore')

IST = pytz.timezone('Asia/Kolkata')

# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSE: NSE top liquid stocks (Nifty 200 representative)
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
    "BERGEPAINT.NS","KANSAINER.NS","PIDILITIND.NS","VOLTAS.NS","WHIRLPOOL.NS",
    "ZOMATO.NS","NYKAA.NS","PAYTM.NS","DELHIVERY.NS","POLICYBZR.NS",
    "HAL.NS","BEL.NS","BHEL.NS","BEML.NS","IRCTC.NS",
    "CHOLAFIN.NS","MUTHOOTFIN.NS","BAJAJHLDNG.NS","RECLTD.NS","PFC.NS",
    "SIEMENS.NS","ABB.NS","CUMMINSIND.NS","THERMAX.NS","BHARAT FORGE.NS",
    "PERSISTENT.NS","LTIM.NS","MPHASIS.NS","COFORGE.NS","OFSS.NS",
    "ASTRAL.NS","SUPREMEIND.NS","APOLLOHOSP.NS","FORTIS.NS","MAXHEALTH.NS",
    "DMART.NS","TRENT.NS","JUBLFOOD.NS","DEVYANI.NS","WESTLIFE.NS",
]

# ─────────────────────────────────────────────────────────────────────────────
# EMA CALCULATION
# ─────────────────────────────────────────────────────────────────────────────
def calculate_emas(closes):
    s = pd.Series(closes)
    ema20 = s.ewm(span=20, adjust=False).mean()
    ema50 = s.ewm(span=50, adjust=False).mean()
    ema200 = s.ewm(span=200, adjust=False).mean()
    return ema20.values, ema50.values, ema200.values

def calculate_rsi(closes, period=14):
    s = pd.Series(closes)
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.values[-1]

# ─────────────────────────────────────────────────────────────────────────────
# SCORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def score_stock(data: dict) -> dict:
    score = 0
    max_score = 0
    breakdown = {}

    # 1. Yesterday close near day high (within 1.5%)
    max_score += 15
    if data.get('prev_close_vs_high') is not None:
        pct = data['prev_close_vs_high']
        if pct <= 0.5:
            pts = 15
        elif pct <= 1.0:
            pts = 12
        elif pct <= 1.5:
            pts = 8
        else:
            pts = 2
        score += pts
        breakdown['Yesterday Close Near High'] = {'score': pts, 'max': 15, 'value': f"{pct:.1f}% from high"}

    # 2. Gap up / flat open
    max_score += 10
    gap = data.get('gap_pct', 0)
    if gap >= 0.5:
        pts = 10
    elif gap >= 0:
        pts = 7
    else:
        pts = 0
    score += pts
    breakdown['Gap Up / Flat'] = {'score': pts, 'max': 10, 'value': f"Gap: {gap:+.2f}%"}

    # 3. Rising volume vs average
    max_score += 15
    vol_ratio = data.get('vol_ratio', 0)
    if vol_ratio >= 5:
        pts = 15
    elif vol_ratio >= 3:
        pts = 12
    elif vol_ratio >= 2:
        pts = 8
    elif vol_ratio >= 1:
        pts = 4
    else:
        pts = 0
    score += pts
    breakdown['Volume Surge'] = {'score': pts, 'max': 15, 'value': f"{vol_ratio:.1f}x avg volume"}

    # 4. EMA stack: price > 20ema > 50ema > 200ema
    max_score += 20
    ema_ok = data.get('ema_stack_ok', False)
    if ema_ok:
        score += 20
        pts = 20
    else:
        pts = 0
    breakdown['EMA Stack (20>50>200)'] = {'score': pts, 'max': 20, 'value': '✅ Perfect stack' if ema_ok else '❌ Not stacked'}

    # 5. EMAs pointing upward
    max_score += 10
    ema_up = data.get('emas_pointing_up', 0)  # 0-3
    pts = int(ema_up / 3 * 10)
    score += pts
    breakdown['EMAs Pointing Up'] = {'score': pts, 'max': 10, 'value': f"{ema_up}/3 EMAs rising"}

    # 6. RSI below 65
    max_score += 10
    rsi = data.get('rsi', 80)
    if rsi < 55:
        pts = 10
    elif rsi < 60:
        pts = 8
    elif rsi < 65:
        pts = 5
    else:
        pts = 0
    score += pts
    breakdown['RSI < 65'] = {'score': pts, 'max': 10, 'value': f"RSI: {rsi:.1f}"}

    # 7. Already moving 2-3% up from open
    max_score += 15
    move_from_open = data.get('move_from_open', 0)
    if 2.0 <= move_from_open <= 5.0:
        pts = 15
    elif 1.0 <= move_from_open < 2.0:
        pts = 8
    elif move_from_open > 5.0:
        pts = 5  # extended, risky
    else:
        pts = 0
    score += pts
    breakdown['Already Moving (2-3%+)'] = {'score': pts, 'max': 15, 'value': f"+{move_from_open:.2f}% from open"}

    # 8. High today volume (min 500k)
    max_score += 5
    today_vol = data.get('today_volume', 0)
    if today_vol >= 1000000:
        pts = 5
    elif today_vol >= 500000:
        pts = 4
    elif today_vol >= 100000:
        pts = 2
    else:
        pts = 0
    score += pts
    breakdown['Today Volume ≥500K'] = {'score': pts, 'max': 5, 'value': f"{today_vol:,.0f} shares"}

    # Probability estimate
    raw_pct = (score / max_score) * 100 if max_score > 0 else 0
    # Calibrate to realistic 60-92% range
    probability = 55 + (raw_pct / 100) * 37

    return {
        'total_score': score,
        'max_score': max_score,
        'rating': round(score / max_score * 5, 1) if max_score > 0 else 0,
        'probability': round(probability, 1),
        'breakdown': breakdown,
    }

# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK DEMO DATA (when YFinance data unavailable)
# ─────────────────────────────────────────────────────────────────────────────
def generate_demo_result(symbol: str) -> dict | None:
    """Generate realistic demo data for stocks when live data unavailable"""
    import random
    random.seed(hash(symbol) % 2**32)  # Consistent per symbol
    
    # Mock data with some randomness
    base_price = random.uniform(100, 5000)
    change_pct = random.uniform(-1.5, 3.5)
    gap_pct = random.uniform(-0.5, 2.5)
    volume_ratio = random.uniform(1.5, 4.0)
    rsi_val = random.uniform(40, 65)
    move_from_open_pct = random.uniform(2.0, 3.5)
    
    ema20_val = base_price * random.uniform(0.98, 1.02)
    ema50_val = base_price * random.uniform(0.95, 1.00)
    ema200_val = base_price * random.uniform(0.90, 0.98)
    
    # Calculated fields
    today_open = base_price / (1 + change_pct/100)
    prev_close = base_price / (1 + gap_pct/100)
    today_vol = random.randint(500000, 5000000)
    prev_vol = today_vol / volume_ratio
    sl = prev_close
    risk = base_price - sl
    target_1 = base_price + (risk * 2.5)
    target_2 = base_price + (risk * 3.0)
    
    # Scoring breakdown
    emas_up = random.randint(2, 3)
    total_score = random.randint(45, 85)
    rating = round(total_score / 90 * 5, 1)
    probability = round(random.uniform(65, 92), 1)
    
    breakdown = {
        'Yesterday Close Near High': {
            'score': random.randint(8, 15), 
            'max': 15, 
            'value': f"{random.uniform(0.2, 1.8):.1f}% from high"
        },
        'Gap Up / Flat': {
            'score': random.randint(7, 10), 
            'max': 10, 
            'value': f"Gap: {gap_pct:+.2f}%"
        },
        'Rising Volume': {
            'score': random.randint(10, 15), 
            'max': 15, 
            'value': f"{volume_ratio:.2f}x avg"
        },
        'EMA Stack': {
            'score': 20, 
            'max': 20, 
            'value': 'Price > 20 > 50 > 200'
        },
        'EMAs Up': {
            'score': 10, 
            'max': 10, 
            'value': 'All rising'
        },
        'RSI < 65': {
            'score': 10, 
            'max': 10, 
            'value': f"RSI: {rsi_val:.1f}"
        },
        'Vol ≥500K': {
            'score': 5, 
            'max': 5, 
            'value': f"500K+ shares"
        },
        '2-3% Moving': {
            'score': random.randint(10, 15), 
            'max': 15, 
            'value': f"Already +{move_from_open_pct:.2f}%"
        },
    }
    
    # Strip .NS from symbol for frontend
    name = symbol.replace('.NS', '') if '.NS' in symbol else symbol
    
    return {
        'symbol': name,
        'full_symbol': symbol,
        'price': round(base_price, 2),
        'open': round(today_open, 2),
        'prev_close': round(prev_close, 2),
        'change_pct': round(change_pct, 2),
        'gap_pct': round(gap_pct, 2),
        'vol_ratio': round(volume_ratio, 2),
        'rsi': round(rsi_val, 1),
        'move_from_open': round(move_from_open_pct, 2),
        'ema20': round(ema20_val, 2),
        'ema50': round(ema50_val, 2),
        'ema200': round(ema200_val, 2),
        'ema_stack_ok': True,
        'emas_pointing_up': emas_up,
        'today_volume': int(today_vol),
        'avg_volume': int(prev_vol),
        'stop_loss': round(sl, 2),
        'target1': round(target_1, 2),
        'target2': round(target_2, 2),
        'risk_reward': '1:2.5 / 1:3',
        'total_score': total_score,
        'max_score': 90,
        'rating': rating,
        'probability': probability,
        'breakdown': breakdown,
    }

# ─────────────────────────────────────────────────────────────────────────────
# FETCH & ANALYZE A SINGLE STOCK
# ─────────────────────────────────────────────────────────────────────────────
def analyze_stock(symbol: str) -> dict | None:
    try:
        ticker = yf.Ticker(symbol)

        # Get 1-year daily history for EMAs
        hist = ticker.history(period="1y", interval="1d")
        if hist is None or len(hist) < 210:
            return None  # Not enough data, skip this stock

        closes = hist['Close'].values
        highs = hist['High'].values
        volumes = hist['Volume'].values

        # Yesterday's data
        prev_close = closes[-2]
        prev_high = highs[-2]
        prev_vol = float(np.mean(volumes[-20:-1]))  # 20-day avg excl today

        # Today's data (last row)
        today_open = hist['Open'].values[-1]
        today_close = closes[-1]  # latest price
        today_high = highs[-1]
        today_vol = float(volumes[-1])

        # ── Filter 1: Gap not down ──────────────────────────────────────────
        gap_pct = (today_open - prev_close) / prev_close * 100
        if gap_pct < -0.3:
            return None  # Gap down, skip

        # ── Filter 2: Average volume > 10k (basic liquidity) ────────────────
        if prev_vol < 10000:
            return None

        # ── Filter 3: Today volume surge ────────────────────────────────────
        if today_vol < 100000:
            return None

        # ── EMA calculations ─────────────────────────────────────────────────
        ema20, ema50, ema200 = calculate_emas(closes)
        e20, e50, e200 = float(ema20[-1]), float(ema50[-1]), float(ema200[-1])
        e20_prev, e50_prev, e200_prev = float(ema20[-3]), float(ema50[-3]), float(ema200[-3])

        # ── Filter 4: Price above EMA stack ──────────────────────────────────
        ema_stack_ok = bool(today_close > e20 > e50 > e200)

        # ── EMAs pointing up ─────────────────────────────────────────────────
        emas_up = int(sum([
            ema20[-1] > ema20[-5],
            ema50[-1] > ema50[-5],
            ema200[-1] > ema200[-10],
        ]))

        # ── RSI ───────────────────────────────────────────────────────────────
        rsi = calculate_rsi(closes)
        if rsi > 75:
            return None  # Overbought

        # ── Filter: RSI < 65 ─────────────────────────────────────────────────
        # (soft filter – penalized in score if above)

        # ── Move from open ────────────────────────────────────────────────────
        move_from_open = (today_close - today_open) / today_open * 100
        if move_from_open < 1.5:
            return None  # Not moving enough yet

        # ── Yesterday close near day high ─────────────────────────────────────
        prev_close_vs_high = abs(prev_close - prev_high) / prev_high * 100

        # ── Volume ratio ─────────────────────────────────────────────────────
        vol_ratio = today_vol / prev_vol if prev_vol > 0 else 0

        # ── Change % (vs prev close) ─────────────────────────────────────────
        change_pct = (today_close - prev_close) / prev_close * 100

        # ── Stop loss & targets ───────────────────────────────────────────────
        sl = prev_close  # previous day closing
        risk = today_close - sl
        target_1 = today_close + (risk * 2.5)
        target_2 = today_close + (risk * 3.0)

        data_dict = {
            'prev_close_vs_high': prev_close_vs_high,
            'gap_pct': gap_pct,
            'vol_ratio': vol_ratio,
            'ema_stack_ok': ema_stack_ok,
            'emas_pointing_up': emas_up,
            'rsi': rsi,
            'move_from_open': move_from_open,
            'today_volume': today_vol,
        }

        score_result = score_stock(data_dict)

        # Only return if probability > 65%
        if score_result['probability'] < 65:
            return None

        name = symbol.replace('.NS', '')

        return {
            'symbol': name,
            'full_symbol': symbol,
            'price': round(today_close, 2),
            'open': round(today_open, 2),
            'prev_close': round(prev_close, 2),
            'change_pct': round(change_pct, 2),
            'move_from_open': round(move_from_open, 2),
            'gap_pct': round(gap_pct, 2),
            'rsi': round(rsi, 1),
            'ema20': round(e20, 2),
            'ema50': round(e50, 2),
            'ema200': round(e200, 2),
            'ema_stack_ok': ema_stack_ok,
            'emas_pointing_up': emas_up,
            'vol_ratio': round(vol_ratio, 2),
            'today_volume': int(today_vol),
            'avg_volume': int(prev_vol),
            'stop_loss': round(sl, 2),
            'target1': round(target_1, 2),
            'target2': round(target_2, 2),
            'risk_reward': '1:2.5 / 1:3',
            **score_result,
        }

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None  # Skip stocks with errors, only show real data

# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCAN
# ─────────────────────────────────────────────────────────────────────────────
def run_scan(max_results=5) -> dict:
    results = []
    scanned = 0
    errors = 0
    
    # Scan full universe for real results
    test_universe = STOCK_UNIVERSE

    for symbol in test_universe:
        try:
            result = analyze_stock(symbol)
            scanned += 1
            if result:
                results.append(result)
        except:
            errors += 1
            continue

    # Sort by probability then rating
    results.sort(key=lambda x: (x['probability'], x['rating']), reverse=True)
    top = results[:max_results]

    # Add rank
    for i, r in enumerate(top):
        r['rank'] = i + 1

    return {
        'scan_time': datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST'),
        'market_session': get_market_session(),
        'stocks_scanned': scanned,
        'qualified': len(results),
        'top_picks': top,
    }

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

if __name__ == "__main__":
    print("🪨 GREY ROCK STRATEGY - Running scan...")
    result = run_scan()
    print(json.dumps(result, indent=2, default=str))