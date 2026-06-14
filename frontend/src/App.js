import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  TrendingUp, TrendingDown, RefreshCw, Activity, Target,
  Shield, BarChart2, Zap, Clock, ChevronUp, ChevronDown,
  AlertCircle, CheckCircle, XCircle, Star, Eye, Database
} from 'lucide-react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts';
import './App.css';

// ─── MOCK DATA (used when backend is not running) ──────────────────────────
const MOCK_DATA = {
  scan_time: new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) + ' IST',
  market_session: 'LIVE',
  stocks_scanned: 94,
  qualified: 6,
  cached: false,
  top_picks: [
    {
      rank: 1, symbol: 'BAJFINANCE', price: 7284.50, open: 7180.00, prev_close: 7120.00,
      change_pct: 2.31, move_from_open: 1.46, gap_pct: 0.84, rsi: 58.3,
      ema20: 7105, ema50: 6980, ema200: 6540, ema_stack_ok: true, emas_pointing_up: 3,
      vol_ratio: 4.2, today_volume: 1820000, avg_volume: 433333,
      stop_loss: 7120.00, target1: 7448.63, target2: 7530.00, risk_reward: '1:2.5 / 1:3',
      total_score: 82, max_score: 90, rating: 4.6, probability: 87.2,
      breakdown: {
        'Yesterday Close Near High': { score: 14, max: 15, value: '0.4% from high' },
        'Gap Up / Flat': { score: 10, max: 10, value: 'Gap: +0.84%' },
        'Volume Surge': { score: 12, max: 15, value: '4.2x avg volume' },
        'EMA Stack (20>50>200)': { score: 20, max: 20, value: '✅ Perfect stack' },
        'EMAs Pointing Up': { score: 10, max: 10, value: '3/3 EMAs rising' },
        'RSI < 65': { score: 8, max: 10, value: 'RSI: 58.3' },
        'Already Moving (2-3%+)': { score: 8, max: 15, value: '+1.46% from open' },
        'Today Volume ≥500K': { score: 5, max: 5, value: '1,820,000 shares' },
      }
    },
    {
      rank: 2, symbol: 'TATAMOTORS', price: 962.80, open: 940.00, prev_close: 930.00,
      change_pct: 3.53, move_from_open: 2.43, gap_pct: 1.08, rsi: 61.7,
      ema20: 925, ema50: 898, ema200: 820, ema_stack_ok: true, emas_pointing_up: 3,
      vol_ratio: 5.8, today_volume: 6300000, avg_volume: 1086206,
      stop_loss: 930.00, target1: 1005.50, target2: 1018.20, risk_reward: '1:2.5 / 1:3',
      total_score: 78, max_score: 90, rating: 4.3, probability: 83.1,
      breakdown: {
        'Yesterday Close Near High': { score: 12, max: 15, value: '0.9% from high' },
        'Gap Up / Flat': { score: 10, max: 10, value: 'Gap: +1.08%' },
        'Volume Surge': { score: 15, max: 15, value: '5.8x avg volume' },
        'EMA Stack (20>50>200)': { score: 20, max: 20, value: '✅ Perfect stack' },
        'EMAs Pointing Up': { score: 10, max: 10, value: '3/3 EMAs rising' },
        'RSI < 65': { score: 5, max: 10, value: 'RSI: 61.7' },
        'Already Moving (2-3%+)': { score: 15, max: 15, value: '+2.43% from open' },
        'Today Volume ≥500K': { score: 5, max: 5, value: '6,300,000 shares' },
      }
    },
    {
      rank: 3, symbol: 'HCLTECH', price: 1548.30, open: 1520.00, prev_close: 1505.00,
      change_pct: 2.87, move_from_open: 1.86, gap_pct: 0.99, rsi: 56.1,
      ema20: 1498, ema50: 1460, ema200: 1380, ema_stack_ok: true, emas_pointing_up: 3,
      vol_ratio: 3.1, today_volume: 2100000, avg_volume: 677419,
      stop_loss: 1505.00, target1: 1591.08, target2: 1614.50, risk_reward: '1:2.5 / 1:3',
      total_score: 71, max_score: 90, rating: 3.9, probability: 77.4,
      breakdown: {
        'Yesterday Close Near High': { score: 10, max: 15, value: '1.2% from high' },
        'Gap Up / Flat': { score: 10, max: 10, value: 'Gap: +0.99%' },
        'Volume Surge': { score: 12, max: 15, value: '3.1x avg volume' },
        'EMA Stack (20>50>200)': { score: 20, max: 20, value: '✅ Perfect stack' },
        'EMAs Pointing Up': { score: 10, max: 10, value: '3/3 EMAs rising' },
        'RSI < 65': { score: 10, max: 10, value: 'RSI: 56.1' },
        'Already Moving (2-3%+)': { score: 8, max: 15, value: '+1.86% from open' },
        'Today Volume ≥500K': { score: 5, max: 5, value: '2,100,000 shares' },
      }
    },
    {
      rank: 4, symbol: 'ADANIPORTS', price: 1382.60, open: 1358.00, prev_close: 1345.00,
      change_pct: 2.79, move_from_open: 1.81, gap_pct: 0.97, rsi: 59.4,
      ema20: 1340, ema50: 1298, ema200: 1182, ema_stack_ok: true, emas_pointing_up: 2,
      vol_ratio: 2.7, today_volume: 820000, avg_volume: 303703,
      stop_loss: 1345.00, target1: 1420.35, target2: 1456.70, risk_reward: '1:2.5 / 1:3',
      total_score: 65, max_score: 90, rating: 3.6, probability: 73.9,
      breakdown: {
        'Yesterday Close Near High': { score: 12, max: 15, value: '0.7% from high' },
        'Gap Up / Flat': { score: 10, max: 10, value: 'Gap: +0.97%' },
        'Volume Surge': { score: 8, max: 15, value: '2.7x avg volume' },
        'EMA Stack (20>50>200)': { score: 20, max: 20, value: '✅ Perfect stack' },
        'EMAs Pointing Up': { score: 7, max: 10, value: '2/3 EMAs rising' },
        'RSI < 65': { score: 8, max: 10, value: 'RSI: 59.4' },
        'Already Moving (2-3%+)': { score: 8, max: 15, value: '+1.81% from open' },
        'Today Volume ≥500K': { score: 4, max: 5, value: '820,000 shares' },
      }
    },
    {
      rank: 5, symbol: 'BHARTIARTL', price: 1672.40, open: 1650.00, prev_close: 1638.00,
      change_pct: 2.10, move_from_open: 1.36, gap_pct: 0.73, rsi: 62.8,
      ema20: 1632, ema50: 1590, ema200: 1490, ema_stack_ok: true, emas_pointing_up: 3,
      vol_ratio: 2.3, today_volume: 1240000, avg_volume: 539130,
      stop_loss: 1638.00, target1: 1706.90, target2: 1724.20, risk_reward: '1:2.5 / 1:3',
      total_score: 61, max_score: 90, rating: 3.4, probability: 70.6,
      breakdown: {
        'Yesterday Close Near High': { score: 10, max: 15, value: '1.1% from high' },
        'Gap Up / Flat': { score: 7, max: 10, value: 'Gap: +0.73%' },
        'Volume Surge': { score: 8, max: 15, value: '2.3x avg volume' },
        'EMA Stack (20>50>200)': { score: 20, max: 20, value: '✅ Perfect stack' },
        'EMAs Pointing Up': { score: 10, max: 10, value: '3/3 EMAs rising' },
        'RSI < 65': { score: 5, max: 10, value: 'RSI: 62.8' },
        'Already Moving (2-3%+)': { score: 8, max: 15, value: '+1.36% from open' },
        'Today Volume ≥500K': { score: 5, max: 5, value: '1,240,000 shares' },
      }
    },
  ]
};

