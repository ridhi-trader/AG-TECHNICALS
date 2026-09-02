"""
AG TRADEBRIDGE — Pure Python Bridge Module
==========================================
Drop-in replacement for the compiled .so bridge.
Works on Python 3.10+ (including 3.14). No external deps beyond FastAPI/httpx.

INSTALL:
  from bridge_module import bridge_router, add_strategy, add_license, subscribe
  app.include_router(bridge_router)

SIGNAL FLOW:
  TradingView → POST /master/{sid}  →  queue signal → PENDING[lid]
  MT5 EA      → GET  /api/pull/{lid}  →  consume signal (plain text)
"""

import time, threading, datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse, Response

bridge_router = APIRouter()
_lock = threading.Lock()

# ── IN-MEMORY STORES ──────────────────────────────────────────────────────────
STRATEGIES = {}
# sid → {"secret": str, "name": str, "active": bool}

LICENSES = {}
# lid → {"expires": float (unix), "account": str|None, "paused": bool, "subs": [sid,...], "ea_ver": str|None, "last_config_push": float}

PENDING = {}
# lid → [signal_str, ...]   (FIFO queue per license)

_ea_file_bytes = None
_ea_filename = "AG_Bridge_EA.ex5"

# ── MANAGEMENT FUNCTIONS ──────────────────────────────────────────────────────

def add_strategy(sid: str, secret: str, name: str = ""):
    with _lock:
        STRATEGIES[sid] = {"secret": secret, "name": name or sid, "active": True}

def remove_strategy(sid: str):
    with _lock:
        if sid in STRATEGIES:
            STRATEGIES[sid]["active"] = False

def add_license(lid: str, days: int = 365, sid: str = None):
    with _lock:
        LICENSES[lid] = {
            "expires": time.time() + days * 86400,
            "account": None,
            "paused": False,
            "subs": [sid] if sid else [],
            "ea_ver": None,
            "last_config_push": 0.0,
        }
        PENDING.setdefault(lid, [])

def extend_license(lid: str, days: int):
    with _lock:
        if lid in LICENSES:
            LICENSES[lid]["expires"] += days * 86400

def subscribe(lid: str, sid: str):
    with _lock:
        if lid in LICENSES and sid not in LICENSES[lid]["subs"]:
            LICENSES[lid]["subs"].append(sid)

def unsubscribe(lid: str, sid: str):
    with _lock:
        if lid in LICENSES:
            LICENSES[lid]["subs"] = [s for s in LICENSES[lid]["subs"] if s != sid]

def pause(lid: str, paused: bool = True):
    with _lock:
        if lid in LICENSES:
            LICENSES[lid]["paused"] = paused

def set_ea_file(path_or_bytes, filename: str = "AG_Bridge_EA.ex5"):
    global _ea_file_bytes, _ea_filename
    if isinstance(path_or_bytes, (bytes, bytearray)):
        _ea_file_bytes = bytes(path_or_bytes)
    else:
        with open(path_or_bytes, "rb") as f:
            _ea_file_bytes = f.read()
    _ea_filename = filename

# ── SIGNAL VALIDATION ─────────────────────────────────────────────────────────

def _build_signal(body: dict):
    """Validate + format signal string. Returns (signal_str, error_reason)."""
    action = str(body.get("action", "")).strip().lower()
    if action not in ("buy", "sell"):
        return None, f"bad action '{action}'"

    symbol = str(body.get("symbol", "")).strip().upper()
    if not symbol:
        return None, "empty symbol"

    try:
        price = float(body.get("price", 0))
        if price <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return None, "invalid price"

    # swing_price — accept swing_low / swing_high / swing_price
    sw = body.get("swing_price") or body.get("swing_low") or body.get("swing_high")
    sl = ""
    if sw is not None:
        try:
            swing = float(sw)
            # Validate swing side
            if action == "buy" and swing >= price:
                return None, f"swing_price {swing} must be BELOW entry {price} for BUY"
            if action == "sell" and swing <= price:
                return None, f"swing_price {swing} must be ABOVE entry {price} for SELL"
            # Too close — drop SL (let EA use its own)
            pct_diff = abs(price - swing) / price
            if pct_diff >= 0.0002:  # >= 0.02%
                sl = str(swing)
        except (ValueError, TypeError):
            pass  # ignore bad swing

    tp = str(body.get("tp", "")).strip()
    lot = str(body.get("lot", "")).strip()

    # Format: action,symbol,price,sl,tp,lot
    signal = f"{action},{symbol},{price},{sl},{tp},{lot}"
    return signal, None

# ── WEBHOOK ENDPOINT ──────────────────────────────────────────────────────────

