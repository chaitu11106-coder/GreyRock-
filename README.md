# 🪨 GREY ROCK STRATEGY — Intraday Trading Engine

A professional, hedge-fund grade intraday stock scanner for NSE/BSE.
Runs every morning at 9:30 AM IST and surfaces the **3-5 highest probability** momentum trades with stop losses and targets.

---

## 🎯 Strategy Logic

| Filter | Condition |
|--------|-----------|
| Yesterday close | Must be within 1.5% of day high |
| Gap | Only Gap Up or Flat (no gap down) |
| Volume | Today's volume ≥ 500K, ratio ≥ 2x avg |
| EMA Stack | Price > 20 EMA > 50 EMA > 200 EMA |
| EMA Direction | All EMAs pointing upward |
| RSI | Below 65 (not overbought) |
| Momentum | Already +2 to +3% from open |
| Stop Loss | Previous day closing price |
| Risk:Reward | 1:2.5 and 1:3 |

---

## 📁 Project Structure

```
grey-rock-strategy/
├── backend/
│   ├── scanner.py        ← Core scanning + scoring engine
│   ├── app.py            ← Flask REST API
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js        ← Main React UI
│   │   └── App.css       ← Dark hedge fund styling
│   ├── public/
│   │   └── index.html
│   └── package.json
├── start.sh              ← One-command startup (macOS/Linux)
├── start.bat             ← One-command startup (Windows)
└── README.md
```

---

## ⚡ QUICK START

### Step 1 — Install Python dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 2 — Install Node dependencies
```bash
cd frontend
npm install
```

### Step 3 — Start everything

**macOS / Linux:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```
start.bat
```

**Or manually:**
```bash
# Terminal 1 — Backend
cd backend && python app.py

# Terminal 2 — Frontend
cd frontend && npm start
```

Then open **http://localhost:3000**

## Production (recommended: Docker)

Build a single production image that compiles the React app and embeds it in the
Python backend. This creates a self-contained container serving the frontend
and API on port 5000.

Build and run with Docker Compose:

```bash
docker compose build --pull
docker compose up -d
```

Open http://localhost:5000 when ready.

To stop and remove containers:

```bash
docker compose down
```

---

## 🌐 DEPLOYING TO NETLIFY

The frontend is a static React app. For Netlify deployment:

### Option A — Netlify Drop (easiest)
1. Run `cd frontend && npm run build`
2. Drag the `frontend/build/` folder to **app.netlify.com/drop**

### Option B — Netlify CLI
```bash
npm install -g netlify-cli
cd frontend
npm run build
netlify deploy --prod --dir=build
```

### ⚠️ Backend Hosting
The Python backend needs to run somewhere that stays online:
- **Railway.app** (free tier) — Recommended
- **Render.com** (free tier)
- **AWS EC2 / DigitalOcean** (production)

Once hosted, update the `proxy` in `frontend/package.json` to your backend URL:
```json
"proxy": "https://your-backend.railway.app"
```

Or set an environment variable in Netlify:
```
REACT_APP_API_URL=https://your-backend.railway.app
```

And update the axios calls in App.js:
```js
const API = process.env.REACT_APP_API_URL || '';
const res = await axios.get(`${API}/api/scan`);
```

---

## 📡 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/scan` | Run scanner (cached 2 min) |
| `GET /api/scan?force=true` | Force fresh scan |
| `GET /api/market-status` | Current market session |
| `GET /api/stock/RELIANCE` | Analyze single stock |
| `GET /api/universe` | Full stock universe |
| `GET /api/health` | Health check |

---

## ⏰ Best Time to Run

**Run at 9:30 AM IST** — stocks will already be moving and you get clean data.
The scanner auto-refreshes every 2 minutes when "Auto ON" is enabled.

---

## 📊 Scoring System

Each stock is scored out of **90 points** across 8 factors:

| Factor | Max Points |
|--------|-----------|
| Yesterday close near high | 15 |
| Gap up / flat | 10 |
| Volume surge | 15 |
| EMA stack (price>20>50>200) | 20 |
| EMAs pointing up | 10 |
| RSI < 65 | 10 |
| Already moving 2-3%+ | 15 |
| Today volume ≥500K | 5 |

**Win probability** is calibrated from the score (range: 60–92%).

---

## ⚠️ Risk Disclaimer

This tool is for **educational purposes**. Past performance does not guarantee future results.
- Never risk more than **1-2% of capital** per trade
- Always use the provided **stop loss**
- This is not SEBI registered financial advice

---

## 🔧 Customization

### Change stock universe
Edit `STOCK_UNIVERSE` in `backend/scanner.py`.

### Change scan filters
Adjust thresholds at the top of `analyze_stock()` in `scanner.py`.

### Change scoring weights
Edit the `score_stock()` function in `scanner.py`.

### Add US stocks
Change symbols to remove `.NS` suffix and use Yahoo Finance tickers directly.

---

Built with ❤️ for serious intraday traders.