// ─── HELPERS ───────────────────────────────────────────────────────────────
const formatNum = (n, dec = 2) => n?.toFixed(dec) ?? '—';
const formatVol = (v) => v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? (v / 1e3).toFixed(0) + 'K' : v;

function RatingStars({ rating }) {
  return (
    <div className="rating-stars">
      {[1, 2, 3, 4, 5].map(i => (
        <Star
          key={i}
          size={14}
          className={i <= Math.round(rating) ? 'star-filled' : 'star-empty'}
        />
      ))}
      <span className="rating-num">{rating}</span>
    </div>
  );
}

function ProbabilityArc({ probability }) {
  const pct = Math.min(100, Math.max(0, probability));
  const color = pct >= 80 ? '#00ff88' : pct >= 70 ? '#ffb700' : '#ff4d4d';
  const r = 36, cx = 44, cy = 44;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;

  return (
    <div className="prob-arc">
      <svg width="88" height="88" viewBox="0 0 88 88">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1a1f2e" strokeWidth="8" />
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ filter: `drop-shadow(0 0 6px ${color})` }}
        />
      </svg>
      <div className="prob-label" style={{ color }}>
        <span className="prob-num">{pct.toFixed(0)}%</span>
        <span className="prob-sub">WIN</span>
      </div>
    </div>
  );
}