@bridge_router.post("/master/{sid}")
async def webhook(sid: str, request: Request):
    strat = STRATEGIES.get(sid)
    if not strat or not strat["active"]:
        return JSONResponse({"status": "unknown_strategy"})

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "bad_json"})

    secret = str(body.get("secret", ""))
    if secret != strat["secret"]:
        return JSONResponse({"status": "unauthorized"})

    signal, err = _build_signal(body)
    if err:
        return JSONResponse({"status": "rejected", "reason": err})

    # Queue to all eligible licenses
    delivered = 0
    now = time.time()
    with _lock:
        for lid, lic in LICENSES.items():
            if lic["expires"] < now:
                continue
            if lic["paused"]:
                continue
            if sid not in lic["subs"]:
                continue
            PENDING.setdefault(lid, []).append(signal)
            delivered += 1

    return JSONResponse({
        "status": "broadcast",
        "strategy": strat["name"],
        "delivered_to": delivered,
    })

# ── EA POLL ENDPOINT ──────────────────────────────────────────────────────────

@bridge_router.get("/api/pull/{lid}")
async def pull(lid: str, request: Request):
    params = request.query_params
    account = params.get("account", "").strip()
    ea_ver = params.get("v", "").strip()

    if lid not in LICENSES:
        return PlainTextResponse("ERROR|Invalid License ID")

    if not account:
        return PlainTextResponse("ERROR|No account number sent")

    now = time.time()
    with _lock:
        lic = LICENSES[lid]

        # Expiry check
        if lic["expires"] < now:
            return PlainTextResponse("ERROR|Subscription expired. Please renew.")

        # Account lock
        if lic["account"] is None:
            lic["account"] = account
            lic["ea_ver"] = ea_ver
            # Return OK but still check for pending signals below
            pending = PENDING.get(lid, [])
            if pending:
                sig = pending.pop(0)
                return PlainTextResponse(sig)
            return PlainTextResponse(f"OK|License activated on this account")

        if lic["account"] != account:
            return PlainTextResponse(f"ERROR|License is locked to account {lic['account']}. Contact support.")

        # Update EA ver
        if ea_ver:
            lic["ea_ver"] = ea_ver

        # Paused
        if lic["paused"]:
            return PlainTextResponse("")

        # Signal pending?
        pending = PENDING.get(lid, [])
        if pending:
            sig = pending.pop(0)
            return PlainTextResponse(sig)

        # CONFIG push for EA v1.22+
        try:
            ver_num = float(ea_ver) if ea_ver else 0
        except ValueError:
            ver_num = 0

        if ver_num >= 1.22 and (now - lic.get("last_config_push", 0)) >= 60:
            lic["last_config_push"] = now
            return PlainTextResponse("CONFIG|manual=0")

    return PlainTextResponse("")

# ── BRIDGE STATUS ─────────────────────────────────────────────────────────────

@bridge_router.get("/api/bridge/status")
async def bridge_status():
    now = time.time()
    with _lock:
        active_licenses = sum(1 for l in LICENSES.values() if l["expires"] > now)
        total_pending = sum(len(q) for q in PENDING.values())
    return JSONResponse({
        "status": "ok",
        "mode": "python",
        "strategies": len(STRATEGIES),
        "active_licenses": active_licenses,
        "pending_signals": total_pending,
    })

# ── EA DOWNLOAD ───────────────────────────────────────────────────────────────

@bridge_router.get("/download/ea")
async def download_ea():
    if not _ea_file_bytes:
        return PlainTextResponse("EA file not configured", status_code=404)
    return Response(
        content=_ea_file_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{_ea_filename}"'},
    )

# ── TB / DASHBOARD PAGES ──────────────────────────────────────────────────────

