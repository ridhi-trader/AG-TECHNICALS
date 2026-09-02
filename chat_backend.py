"""
AG Assistant Chat Backend
FastAPI proxy → Anthropic API + Market Data + File Upload
"""
import os, httpx, json, time, shutil, uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

from bridge_module import bridge_router, add_strategy, add_license
app.include_router(bridge_router)

from video_module import video_router, add_video
app.include_router(video_router)

# EA Demo Videos
import os as _os
_base = _os.path.dirname(_os.path.abspath(__file__))

# Upload directory — persists within Render instance (ephemeral on restart)
UPLOAD_DIR = _os.path.join(_base, "uploaded_files")
_os.makedirs(UPLOAD_DIR, exist_ok=True)

for _vid_id, _vid_file in [
    ("smc_ea",       "SMC_EA_demo.mp4"),
    ("orderflow_ea", "AG_OrderFlow_EA_demo.mp4"),
    ("grid3_ea",     "AG_3LOGIC_GRID_EA_demo.mp4"),
    ("atr_ea",       "AG_ATR_GRID_EA_demo.mp4"),
    ("swing_ea",     "AG_SWING_EMA_RR_EA_demo.mp4"),
]:
    _path = _os.path.join(_base, _vid_file)
    if _os.path.exists(_path):
        add_video(_vid_id, _path)

add_strategy(sid="agbridge", secret="ag-bridge-secret-2026", name="AG TradeBridge")
add_license(lid="LIC-0001", days=365)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM = """You are AG Assistant — the official AI assistant for AG Technicals (ag-technicals.onrender.com).

AG Technicals is a professional trading analysis platform offering:

PRODUCTS:
1. TradingView Indicator — 3 custom Pine Script indicators: AG SMC, AG Order Flow, AG-ESB.
2. Algo (MT5) — Automated trading system for MetaTrader 5.
3. Bridge — TradingView → MT5 signal connector.
4. Education — Structured courses: Basic To Pro and SMC Complete Course.
5. Guide — Written trading playbooks.
6. Custom Strategy — Personalized trading strategy.
7. News — AG Intel live market dossiers.

CONTACT:
- Telegram: @agtechnical | https://t.me/agtechnical
- WhatsApp: +91 98765 43210 | https://wa.me/919876543210
- Instagram: @agtechnical | https://instagram.com/agtechnical

RULES:
- NEVER share passwords, admin details, admin.html URL, GitHub info, backend/internal details
- For pricing: say "contact us on WhatsApp or Telegram for pricing"
- Respond in same language as user (Hinglish, Hindi, or English)
- Keep answers concise (under 150 words) unless detail needed
- Not financial advice — educational and analytical content only"""

# ── MARKET DATA CACHE ──────────────────────────────────────────────────────────
_market_cache = {"data": None, "ts": 0}
CACHE_TTL = 3600

async def fetch_prices():
    prices = {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            syms = '["BTCUSDT","ETHUSDT","XAUUSDT","EURUSDT","GBPUSDT"]'
            r = await client.get(f"https://api.binance.com/api/v3/ticker/24hr?symbols={syms}")
            if r.status_code == 200:
                for item in r.json():
                    prices[item["symbol"]] = {
                        "price": float(item["lastPrice"]),
                        "chg": float(item["priceChangePercent"])
                    }
    except Exception:
        pass
    defaults = {
        "XAUUSDT": {"price": 2645.0, "chg": 0.3},
        "BTCUSDT": {"price": 68200.0, "chg": 1.2},
        "ETHUSDT": {"price": 3540.0, "chg": 2.1},
        "EURUSDT": {"price": 1.0842, "chg": 0.1},
        "GBPUSDT": {"price": 1.2735, "chg": 0.2},
    }
    for k, v in defaults.items():
        if k not in prices:
            prices[k] = v
    return prices

async def fetch_news_ai(prices: dict):
    if not ANTHROPIC_KEY:
        return None
    price_str = ", ".join([
        f"Gold ${prices.get('XAUUSDT',{}).get('price',2645):.0f} ({prices.get('XAUUSDT',{}).get('chg',0):+.1f}%)",
        f"BTC ${prices.get('BTCUSDT',{}).get('price',68000):.0f} ({prices.get('BTCUSDT',{}).get('chg',0):+.1f}%)",
        f"ETH ${prices.get('ETHUSDT',{}).get('price',3500):.0f} ({prices.get('ETHUSDT',{}).get('chg',0):+.1f}%)",
        f"EUR/USD {prices.get('EURUSDT',{}).get('price',1.084):.4f} ({prices.get('EURUSDT',{}).get('chg',0):+.1f}%)",
        f"GBP/USD {prices.get('GBPUSDT',{}).get('price',1.273):.4f} ({prices.get('GBPUSDT',{}).get('chg',0):+.1f}%)",
    ])
    prompt = f"""Current market prices: {price_str}
Today: {time.strftime('%B %d, %Y')}.
Return ONLY valid JSON:
{{"latest":[{{"title":"headline","time":"Xh ago · Forex","dir":"up"}},{{"title":"headline","time":"Xh ago · Crypto","dir":"up"}},{{"title":"headline","time":"Xh ago · Commodities","dir":"dn"}},{{"title":"headline","time":"Xh ago · Indices","dir":"up"}}],"analysis":[{{"title":"EUR/USD analysis","time":"Xh ago · AG Analysis","dir":"up"}},{{"title":"Gold analysis","time":"Xh ago · AG Analysis","dir":"dn"}},{{"title":"GBP/USD analysis","time":"Xh ago · AG Analysis","dir":"up"}},{{"title":"BTC analysis","time":"Xh ago · AG Analysis","dir":"up"}}],"sentiment":[{{"label":"Forex","pct":65,"dir":"up"}},{{"label":"Crypto","pct":72,"dir":"up"}},{{"label":"Gold","pct":55,"dir":"up"}},{{"label":"Indices","pct":60,"dir":"up"}},{{"label":"Crude Oil","pct":45,"dir":"neutral"}}],"ticker_extra":["macro event note"]}}
Use actual prices. Make headlines specific and realistic."""
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]}
            )
        text = r.json().get("content", [{}])[0].get("text", "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"): text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return None