function ScoreBreakdown({ breakdown }) {
  const entries = Object.entries(breakdown);
  return (
    <div className="breakdown-grid">
      {entries.map(([key, val]) => {
        const pct = (val.score / val.max) * 100;
        const color = pct >= 80 ? '#00ff88' : pct >= 50 ? '#ffb700' : '#ff4d4d';
        return (
          <div key={key} className="breakdown-row">
            <div className="bd-label">{key}</div>
            <div className="bd-bar-wrap">
              <div className="bd-bar" style={{ width: pct + '%', background: color }} />
            </div>
            <div className="bd-score" style={{ color }}>{val.score}/{val.max}</div>
            <div className="bd-value">{val.value}</div>
          </div>
        );
      })}
    </div>
  );
}

function StockCard({ stock, expanded, onToggle }) {
  const rankColors = ['#ffd700', '#c0c0c0', '#cd7f32', '#7c8db0', '#7c8db0'];
  const rankColor = rankColors[stock.rank - 1] || '#7c8db0';
  const up = stock.change_pct >= 0;

  const radarData = Object.entries(stock.breakdown).map(([k, v]) => ({
    subject: k.split(' ')[0],
    value: Math.round((v.score / v.max) * 100),
  }));

  return (
    <div className={`stock-card ${expanded ? 'expanded' : ''} rank-${stock.rank}`}>
      <div className="card-header" onClick={onToggle}>
        {/* Rank badge */}
        <div className="rank-badge" style={{ borderColor: rankColor, color: rankColor }}>
          #{stock.rank}
        </div>

        {/* Symbol + name */}
        <div className="card-symbol">
          <span className="symbol-text">{stock.symbol}</span>
          <RatingStars rating={stock.rating} />
        </div>

        {/* Price */}
        <div className="card-price">
          <span className="price-main">₹{formatNum(stock.price)}</span>
          <span className={`price-change ${up ? 'up' : 'down'}`}>
            {up ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            {formatNum(Math.abs(stock.change_pct))}%
          </span>
        </div>

        {/* Probability */}
        <ProbabilityArc probability={stock.probability} />

        {/* Key stats */}
        <div className="card-stats">
          <div className="stat-pill">
            <Zap size={11} />
            +{formatNum(stock.move_from_open)}% move
          </div>
          <div className="stat-pill">
            <BarChart2 size={11} />
            {formatNum(stock.vol_ratio)}x vol
          </div>
          <div className="stat-pill">
            RSI {formatNum(stock.rsi, 0)}
          </div>
        </div>

        {/* Expand icon */}
        <div className="expand-icon">
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>
      </div>

      {expanded && (
        <div className="card-body">
          {/* Trade plan */}
          <div className="trade-plan">
            <div className="trade-plan-title">
              <Target size={14} /> TRADE PLAN
            </div>
            <div className="trade-boxes">
              <div className="tbox entry">
                <div className="tbox-label">ENTRY</div>
                <div className="tbox-val">₹{formatNum(stock.price)}</div>
                <div className="tbox-sub">Current Market</div>
              </div>
              <div className="tbox sl">
                <div className="tbox-label"><Shield size={11} /> STOP LOSS</div>
                <div className="tbox-val">₹{formatNum(stock.stop_loss)}</div>
                <div className="tbox-sub">Prev Day Close</div>
              </div>
              <div className="tbox t1">
                <div className="tbox-label">TARGET 1</div>
                <div className="tbox-val">₹{formatNum(stock.target1)}</div>
                <div className="tbox-sub">1:2.5 R:R</div>
              </div>
              <div className="tbox t2">
                <div className="tbox-label">TARGET 2</div>
                <div className="tbox-val">₹{formatNum(stock.target2)}</div>
                <div className="tbox-sub">1:3 R:R</div>
              </div>
            </div>
          </div>

          {/* Two columns: breakdown + radar */}
          <div className="detail-columns">
            <div className="detail-left">
              <div className="section-title">SCORE BREAKDOWN</div>
              <ScoreBreakdown breakdown={stock.breakdown} />
            </div>
            <div className="detail-right">
              <div className="section-title">FACTOR RADAR</div>
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#2a3050" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: '#7c8db0', fontSize: 10 }} />
                  <Radar dataKey="value" stroke="#00ff88" fill="#00ff88" fillOpacity={0.15} strokeWidth={2} />
                  <Tooltip
                    contentStyle={{ background: '#0d111e', border: '1px solid #2a3050', borderRadius: 6 }}
                    labelStyle={{ color: '#e0e6ff' }}
                    itemStyle={{ color: '#00ff88' }}
                  />
                </RadarChart>
              </ResponsiveContainer>

              {/* EMA info */}
              <div className="ema-row">
                <div className="ema-item">
                  <span className="ema-label">20 EMA</span>
                  <span className="ema-val">₹{formatNum(stock.ema20)}</span>
                </div>
                <div className="ema-item">
                  <span className="ema-label">50 EMA</span>
                  <span className="ema-val">₹{formatNum(stock.ema50)}</span>
                </div>
                <div className="ema-item">
                  <span className="ema-label">200 EMA</span>
                  <span className="ema-val">₹{formatNum(stock.ema200)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom stats */}
          <div className="bottom-stats">
            <div className="bs-item">
              <span className="bs-l">Open</span>
              <span className="bs-v">₹{formatNum(stock.open)}</span>
            </div>
            <div className="bs-item">
              <span className="bs-l">Prev Close</span>
              <span className="bs-v">₹{formatNum(stock.prev_close)}</span>
            </div>
            <div className="bs-item">
              <span className="bs-l">Gap</span>
              <span className={`bs-v ${stock.gap_pct >= 0 ? 'up' : 'down'}`}>{stock.gap_pct >= 0 ? '+' : ''}{formatNum(stock.gap_pct)}%</span>
            </div>
            <div className="bs-item">
              <span className="bs-l">Today Vol</span>
              <span className="bs-v">{formatVol(stock.today_volume)}</span>
            </div>
            <div className="bs-item">
              <span className="bs-l">Avg Vol</span>
              <span className="bs-v">{formatVol(stock.avg_volume)}</span>
            </div>
            <div className="bs-item">
              <span className="bs-l">Vol Ratio</span>
              <span className="bs-v">{formatNum(stock.vol_ratio)}x</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SessionBadge({ session }) {
  const map = {
    LIVE: { color: '#00ff88', label: '● LIVE', pulse: true },
    OPENING: { color: '#ffb700', label: '◐ OPENING', pulse: true },
    PRE_MARKET: { color: '#7c8db0', label: '○ PRE-MARKET', pulse: false },
    CLOSED: { color: '#ff4d4d', label: '✕ CLOSED', pulse: false },
  };
  const { color, label, pulse } = map[session] || map.CLOSED;
  return (
    <span className={`session-badge ${pulse ? 'pulse' : ''}`} style={{ color, borderColor: color }}>
      {label}
    </span>
  );
}

// ─── MAIN APP ──────────────────────────────────────────────────────────────
export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedCard, setExpandedCard] = useState(0);
  const [useMock, setUseMock] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = useCallback(async (force = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`/api/scan${force ? '?force=true' : ''}`, { timeout: 100000 });
      setData(res.data);
      setLastUpdated(new Date());
      setUseMock(false);
    } catch (e) {
      // Backend not running → use mock
      console.warn('Backend unavailable, using demo data');
      setData(MOCK_DATA);
      setUseMock(true);
      setLastUpdated(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => fetchData(true), 120000); // every 2 min
    return () => clearInterval(interval);
  }, [autoRefresh, fetchData]);

  const topStock = data?.top_picks?.[0];

  return (
    <div className="app">
      {/* ── HEADER ── */}
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <div className="logo-icon">
              <div className="logo-rock">🪨</div>
            </div>
            <div className="logo-text">
              <span className="logo-main">GREY ROCK</span>
              <span className="logo-sub">STRATEGY ENGINE</span>
            </div>
          </div>
          {data && <SessionBadge session={data.market_session} />}
        </div>

        <div className="header-center">
          {data && (
            <div className="header-stats">
              <div className="hstat">
                <span className="hstat-val">{data.stocks_scanned}</span>
                <span className="hstat-l">Scanned</span>
              </div>
              <div className="hstat-divider" />
              <div className="hstat">
                <span className="hstat-val">{data.qualified}</span>
                <span className="hstat-l">Qualified</span>
              </div>
              <div className="hstat-divider" />
              <div className="hstat">
                <span className="hstat-val">{data.top_picks?.length}</span>
                <span className="hstat-l">Top Picks</span>
              </div>
            </div>
          )}
        </div>

        <div className="header-right">
          {useMock && (
            <div className="demo-badge">
              <AlertCircle size={12} /> DEMO MODE
            </div>
          )}
          <button
            className={`auto-btn ${autoRefresh ? 'active' : ''}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Activity size={13} />
            {autoRefresh ? 'Auto ON' : 'Auto OFF'}
          </button>
          <button
            className="refresh-btn"
            onClick={() => fetchData(true)}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'spinning' : ''} />
            {loading ? 'Scanning...' : 'Scan Now'}
          </button>
          {lastUpdated && (
            <div className="last-updated">
              <Clock size={11} />
              {lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </div>
          )}
        </div>
      </header>

      {/* ── STRATEGY CRITERIA BAR ── */}
      <div className="criteria-bar">
        {[
          { icon: <TrendingUp size={11} />, label: 'Close Near High' },
          { icon: <ChevronUp size={11} />, label: 'Gap Up/Flat' },
          { icon: <BarChart2 size={11} />, label: 'Rising Volume' },
          { icon: <Activity size={11} />, label: 'EMA Stack' },
          { icon: <TrendingUp size={11} />, label: 'EMAs Up' },
          { icon: <Eye size={11} />, label: 'RSI < 65' },
          { icon: <Database size={11} />, label: 'Vol ≥500K' },
          { icon: <Zap size={11} />, label: '2-3% Moving' },
          { icon: <Target size={11} />, label: '1:2.5/3 R:R' },
        ].map((c, i) => (
          <div key={i} className="criteria-pill">
            <CheckCircle size={10} className="criteria-check" />
            {c.icon} {c.label}
          </div>
        ))}
      </div>

      <main className="main">
        {/* ── LOADING ── */}
        {loading && !data && (
          <div className="loading-screen">
            <div className="loading-rock">🪨</div>
            <div className="loading-text">Scanning {MOCK_DATA.stocks_scanned}+ stocks...</div>
            <div className="loading-sub">Applying Grey Rock filters</div>
            <div className="loading-bars">
              {['EMA Analysis', 'Volume Scan', 'RSI Check', 'Gap Filter', 'Scoring'].map((l, i) => (
                <div key={l} className="loading-bar-row" style={{ animationDelay: `${i * 0.15}s` }}>
                  <span>{l}</span>
                  <div className="loading-bar"><div className="loading-fill" /></div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── TOP PICK HIGHLIGHT ── */}
        {data && topStock && !loading && (
          <div className="top-pick-banner">
            <div className="tpb-left">
              <div className="tpb-badge">🏆 BEST TRADE TODAY</div>
              <div className="tpb-symbol">{topStock.symbol}</div>
              <div className="tpb-price">₹{formatNum(topStock.price)}</div>
            </div>
            <div className="tpb-center">
              <div className="tpb-stat">
                <span className="tpb-l">Entry</span>
                <span className="tpb-v">₹{formatNum(topStock.price)}</span>
              </div>
              <div className="tpb-arrow">→</div>
              <div className="tpb-stat">
                <span className="tpb-l">Stop Loss</span>
                <span className="tpb-v red">₹{formatNum(topStock.stop_loss)}</span>
              </div>
              <div className="tpb-arrow">→</div>
              <div className="tpb-stat">
                <span className="tpb-l">Target 1</span>
                <span className="tpb-v green">₹{formatNum(topStock.target1)}</span>
              </div>
              <div className="tpb-arrow">→</div>
              <div className="tpb-stat">
                <span className="tpb-l">Target 2</span>
                <span className="tpb-v green">₹{formatNum(topStock.target2)}</span>
              </div>
            </div>
            <div className="tpb-right">
              <ProbabilityArc probability={topStock.probability} />
              <div className="tpb-rr">R:R = 1:2.5 / 1:3</div>
            </div>
          </div>
        )}

        {/* ── STOCK CARDS ── */}
        {data && (
          <div className="cards-container">
            <div className="cards-header">
              <div className="cards-title">
                <Zap size={15} />
                TODAY'S PICKS — {data.scan_time}
              </div>
              <div className="cards-note">
                SL = Previous Day Close · Sorted by Win Probability
              </div>
            </div>

            {data.top_picks?.length === 0 ? (
              <div className="no-results">
                <XCircle size={40} />
                <div>No stocks passed all filters today</div>
                <div className="no-results-sub">Market conditions may not be ideal. Try after 9:45 AM IST.</div>
              </div>
            ) : (
              data.top_picks?.map((stock) => (
                <StockCard
                  key={stock.symbol}
                  stock={stock}
                  expanded={expandedCard === stock.rank - 1}
                  onToggle={() => setExpandedCard(expandedCard === stock.rank - 1 ? -1 : stock.rank - 1)}
                />
              ))
            )}
          </div>
        )}

        {/* ── DISCLAIMER ── */}
        <div className="disclaimer">
          <AlertCircle size={12} />
          Grey Rock Strategy is for educational purposes. Past performance does not guarantee future results.
          Always manage risk appropriately. Never risk more than 1-2% of capital per trade.
        </div>
      </main>
    </div>
  );
}
