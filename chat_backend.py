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
FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")

import xml.etree.ElementTree as ET
import hashlib as _hashlib

RSS_FEEDS = [
    {"url": "https://www.fxstreet.com/rss/news", "source": "FXStreet", "category": "Forex"},
    {"url": "https://www.forexfactory.com/ff_calendar.xml", "source": "ForexFactory", "category": "Forex"},
    {"url": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=XAUUSD%3DX&region=US&lang=en-US", "source": "Yahoo Finance", "category": "Gold"},
    {"url": "https://cointelegraph.com/rss", "source": "CoinTelegraph", "category": "Crypto"},
    {"url": "https://www.investing.com/rss/news_25.rss", "source": "Investing.com", "category": "Forex"},
    {"url": "https://www.investing.com/rss/news_301.rss", "source": "Investing.com", "category": "Crypto"},
    {"url": "https://www.investing.com/rss/news_1.rss", "source": "Investing.com", "category": "Gold"},
    # Indian Markets
    {"url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "source": "Economic Times", "category": "Indices"},
    {"url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms", "source": "Economic Times", "category": "Indices"},
    {"url": "https://www.moneycontrol.com/rss/marketreports.xml", "source": "Moneycontrol", "category": "Indices"},
    {"url": "https://www.livemint.com/rss/markets", "source": "LiveMint", "category": "Indices"},
    {"url": "https://economictimes.indiatimes.com/markets/commodities/rssfeeds/2146791.cms", "source": "Economic Times", "category": "Gold"},
]

async def fetch_rss_news():
    all_news = []
    try:
        async with httpx.AsyncClient(timeout=8, headers={"User-Agent": "Mozilla/5.0 (AG Technicals News Bot)"}) as client:
            for feed in RSS_FEEDS:
                try:
                    r = await client.get(feed["url"])
                    if r.status_code != 200:
                        continue
                    root = ET.fromstring(r.text)
                    ns = {"media": "http://search.yahoo.com/mrss/"}
                    for item in root.findall(".//item")[:6]:
                        title = item.findtext("title", "").strip()
                        link = item.findtext("link", "").strip()
                        import re as _re
                        raw_desc = item.findtext("description", "").strip()
                        desc = _re.sub(r'<[^>]+>', '', raw_desc).strip()[:600]
                        pub = item.findtext("pubDate", "")
                        # Try to get image
                        img = ""
                        media = item.find("media:thumbnail", ns) or item.find("media:content", ns)
                        if media is not None:
                            img = media.get("url", "")
                        if not img:
                            # Try enclosure
                            enc = item.find("enclosure")
                            if enc is not None and "image" in enc.get("type", ""):
                                img = enc.get("url", "")
                        # Parse time
                        import email.utils as _eu
                        ts = 0
                        try:
                            ts = int(_eu.parsedate_to_datetime(pub).timestamp()) if pub else 0
                        except: pass
                        if title and link:
                            all_news.append({
                                "title": title,
                                "summary": desc,
                                "url": link,
                                "image": img,
                                "source": feed["source"],
                                "category": feed["category"],
                                "time_unix": ts,
                                "badge": "LIVE",
                            })
                except Exception as fe:
                    print(f"RSS feed error {feed['source']}: {fe}")
                    continue
    except Exception as e:
        print(f"RSS fetch error: {e}")
    all_news.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
    return all_news[:40]

async def fetch_finnhub_news():
    if not FINNHUB_KEY:
        return []
    try:
        all_news = []
        async with httpx.AsyncClient(timeout=10) as client:
            for cat in ["forex", "crypto", "general"]:
                r = await client.get(f"https://finnhub.io/api/v1/news?category={cat}&token={FINNHUB_KEY}")
                if r.status_code == 200:
                    for item in r.json()[:5]:
                        all_news.append({
                            "title": item.get("headline", ""),
                            "summary": item.get("summary", "")[:200],
                            "url": item.get("url", ""),
                            "image": item.get("image", ""),
                            "source": item.get("source", ""),
                            "time_unix": item.get("datetime", 0),
                            "category": cat.title(),
                            "badge": "LIVE",
                        })
        all_news.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
        return all_news[:20]
    except Exception as e:
        print(f"Finnhub error: {e}")
        return []

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
CACHE_TTL = 300  # 5 min cache for news freshness

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
    prompt = f"""You are a financial news writer. Today: {time.strftime('%B %d, %Y')}. Prices: {price_str}.
Generate 12 realistic trading news headlines. Return ONLY valid JSON:
{{"articles":[
  {{"title":"Gold headline using actual price","category":"Gold","dir":"up","summary":"2-sentence context","time":"1h ago"}},
  {{"title":"Forex EUR/USD headline","category":"Forex","dir":"dn","summary":"context","time":"2h ago"}},
  {{"title":"BTC crypto headline","category":"Crypto","dir":"up","summary":"context","time":"1h ago"}},
  {{"title":"Indices NAS/SPX headline","category":"Indices","dir":"up","summary":"context","time":"3h ago"}},
  {{"title":"Fed/Macro headline","category":"Macro","dir":"neutral","summary":"context","time":"4h ago"}},
  {{"title":"Gold analysis","category":"Analysis","dir":"up","summary":"context","time":"2h ago"}},
  {{"title":"GBP/USD headline","category":"Forex","dir":"up","summary":"context","time":"3h ago"}},
  {{"title":"ETH headline","category":"Crypto","dir":"up","summary":"context","time":"5h ago"}},
  {{"title":"Oil/commodities","category":"Commodities","dir":"dn","summary":"context","time":"4h ago"}},
  {{"title":"DXY dollar strength","category":"Forex","dir":"up","summary":"context","time":"6h ago"}},
  {{"title":"COT institutional positioning","category":"Analysis","dir":"up","summary":"context","time":"7h ago"}},
  {{"title":"JPY/USD headline","category":"Forex","dir":"dn","summary":"context","time":"8h ago"}}
],
"sentiment":[
  {{"label":"Gold","pct":65,"dir":"up"}},{{"label":"Forex","pct":58,"dir":"up"}},
  {{"label":"Crypto","pct":72,"dir":"up"}},{{"label":"Indices","pct":55,"dir":"up"}},
  {{"label":"Crude Oil","pct":40,"dir":"dn"}}
],"ticker_extra":["macro event or central bank note"]}}
Use actual prices. dir: up/dn/neutral."""
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
        data = json.loads(text.strip())
        arts = data.get("articles", [])
        data["latest"] = [{"title":a["title"],"time":a["time"]+" · "+a["category"],"dir":a["dir"]} for a in arts[:4]]
        data["analysis"] = [{"title":a["title"],"time":a["time"]+" · AG Analysis","dir":a["dir"]} for a in arts[4:8]]
        return data
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
                chunk = await file.read(4 * 1024 * 1024)  # 4MB chunks
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

@app.get("/api/news")
async def get_news(category: str = "", search: str = ""):
    prices = await fetch_prices()
    finnhub = await fetch_finnhub_news()
    rss = await fetch_rss_news()
    ai = await fetch_news_ai(prices)

    articles = []
    # RSS news first (real, with covers)
    for item in rss:
        t_diff = int((time.time() - item.get("time_unix", time.time())) / 3600)
        articles.append({
            "title": item["title"], "summary": item.get("summary",""),
            "category": item.get("category","Market"), "source": item.get("source",""),
            "url": item.get("url",""), "image": item.get("image",""),
            "dir":"up", "real": True, "badge": "LIVE",
            "time": (str(t_diff)+"h ago") if t_diff < 24 else (str(t_diff//24)+"d ago"),
        })
    for item in finnhub:
        articles.append({
            "title": item["title"], "summary": item.get("summary",""),
            "category": item.get("category","Market"), "source": item.get("source",""),
            "url": item.get("url",""), "image": item.get("image",""),
            "dir":"up", "real": True, "badge": "LIVE",
            "time": str(int((time.time() - item.get("time_unix",time.time()))/3600))+"h ago",
        })
    if ai and ai.get("articles"):
        for a in ai["articles"]:
            articles.append({
                "title": a.get("title",""), "summary": a.get("summary",""),
                "category": a.get("category","Market"), "source":"AG Technicals",
                "url":"", "dir": a.get("dir","up"), "real": False,
                "time": a.get("time",""),
            })
    if category and category != "All":
        articles = [a for a in articles if a["category"].lower()==category.lower()]
    if search:
        sl=search.lower()
        articles = [a for a in articles if sl in a["title"].lower() or sl in a.get("summary","").lower()]
    return {
        "articles": articles,
        "sentiment": (ai or {}).get("sentiment",[
            {"label":"Gold","pct":60,"dir":"up"},{"label":"Forex","pct":55,"dir":"up"},
            {"label":"Crypto","pct":65,"dir":"up"},{"label":"Indices","pct":50,"dir":"up"},
            {"label":"Crude Oil","pct":40,"dir":"dn"},
        ]),
        "prices": {"gold":prices.get("XAUUSDT",{}),"btc":prices.get("BTCUSDT",{}),"eurusd":prices.get("EURUSDT",{})},
        "total": len(articles), "has_live": len(finnhub)>0, "updated": int(time.time()),
    }

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

# ── USER AUTH SYSTEM ───────────────────────────────────────────────────────────
import asyncpg, hashlib, secrets, smtplib, ssl
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from fastapi import HTTPException
from fastapi.responses import JSONResponse

DB_URL = os.environ.get("DATABASE_URL", "")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")  # App Password
SITE_URL = "https://ag-technicals.onrender.com"

_db_pool = None

async def get_db():
    global _db_pool
    if not _db_pool and DB_URL:
        try:
            _db_pool = await asyncpg.create_pool(DB_URL, ssl='require', min_size=1, max_size=5)
            await init_db()
        except Exception as e:
            print(f"DB connection failed: {e}")
    return _db_pool

async def init_db():
    pool = _db_pool
    if not pool: return
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ag_users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                products TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW(),
                verified BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS ag_otps (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                otp TEXT NOT NULL,
                purpose TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE
            );
            CREATE TABLE IF NOT EXISTS bridge_licenses (
                lid TEXT PRIMARY KEY,
                secret TEXT NOT NULL,
                user_email TEXT,
                account TEXT,
                active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        # Load licenses from DB into bridge_module
        rows = await conn.fetch("SELECT lid, secret, user_email, account, active, expires_at FROM bridge_licenses WHERE active=TRUE")
        for row in rows:
            days_left = max(1, int((row['expires_at'] - __import__('datetime').datetime.utcnow()).total_seconds() / 86400)) if row['expires_at'] else 365
            add_license(row['lid'], days=days_left)
            add_strategy(sid=row['lid'], secret=row['secret'], name=f"Bridge-{row['lid']}")

def hash_pass(pw): return hashlib.sha256(pw.encode()).hexdigest()
def gen_otp(): return str(secrets.randbelow(900000) + 100000)

def send_email(to_email, subject, body):
    if not GMAIL_USER or not GMAIL_PASS:
        print(f"EMAIL (no creds): To={to_email} Subject={subject}")
        return True
    try:
        msg = MIMEText(body, 'html')
        msg['Subject'] = subject
        msg['From'] = f"AG Technicals <{GMAIL_USER}>"
        msg['To'] = to_email
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ctx) as s:
            s.login(GMAIL_USER, GMAIL_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def otp_email_html(otp, purpose):
    return f"""
    <div style="background:#0d0d0f;padding:40px;font-family:Inter,sans-serif;color:#fff;max-width:500px;margin:0 auto;border-radius:16px;">
      <div style="font-size:24px;font-weight:800;color:#e8b84b;margin-bottom:8px;">AG Technicals</div>
      <div style="font-size:14px;color:#a0a0b8;margin-bottom:32px;">{'Verify your email' if purpose=='signup' else 'Password Reset OTP'}</div>
      <div style="background:#141318;border:1px solid #2a2736;border-radius:12px;padding:24px;text-align:center;margin-bottom:24px;">
        <div style="font-size:13px;color:#a0a0b8;margin-bottom:12px;">Your OTP Code</div>
        <div style="font-size:40px;font-weight:800;color:#e8b84b;letter-spacing:8px;">{otp}</div>
        <div style="font-size:12px;color:#a0a0b8;margin-top:12px;">Valid for 10 minutes</div>
      </div>
      <div style="font-size:12px;color:#7e7a90;">If you did not request this, ignore this email.</div>
    </div>"""

class SignupReq(BaseModel):
    username: str
    email: str
    password: str

class OtpReq(BaseModel):
    email: str
    otp: str

class LoginReq(BaseModel):
    email: str
    password: str

class ForgotReq(BaseModel):
    email: str

class ResetReq(BaseModel):
    email: str
    otp: str
    new_password: str

@app.on_event("startup")
async def startup():
    await get_db()

@app.post("/api/auth/signup")
async def signup(req: SignupReq):
    pool = await get_db()
    if not pool:
        return JSONResponse({"ok": False, "error": "Database unavailable"})
    if len(req.password) < 6:
        return JSONResponse({"ok": False, "error": "Password must be at least 6 characters"})
    if len(req.username) < 3:
        return JSONResponse({"ok": False, "error": "Username must be at least 3 characters"})
    try:
        async with pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT id FROM ag_users WHERE email=$1 OR username=$2", req.email, req.username)
            if existing:
                return JSONResponse({"ok": False, "error": "Email or username already registered"})
            await conn.execute("INSERT INTO ag_users (username, email, password_hash) VALUES ($1,$2,$3)",
                req.username, req.email, hash_pass(req.password))
            # Delete old OTPs
            await conn.execute("DELETE FROM ag_otps WHERE email=$1 AND purpose='signup'", req.email)
            otp = gen_otp()
            expires = datetime.utcnow() + timedelta(minutes=10)
            await conn.execute("INSERT INTO ag_otps (email,otp,purpose,expires_at) VALUES ($1,$2,'signup',$3)", req.email, otp, expires)
            send_email(req.email, "AG Technicals — Verify Your Email", otp_email_html(otp, 'signup'))
            return JSONResponse({"ok": True, "msg": "OTP sent to your email"})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})

@app.post("/api/auth/verify-otp")
async def verify_otp(req: OtpReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM ag_otps WHERE email=$1 AND otp=$2 AND purpose='signup' AND used=FALSE AND expires_at > NOW()", req.email, req.otp)
        if not row: return JSONResponse({"ok": False, "error": "Invalid or expired OTP"})
        await conn.execute("UPDATE ag_otps SET used=TRUE WHERE id=$1", row['id'])
        await conn.execute("UPDATE ag_users SET verified=TRUE WHERE email=$1", req.email)
        user = await conn.fetchrow("SELECT id,username,email,products FROM ag_users WHERE email=$1", req.email)
        return JSONResponse({"ok": True, "user": {"id": user['id'], "username": user['username'], "email": user['email'], "products": user['products']}})

@app.post("/api/auth/login")
async def login(req: LoginReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM ag_users WHERE email=$1 AND password_hash=$2 AND verified=TRUE", req.email, hash_pass(req.password))
        if not user: return JSONResponse({"ok": False, "error": "Invalid credentials or email not verified"})
        return JSONResponse({"ok": True, "user": {"id": user['id'], "username": user['username'], "email": user['email'], "products": user['products']}})

@app.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id FROM ag_users WHERE email=$1", req.email)
        if not user: return JSONResponse({"ok": False, "error": "Email not found"})
        await conn.execute("DELETE FROM ag_otps WHERE email=$1 AND purpose='reset'", req.email)
        otp = gen_otp()
        expires = datetime.utcnow() + timedelta(minutes=10)
        await conn.execute("INSERT INTO ag_otps (email,otp,purpose,expires_at) VALUES ($1,$2,'reset',$3)", req.email, otp, expires)
        send_email(req.email, "AG Technicals — Password Reset OTP", otp_email_html(otp, 'reset'))
        return JSONResponse({"ok": True, "msg": "OTP sent to your email"})

@app.post("/api/auth/reset-password")
async def reset_password(req: ResetReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM ag_otps WHERE email=$1 AND otp=$2 AND purpose='reset' AND used=FALSE AND expires_at > NOW()", req.email, req.otp)
        if not row: return JSONResponse({"ok": False, "error": "Invalid or expired OTP"})
        if len(req.new_password) < 6: return JSONResponse({"ok": False, "error": "Password too short"})
        await conn.execute("UPDATE ag_otps SET used=TRUE WHERE id=$1", row['id'])
        await conn.execute("UPDATE ag_users SET password_hash=$1 WHERE email=$2", hash_pass(req.new_password), req.email)
        return JSONResponse({"ok": True, "msg": "Password reset successfully"})

@app.get("/api/auth/user/{user_id}")
async def get_user(user_id: int):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False})
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id,username,email,products,created_at FROM ag_users WHERE id=$1", user_id)
        if not user: return JSONResponse({"ok": False, "error": "User not found"})
        return JSONResponse({"ok": True, "user": {"id": user['id'], "username": user['username'], "email": user['email'], "products": user['products'], "joined": str(user['created_at'])[:10]}})

# Admin: assign products to user
class AssignReq(BaseModel):
    user_id: int
    products: str  # comma-separated product ids

@app.post("/api/admin/assign-products")
async def assign_products(req: AssignReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False})
    async with pool.acquire() as conn:
        await conn.execute("UPDATE ag_users SET products=$1 WHERE id=$2", req.products, req.user_id)
        return JSONResponse({"ok": True})

@app.get("/api/admin/users")
async def admin_users():
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "users": []})
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id,username,email,products,created_at,verified FROM ag_users ORDER BY created_at DESC")
        return JSONResponse({"ok": True, "users": [{"id":r['id'],"username":r['username'],"email":r['email'],"products":r['products'],"joined":str(r['created_at'])[:10],"verified":r['verified']} for r in rows]})

# ── BRIDGE LICENSE MANAGEMENT ─────────────────────────────────────────────────

class BridgeLicReq(BaseModel):
    user_email: str = ""
    days: int = 365

class BridgeAssignReq(BaseModel):
    lid: str
    account: str = ""

@app.post("/api/admin/bridge/create-license")
async def create_bridge_license(req: BridgeLicReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    import secrets as _sec, datetime as _dt
    lid = "LIC-" + _sec.token_hex(4).upper()
    secret = _sec.token_urlsafe(24)
    expires = _dt.datetime.utcnow() + _dt.timedelta(days=req.days)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO bridge_licenses (lid, secret, user_email, expires_at) VALUES ($1,$2,$3,$4)",
            lid, secret, req.user_email or None, expires
        )
    add_license(lid, days=req.days)
    add_strategy(sid=lid, secret=secret, name=f"Bridge-{lid}")
    return JSONResponse({"ok": True, "lid": lid, "secret": secret, "expires": str(expires.date()), "user_email": req.user_email})

@app.get("/api/admin/bridge/licenses")
async def list_bridge_licenses():
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "licenses": []})
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT lid, secret, user_email, account, active, expires_at, created_at FROM bridge_licenses ORDER BY created_at DESC")
        return JSONResponse({"ok": True, "licenses": [dict(r) for r in rows]})