TB_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AG TradeBridge — TradingView Setup</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08070a;color:#f4efe6;font-family:'Inter',sans-serif;min-height:100vh;padding:40px 20px}
.wrap{max-width:760px;margin:0 auto}
h1{font-size:28px;font-weight:800;color:#f7c04a;margin-bottom:8px}
.sub{color:#9d95a6;margin-bottom:40px;font-size:15px}
.card{background:#141119;border:1px solid #2a2536;border-radius:14px;padding:28px;margin-bottom:24px}
.card h2{font-size:16px;font-weight:700;color:#f7c04a;margin-bottom:16px;text-transform:uppercase;letter-spacing:1px}
code,pre{background:#0d0c11;border:1px solid #2a2536;border-radius:8px;padding:4px 8px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#e8c766}
pre{padding:16px;display:block;white-space:pre-wrap;line-height:1.7}
.step{display:flex;gap:16px;margin-bottom:20px;align-items:flex-start}
.step-num{background:#f7c04a;color:#000;font-weight:800;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:13px}
.step-body{flex:1}
.step-body h3{font-size:14px;font-weight:700;color:#fff;margin-bottom:8px}
.step-body p{font-size:13px;color:#9d95a6;line-height:1.6}
label{font-size:13px;color:#9d95a6;display:block;margin-bottom:6px}
input{width:100%;background:#0d0c11;border:1px solid #2a2536;border-radius:8px;padding:10px 14px;color:#f4efe6;font-size:14px;outline:none}
input:focus{border-color:#f7c04a}
</style>
</head>
<body>
<div class="wrap">
  <h1>⚡ AG TradeBridge — TradingView Setup</h1>
  <p class="sub">Connect your TradingView alerts to MT5 in 3 steps</p>

  <div class="card">
    <h2>Step 1 — Add Your Strategy Details</h2>
    <div style="display:grid;gap:16px">
      <div><label>Your Strategy ID (ask support)</label><input id="sid" placeholder="e.g. gold-scalper"></div>
      <div><label>Your Strategy Secret (ask support)</label><input id="sec" type="password" placeholder="e.g. ag-secret-2026"></div>
      <div><label>Your Symbol</label><input id="sym" value="XAUUSD"></div>
    </div>
  </div>

  <div class="card">
    <h2>Step 2 — TradingView Alert Setup</h2>
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-body">
        <h3>Open your indicator → Create Alert</h3>
        <p>In TradingView, right-click your chart or indicator → "Add Alert"</p>
      </div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-body">
        <h3>Set Webhook URL</h3>
        <p style="margin-bottom:8px">In Alert → Notifications → Webhook URL:</p>
        <pre id="wh_url">https://ag-technicals.onrender.com/master/YOUR-SID</pre>
      </div>
    </div>
    <div class="step">
      <div class="step-num">3</div>
      <div class="step-body">
        <h3>Alert Message (JSON body)</h3>
        <p style="margin-bottom:8px">Paste this in the "Message" field:</p>
        <pre id="tv_body">{
  "secret": "YOUR-SECRET",
  "action": "buy",
  "symbol": "XAUUSD",
  "price": {{close}},
  "swing_price": 0
}</pre>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Step 3 — MT5 EA Setup</h2>
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-body">
        <h3>Allow WebRequest in MT5</h3>
        <p>Tools → Options → Expert Advisors → Allow WebRequest<br>Add URL: <code>https://ag-assistant-api.onrender.com</code></p>
      </div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-body">
        <h3>EA Inputs</h3>
        <p>License ID: your assigned LIC-xxxx<br>Server URL: <code>https://ag-assistant-api.onrender.com</code></p>
      </div>
    </div>
  </div>
</div>
<script>
function upd(){
  var sid=document.getElementById('sid').value||'YOUR-SID';
  var sec=document.getElementById('sec').value||'YOUR-SECRET';
  var sym=document.getElementById('sym').value||'XAUUSD';
  document.getElementById('wh_url').textContent='https://ag-assistant-api.onrender.com/master/'+sid;
  document.getElementById('tv_body').textContent=JSON.stringify({secret:sec,action:'buy',symbol:sym,price:'{{close}}',swing_price:0},null,2).replace('"{{close}}"','{{close}}');
}
['sid','sec','sym'].forEach(function(id){document.getElementById(id).addEventListener('input',upd)});
</script>
</body>
</html>"""

DASH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AG Bridge Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08070a;color:#f4efe6;font-family:'Inter',sans-serif;min-height:100vh;padding:40px 20px}
.wrap{max-width:700px;margin:0 auto}
h1{font-size:26px;font-weight:800;color:#f7c04a;margin-bottom:6px}
.sub{color:#9d95a6;margin-bottom:36px;font-size:14px}
.card{background:#141119;border:1px solid #2a2536;border-radius:14px;padding:24px;margin-bottom:20px}
.row{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #1c1824}
.row:last-child{border-bottom:none}
.label{font-size:13px;color:#9d95a6}
.val{font-size:14px;font-weight:700;color:#fff}
.badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
.green{background:rgba(74,222,128,.15);color:#4ade80}
.red{background:rgba(242,109,109,.15);color:#f26d6d}
.gold{background:rgba(247,192,74,.15);color:#f7c04a}
code{background:#0d0c11;border:1px solid #2a2536;border-radius:6px;padding:3px 8px;font-size:12px;color:#e8c766;font-family:monospace}
</style>
</head>
<body>
<div class="wrap">
  <h1>📡 AG Bridge Dashboard</h1>
  <p class="sub">Real-time bridge status</p>
  <div class="card" id="status-card">
    <div class="row"><span class="label">Bridge Status</span><span class="badge green" id="st-mode">Loading...</span></div>
    <div class="row"><span class="label">Active Strategies</span><span class="val" id="st-strat">—</span></div>
    <div class="row"><span class="label">Active Licenses</span><span class="val" id="st-lic">—</span></div>
    <div class="row"><span class="label">Pending Signals</span><span class="val" id="st-pending">—</span></div>
  </div>
</div>
<script>
async function refresh(){
  try{
    var r=await fetch('/api/bridge/status');
    var d=await r.json();
    document.getElementById('st-mode').textContent=d.mode||'ok';
    document.getElementById('st-strat').textContent=d.strategies||0;
    document.getElementById('st-lic').textContent=d.active_licenses||0;
    document.getElementById('st-pending').textContent=d.pending_signals||0;
  }catch(e){document.getElementById('st-mode').textContent='Offline';}
}
refresh();
setInterval(refresh,10000);
</script>
</body>
</html>"""
