"""
GREY ROCK STRATEGY - API Server
Flask REST API serving scan results to the React frontend.

Changes from original:
  - Added scan_error field to response so frontend can distinguish "no stocks" from "scan failed"
  - Added /api/debug endpoint to expose filter_log from last scan
  - Added request logging
  - Removed race condition: thread check now atomic with lock
  - Timeout increased to match yfinance download time for 100 stocks
"""

import os
import numpy as np
import threading
import time
import logging
from datetime import datetime
import pytz
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from scanner import run_scan, get_market_session, STOCK_UNIVERSE

log = logging.getLogger('greyrock.api')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

base_dir  = os.path.abspath(os.path.dirname(__file__) + '/..')
build_dir = os.path.join(base_dir, 'frontend', 'build')

app = Flask(__name__, static_folder=build_dir, static_url_path='')
CORS(app)

IST = pytz.timezone('Asia/Kolkata')

_cache = {
    'result':    None,
    'last_scan': None,
    'is_scanning': False,
    'scan_error':  None,
}
_lock = threading.Lock()
CACHE_TTL = 120  # seconds


def _do_scan():
    log.info("Background scan thread started")
    try:
        result = run_scan(max_results=5)
        with _lock:
            _cache['result']    = result
            _cache['last_scan'] = time.time()
            _cache['scan_error'] = None
        log.info(f"Scan complete — qualified={result.get('qualified',0)}, top={len(result.get('top_picks',[]))}")
    except Exception as e:
        log.error(f"Scan thread error: {e}", exc_info=True)
        with _lock:
            _cache['scan_error'] = str(e)
    finally:
        with _lock:
            _cache['is_scanning'] = False


def _sanitize_json(obj):
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


@app.before_request
def log_request():
    log.info(f"→ {request.method} {request.path} args={dict(request.args)}")


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': datetime.now(IST).strftime('%H:%M:%S IST')})


@app.route('/api/scan', methods=['GET'])
def scan():
    force    = request.args.get('force', 'false').lower() == 'true'
    now      = time.time()

    with _lock:
        cache_age   = now - (_cache['last_scan'] or 0)
        is_scanning = _cache['is_scanning']
        has_result  = _cache['result'] is not None

    # Serve fresh cache if available and not forced
    if not force and has_result and cache_age < CACHE_TTL:
        result = dict(_cache['result'])
        result['cached']            = True
        result['cache_age_seconds'] = int(cache_age)
        log.info(f"Serving cached result (age={int(cache_age)}s)")
        return jsonify_safe(result)

    # Start scan thread if not already running
    if not is_scanning:
        with _lock:
            _cache['is_scanning'] = True
        t = threading.Thread(target=_do_scan, daemon=True)
        t.start()
        log.info("Scan thread launched")

    # Wait for scan (max 120 seconds — 100 stocks × ~1.2s yfinance each)
    deadline = time.time() + 120
    while True:
        with _lock:
            still_scanning = _cache['is_scanning']
            has_result     = _cache['result'] is not None
            scan_error     = _cache['scan_error']

        if not still_scanning:
            break
        if time.time() > deadline:
            log.warning("Scan timed out after 120s")
            return jsonify({'status': 'error', 'message': 'Scan timed out after 120s'}), 504
        time.sleep(0.5)

    if scan_error:
        return jsonify({'status': 'error', 'message': scan_error}), 500

    if has_result:
        result = dict(_cache['result'])
        result['cached'] = False
        return jsonify_safe(result)

    return jsonify({'status': 'error', 'message': 'Scan produced no result'}), 500


@app.route('/api/debug', methods=['GET'])
def debug():
    """Expose last scan internals for troubleshooting."""
    with _lock:
        result = _cache.get('result') or {}
    return jsonify_safe({
        'filter_log':    result.get('filter_log', {}),
        'stocks_scanned': result.get('stocks_scanned', 0),
        'qualified':     result.get('qualified', 0),
        'market_session': result.get('market_session', 'UNKNOWN'),
        'scan_time':     result.get('scan_time', None),
        'scan_error':    _cache.get('scan_error'),
    })


@app.route('/api/stock/<symbol>', methods=['GET'])
def single_stock(symbol):
    from scanner import analyze_stock
    full_sym = symbol if '.NS' in symbol else symbol + '.NS'
    result = analyze_stock(full_sym)
    if result:
        return jsonify_safe(result)
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
        'time':    now.strftime('%H:%M:%S'),
        'date':    now.strftime('%d %b %Y'),
        'is_live': session == 'LIVE',
    })


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    if path and os.path.exists(os.path.join(build_dir, path)):
        return send_from_directory(build_dir, path)
    index_path = os.path.join(build_dir, 'index.html')
    if os.path.exists(index_path):
        return send_from_directory(build_dir, 'index.html')
    return jsonify({'error': 'Frontend build not found'}), 404


if __name__ == '__main__':
    print("🪨 Grey Rock Strategy API starting on http://0.0.0.0:5000")
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000, threads=8)
    except ImportError:
        app.run(debug=False, port=5000, threaded=True)