@app.delete("/api/admin/bridge/license/{lid}")
async def delete_bridge_license(lid: str):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bridge_licenses SET active=FALSE WHERE lid=$1", lid)
    return JSONResponse({"ok": True})

@app.post("/api/admin/bridge/assign")
async def assign_bridge_account(req: BridgeAssignReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        await conn.execute("UPDATE bridge_licenses SET account=$1 WHERE lid=$2", req.account, req.lid)
    return JSONResponse({"ok": True})

@app.get("/api/news/article")
async def fetch_article(url: str):
    """Fetch and parse full article content for site-side reader"""
    if not url:
        return JSONResponse({"ok": False, "error": "No URL"})
    try:
        async with httpx.AsyncClient(timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return JSONResponse({"ok": False, "error": f"Status {r.status_code}"})
            html = r.text
        # Extract content using simple heuristics
        import re as _re
        # Remove scripts, styles, nav, footer, ads
        html = _re.sub(r'<script[^>]*>.*?</script>', '', html, flags=_re.DOTALL|_re.IGNORECASE)
        html = _re.sub(r'<style[^>]*>.*?</style>', '', html, flags=_re.DOTALL|_re.IGNORECASE)
        html = _re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=_re.DOTALL|_re.IGNORECASE)
        html = _re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=_re.DOTALL|_re.IGNORECASE)
        html = _re.sub(r'<header[^>]*>.*?</header>', '', html, flags=_re.DOTALL|_re.IGNORECASE)
        # Find article/main content
        art = _re.search(r'<article[^>]*>(.*?)</article>', html, _re.DOTALL|_re.IGNORECASE)
        main = _re.search(r'<main[^>]*>(.*?)</main>', html, _re.DOTALL|_re.IGNORECASE)
        content_div = _re.search(r'class=["'][^"']*(?:article-body|article-content|post-content|entry-content|story-body|article__body)[^"']*["'][^>]*>(.*?)</div>', html, _re.DOTALL|_re.IGNORECASE)
        raw = (art or main or content_div)
        if raw:
            text_html = raw.group(1)
        else:
            # Fallback: get all paragraphs
            paras = _re.findall(r'<p[^>]*>(.*?)</p>', html, _re.DOTALL|_re.IGNORECASE)
            text_html = ' '.join(paras[:15])
        # Strip tags for plain text
        text = _re.sub(r'<[^>]+>', ' ', text_html)
        text = _re.sub(r'\s+', ' ', text).strip()
        # Extract OG image
        og_img = _re.search(r'<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']', html, _re.IGNORECASE)
        img = og_img.group(1) if og_img else ""
        # Extract title
        og_title = _re.search(r'<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']', html, _re.IGNORECASE)
        title = og_title.group(1) if og_title else ""
        return JSONResponse({"ok": True, "content": text[:3000], "image": img, "title": title})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})
