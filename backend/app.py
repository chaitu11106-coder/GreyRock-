"""
GREY ROCK STRATEGY - API Server
Flask REST API that serves scan results to the React frontend
"""

import os
import numpy as np
import threading
import time
from datetime import datetime
import pytz
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scanner import run_scan, get_market_session, STOCK_UNIVERSE

# Setup paths for serving frontend build
base_dir = os.path.abspath(os.path.dirname(__file__) + '/..')
build_dir = os.path.join(base_dir, 'frontend', 'build')

# Create Flask app with static folder pointing to the build directory
app = Flask(__name__, static_folder=build_dir, static_url_path='')
CORS(app)

IST = pytz.timezone('Asia/Kolkata')

# Cache to avoid hammering yfinance
_cache = {
    'result': None,
    'last_scan': None,
    'is_scanning': False,
}
CACHE_TTL = 120  # seconds

def _do_scan():
    _cache['is_scanning'] = True
    try:
        result = run_scan(max_results=5)
        _cache['result'] = result
        _cache['last_scan'] = time.time()
    except Exception as e:
        print(f"Scan error: {e}")
    finally:
        _cache['is_scanning'] = False


def _sanitize_json(obj):
    # Recursively convert numpy types to native Python types for JSON
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_sanitize_json(v) for v in obj)
    if isinstance(obj, np.generic):
        return obj.item()
    return obj


def jsonify_safe(obj):
    return jsonify(_sanitize_json(obj))

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': datetime.now(IST).strftime('%H:%M:%S IST')})

@app.route('/api/scan', methods=['GET'])
def scan():
    force = request.args.get('force', 'false').lower() == 'true'
    now = time.time()
    cache_age = now - (_cache['last_scan'] or 0)

    # If cached result exists and fresh, return it
    if not force and _cache['result'] and cache_age < CACHE_TTL:
        result = dict(_cache['result'])
        result['cached'] = True
        result['cache_age_seconds'] = int(cache_age)
        return jsonify_safe(result)

    # Run scan in thread
    if not _cache['is_scanning']:
        t = threading.Thread(target=_do_scan)
        t.daemon = True
        t.start()

    # Always wait for scan to complete (max 90 seconds)
    start_time = time.time()
    while _cache['is_scanning'] and (time.time() - start_time) < 90:
        time.sleep(0.5)

    if _cache['result']:
        result = dict(_cache['result'])
        result['cached'] = False
        return jsonify_safe(result)

    return jsonify({'status': 'error', 'message': 'Scan timed out'})

@app.route('/api/stock/<symbol>', methods=['GET'])
def single_stock(symbol):
    from scanner import analyze_stock
    full_sym = symbol if '.NS' in symbol else symbol + '.NS'
    result = analyze_stock(full_sym)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Stock not found or filtered out'}), 404

@app.route('/api/universe', methods=['GET'])
def universe():
    return jsonify({'stocks': [s.replace('.NS', '') for s in STOCK_UNIVERSE], 'total': len(STOCK_UNIVERSE)})

@app.route('/api/market-status', methods=['GET'])
def market_status():
    session = get_market_session()
    now = datetime.now(IST)
    return jsonify({
        'session': session,
        'time': now.strftime('%H:%M:%S'),
        'date': now.strftime('%d %b %Y'),
        'is_live': session == 'LIVE',
    })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    # Serve static files directly
    if path != '' and os.path.exists(os.path.join(build_dir, path)):
        return send_from_directory(build_dir, path)
    # For any other route, serve index.html (SPA routing)
    index_path = os.path.join(build_dir, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(build_dir, 'index.html')
    return jsonify({'error': 'Frontend build not found'}), 404

if __name__ == '__main__':
    print("🪨 Grey Rock Strategy API starting on http://0.0.0.0:5000")
    # Prefer waitress for production if installed
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000)
    except Exception:
        app.run(debug=False, port=5000, threaded=True)