@app.get("/api/market-data")
async def market_data():
    global _market_cache
    now = time.time()
    cache_ttl = _market_cache.get("ttl", CACHE_TTL)
    if _market_cache["data"] and (now - _market_cache["ts"]) < cache_ttl:
        return _market_cache["data"]
    prices = await fetch_prices()
    news_ai = await fetch_news_ai(prices)
    def arrow(chg): return "▲" if chg >= 0 else "▼"
    def fmt(sym, label, d=2):
        p = prices.get(sym, {})
        return f"{label}  {p.get('price',0):.{d}f}  {arrow(p.get('chg',0))} {abs(p.get('chg',0)):.2f}%"
    ticker = [
        {"text": fmt("XAUUSDT", "XAU/USD", 2), "type": "gold"},
        {"text": fmt("BTCUSDT", "BTCUSD", 0), "type": "default"},
        {"text": fmt("ETHUSDT", "ETHUSD", 0), "type": "default"},
        {"text": fmt("EURUSDT", "EUR/USD", 4), "type": "default"},
        {"text": fmt("GBPUSDT", "GBP/USD", 4), "type": "default"},
        {"text": "COT · Managed Money tracking institutional flow", "type": "cot"},
        {"text": "AG INTEL · Gold Dossier — Read ↗", "type": "gold"},
    ]
    if news_ai and news_ai.get("ticker_extra"):
        for ev in news_ai["ticker_extra"][:2]:
            ticker.insert(2, {"text": ev, "type": "jh"})
    result = {
        "ticker": ticker,
        "news": news_ai or {},
        "prices": {
            "gold": prices.get("XAUUSDT", {}),
            "btc": prices.get("BTCUSDT", {}),
            "eth": prices.get("ETHUSDT", {}),
            "eurusd": prices.get("EURUSDT", {}),
            "gbpusd": prices.get("GBPUSDT", {}),
        },
        "cached_at": int(now),
    }
    # Short TTL if news AI failed — retry sooner
    has_news = bool(news_ai and news_ai.get("latest"))
    _market_cache = {"data": result, "ts": now, "ttl": CACHE_TTL if has_news else 600}
    return result

# ── FILE UPLOAD SYSTEM ─────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), category: str = Form(default="general")):
    """Upload any file — returns public URL to use in admin panel"""
    try:
        # Sanitize filename
        orig_name = file.filename or "upload"
        ext = orig_name.rsplit(".", 1)[-1].lower() if "." in orig_name else "bin"
        safe_name = orig_name.replace(" ", "_").replace("..", "").replace("/", "")
        # Add short UUID prefix to avoid collisions
        file_id = uuid.uuid4().hex[:8]
        final_name = f"{file_id}_{safe_name}"
        save_path = os.path.join(UPLOAD_DIR, final_name)
        
        # Stream to disk (handles large files)
        with open(save_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                f.write(chunk)
        
        size = os.path.getsize(save_path)
        url = f"https://ag-assistant-api.onrender.com/uploads/{final_name}"
        
        return {
            "ok": True,
            "url": url,
            "filename": orig_name,
            "size": size,
            "file_id": final_name,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/uploads/{filename}")
async def serve_upload(filename: str):
    """Serve uploaded files"""
    # Security: no path traversal
    filename = os.path.basename(filename)
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Not found"}, status_code=404)
    return FileResponse(path)

@app.get("/api/uploads/list")
async def list_uploads():
    """List all uploaded files"""
    files = []
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            fpath = os.path.join(UPLOAD_DIR, fname)
            size = os.path.getsize(fpath)
            files.append({
                "name": fname,
                "url": f"https://ag-assistant-api.onrender.com/uploads/{fname}",
                "size": size,
            })
    return {"files": sorted(files, key=lambda x: x["name"])}

@app.delete("/api/uploads/{filename}")
async def delete_upload(filename: str):
    filename = os.path.basename(filename)
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return {"ok": True}
    return {"ok": False, "error": "Not found"}

class Msg(BaseModel):
    role: str
    content: str

class ChatReq(BaseModel):
    messages: List[Msg]

@app.post("/api/chat")
async def chat(req: ChatReq):
    if not ANTHROPIC_KEY:
        return {"reply": "Service unavailable. Please contact us on WhatsApp or Telegram."}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 500, "system": SYSTEM, "messages": [m.dict() for m in req.messages]}
        )
    reply = r.json().get("content", [{}])[0].get("text", "Sorry, please try again.")
    return {"reply": reply}

@app.get("/api/cache/clear")
async def clear_cache():
    """Force refresh market data cache"""
    global _market_cache
    _market_cache = {"data": None, "ts": 0}
    return {"ok": True, "msg": "Cache cleared — next request will fetch fresh data"}

@app.get("/")
@app.head("/")
def root():
    return {"status": "AG Assistant API running"}
