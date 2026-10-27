"""
AG Assistant Chat Backend
FastAPI proxy → Anthropic API + Market Data + File Upload
"""
import os, httpx, json, time, shutil, uuid
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# ── GLOBAL ERROR HANDLER — never crash on unhandled exceptions ──────────────
from fastapi.responses import JSONResponse as _JSONResponse
from fastapi import Request as _Request
import traceback as _traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: _Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return _JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    print(f"UNHANDLED ERROR on {request.url}: {exc}")
    _traceback.print_exc()
    return _JSONResponse(status_code=500, content={"ok": False, "error": "Internal server error"})

from bridge_module import bridge_router, add_strategy, add_license
app.include_router(bridge_router)

from video_module import video_router, add_video
app.include_router(video_router)

# EA Demo Videos
import os as _os
_base = _os.path.dirname(_os.path.abspath(__file__))

# /var/data = persistent disk on Render paid plan; fallback = ephemeral local
UPLOAD_DIR = "/var/data/uploaded_files" if _os.path.exists("/var/data") else _os.path.join(_base, "uploaded_files")
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

# Per-user licenses loaded from DB on startup (see startup function)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")

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

async def fetch_newsapi():
    """Fetch real news from NewsAPI with full descriptions"""
    if not NEWSAPI_KEY:
        return []
    queries = [
        {"q": "gold XAU price trading analysis", "cat": "Gold"},
        {"q": "forex EUR USD GBP JPY trading", "cat": "Forex"},
        {"q": "bitcoin ethereum crypto trading", "cat": "Crypto"},
        {"q": "Nifty Sensex NSE BSE Indian stock market", "cat": "Indices"},
        {"q": "S&P500 Nasdaq Dow Jones stock market indices", "cat": "Indices"},
        {"q": "Federal Reserve interest rate inflation CPI macroeconomics", "cat": "Macro"},
        {"q": "RBI India economy GDP inflation rupee", "cat": "Macro"},
        {"q": "oil silver commodity futures trading", "cat": "Commodities"},
        {"q": "forex trading technical analysis chart levels", "cat": "Analysis"},
        {"q": "gold technical analysis support resistance", "cat": "Analysis"},
        {"q": "India stock market Nifty Bank Nifty today", "cat": "Indices"},
        {"q": "Mumbai Delhi finance business economy India", "cat": "Macro"},
    ]
    all_news = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for q in queries:
                try:
                    r = await client.get(
                        "https://newsapi.org/v2/everything",
                        params={"q": q["q"], "language": "en", "sortBy": "publishedAt",
                                "pageSize": 8, "apiKey": NEWSAPI_KEY}
                    )
                    if r.status_code == 200:
                        data = r.json()
                        for art in data.get("articles", []):
                            if art.get("title") == "[Removed]": continue
                            import email.utils as _eu
                            ts = 0
                            try:
                                from datetime import datetime as _dt
                                ts = int(_dt.fromisoformat(art["publishedAt"].replace("Z","+00:00")).timestamp())
                            except: pass
                            t_diff = int((time.time() - ts) / 3600) if ts else 0
                            all_news.append({
                                "title": art.get("title",""),
                                "summary": art.get("description","") or art.get("content","")[:400] or "",
                                "image": art.get("urlToImage","") or "",
                                "url": art.get("url",""),
                                "source": art.get("source",{}).get("name","NewsAPI"),
                                "category": q["cat"],
                                "time_unix": ts,
                                "time": (str(t_diff)+"h ago") if t_diff < 24 else (str(t_diff//24)+"d ago"),
                                "real": True,
                                "badge": "LIVE",
                            })
                except Exception as qe:
                    print(f"NewsAPI query error: {qe}")
                    continue
    except HTTPException:
        raise
    except Exception as e:
        print(f"NewsAPI error: {e}")
    all_news.sort(key=lambda x: x.get("time_unix",0), reverse=True)
    return all_news[:50]

_rss_cache = {"data": [], "ts": 0}

async def fetch_rss_news():
    if _rss_cache["data"] and time.time() - _rss_cache["ts"] < 300:
        return _rss_cache["data"]
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"RSS fetch error: {e}")
    all_news.sort(key=lambda x: x.get("time_unix", 0), reverse=True)
    seen, uniq = set(), []
    cutoff = time.time() - 3 * 86400
    for n in all_news:
        key = n["title"].lower()[:80]
        if key in seen or n.get("time_unix", 0) < cutoff:
            continue
        seen.add(key)
        uniq.append(n)
    uniq = uniq[:40]
    if uniq:
        _rss_cache["data"], _rss_cache["ts"] = uniq, time.time()
    return uniq

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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Finnhub error: {e}")
        return []

SYSTEM = """You are AG Assistant — the official AI assistant for AG Technicals (www.agtechnicals.com).

AG Technicals is a software and education service provider. We build trading software (MT5 Expert Advisors, TradingView indicators), websites and custom software, and we teach trading concepts. We do NOT give trading tips, calls, signals or investment advice, and we do not manage anyone's money. You know everything about this platform and help users with any question.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUCTS & SERVICES (Full Detail)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. TRADINGVIEW INDICATOR
   - 3 custom Pine Script indicators built by AG Technicals
   - AG SMC: Smart Money Concepts indicator — marks order blocks, fair value gaps, break of structure, change of character
   - AG Order Flow: Tracks institutional order flow, shows buying/selling pressure zones
   - AG-ESB: Swing + EMA break markers with risk-reward level lines and a live dashboard
   - Works on TradingView platform (any asset — Forex, Crypto, Gold, Stocks)
   - For pricing/access: contact via WhatsApp or Telegram

2. ALGO (MT5)
   - Automated trading robots (Expert Advisors) for MetaTrader 5
   - Multiple EAs available: AG 3Logic Grid EA, AG ATR Grid EA, AG OrderFlow EA, AG Swing EMA RR EA, SMC EA
   - EAs run 24/7 automatically — no manual trading needed
   - Demo videos available on the Algo page of the website
   - Compatible with any MT5 broker
   - For pricing/access: contact via WhatsApp or Telegram

(Bridge / TradingView-to-MT5 connector is not offered at the moment. If asked, say it is not currently available.)

4. EDUCATION
   - Structured trading courses:
   - "Basic To Pro": Complete beginner to advanced trading course covering charts, patterns, risk management
   - "SMC Complete Course": Smart Money Concepts deep-dive — liquidity, order blocks, institutional trading
   - Video-based learning, self-paced
   - For pricing/access: contact via WhatsApp or Telegram

5. GUIDE
   - Written trading playbooks and strategy guides
   - EA Guides: How to set up and use each MT5 Expert Advisor
   - TradingView Guides: How to use AG indicators on TradingView
   - Step-by-step written format with screenshots
   - Available on the Guide page of the website

6. CUSTOM STRATEGY
   - Personalized trading strategy built for individual trader's style
   - Based on user's risk appetite, available time, preferred markets
   - For details/pricing: contact via WhatsApp or Telegram

7. NEWS (AG Intel)
   - Live market news aggregated from: FXStreet, Economic Times, Moneycontrol, CoinTelegraph, Investing.com
   - Live price strip: BTC, ETH, Gold, EUR/USD, GBP/USD
   - Available on the News page

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARKETS COVERED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Forex: EUR/USD, GBP/USD, USD/JPY and all major pairs
- Crypto: Bitcoin (BTC), Ethereum (ETH), and major altcoins
- Gold (XAU/USD) — special focus
- Indian Markets: NSE/BSE stocks, Nifty, Sensex (education/news coverage)
- Commodities and Indices

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEBSITE PAGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Home (index.html): Main landing page with all products overview
- Algo page: MT5 EA demos, videos, details
- Education page: Courses listing
- Guide page: EA Guides + TradingView Guides
- News page: Live market news, prices, charts
- About page: About AG Technicals
- User Login: Email OTP based login for licensed users
- User Dashboard: Access license details after login

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO GET STARTED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Browse products on the website
2. Contact AG Technicals on WhatsApp or Telegram
3. Choose your product, get access/license
5. For Indicators: get added to TradingView indicator access
6. For Algo (MT5): download EA file, install on MT5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRADING CONCEPTS (Help Users Understand)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- SMC (Smart Money Concepts): Trading methodology based on institutional order flow, liquidity zones, order blocks
- MT5 (MetaTrader 5): Professional trading platform used worldwide for Forex, Crypto, Commodities
- EA (Expert Advisor): Automated trading bot that runs on MT5
- TradingView: Online charting platform where custom indicators run
- Pine Script: Programming language used to build TradingView indicators
- Order Block: Price zone where institutional traders placed large orders
- FVG (Fair Value Gap): Price imbalance zone that tends to get filled
- BOS (Break of Structure): When price breaks a key swing high/low — trend confirmation
- CHOCH (Change of Character): First sign of trend reversal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Telegram: @AG_Technical_fx | https://t.me/AG_Technical_fx
- WhatsApp: +91 73570 32456 | https://wa.me/917357032456
- Instagram: @agtechnical | https://instagram.com/agtechnical

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- NEVER share: admin panel URL, GitHub details, backend API keys, database info, internal tech stack, server details
- NEVER give buy/sell signals, tips, price predictions or financial advice. If asked, say: "We are a software and education provider and do not give tips or advice. Trading decisions are yours alone." You may explain concepts and how our tools work.
- Never promise or imply profits, win rates or guaranteed results
- For ALL pricing questions: say "Contact us on WhatsApp or Telegram for pricing"
- Respond in SAME language as user — if user writes Hindi/Hinglish, reply in Hindi/Hinglish
- Be helpful, friendly, concise — under 200 words unless complex topic needs detail
- If asked something not related to AG Technicals or trading, politely redirect to trading topics
- Always recommend contacting via WhatsApp/Telegram for purchases or detailed queries"""

# ── MARKET DATA CACHE ──────────────────────────────────────────────────────────
_market_cache = {"data": None, "ts": 0}
CACHE_TTL = 300  # 5 min cache for news freshness

async def fetch_buysell():
    """Fetch buyer/seller ratio from Binance order book"""
    result = {}
    syms = [("BTCUSDT","BTC"), ("ETHUSDT","ETH"), ("XAUUSDT","XAU")]
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            for sym, label in syms:
                try:
                    # Long/Short ratio from Binance futures
                    r = await client.get(f"https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?symbol={sym}&period=1h&limit=1")
                    if r.status_code == 200:
                        data = r.json()
                        if data:
                            long_pct = float(data[0].get("longAccount","0.5")) * 100
                            short_pct = 100 - long_pct
                            result[label] = {"buy": round(long_pct,1), "sell": round(short_pct,1)}
                except:
                    pass
    except:
        pass
    return result

async def _yahoo_quote(client, symbol):
    r = await client.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d")
    if r.status_code != 200:
        return None
    meta = r.json()["chart"]["result"][0]["meta"]
    price = float(meta["regularMarketPrice"])
    prev = float(meta.get("chartPreviousClose") or meta.get("previousClose") or 0)
    chg = ((price - prev) / prev * 100) if prev else 0.0
    return {"price": price, "chg": chg}

async def fetch_prices():
    """Real prices only. Tries Binance, then CoinGecko (crypto) and Yahoo Finance (gold/FX).
    A symbol that cannot be fetched from any source is left out - never estimated."""
    prices = {}
    hdr = {"User-Agent": "Mozilla/5.0 (AG Technicals)"}
    async with httpx.AsyncClient(timeout=8, headers=hdr) as client:
        for sym in ["BTCUSDT", "ETHUSDT", "EURUSDT", "GBPUSDT"]:
            try:
                r = await client.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={sym}")
                if r.status_code == 200:
                    j = r.json()
                    prices[sym] = {"price": float(j["lastPrice"]), "chg": float(j["priceChangePercent"])}
            except Exception:
                pass
        if "BTCUSDT" not in prices or "ETHUSDT" not in prices:
            try:
                r = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true")
                if r.status_code == 200:
                    j = r.json()
                    for sym, cid in (("BTCUSDT", "bitcoin"), ("ETHUSDT", "ethereum")):
                        if sym not in prices and cid in j:
                            prices[sym] = {"price": float(j[cid]["usd"]), "chg": float(j[cid].get("usd_24h_change", 0))}
            except Exception:
                pass
        for sym, ysym in (("XAUUSDT", "GC=F"), ("EURUSDT", "EURUSD=X"), ("GBPUSDT", "GBPUSD=X")):
            if sym in prices:
                continue
            try:
                q = await _yahoo_quote(client, ysym)
                if q:
                    prices[sym] = q
            except Exception:
                pass
    return prices

@app.get("/api/market-data")
async def market_data():
    """Live prices only. Nothing here is generated or estimated."""
    global _market_cache
    now = time.time()
    if _market_cache["data"] and (now - _market_cache["ts"]) < 120:
        return _market_cache["data"]
    raw = await fetch_prices()
    names = {"XAUUSDT": "XAU/USD", "BTCUSDT": "BTC/USD", "ETHUSDT": "ETH/USD",
             "EURUSDT": "EUR/USD", "GBPUSDT": "GBP/USD"}
    prices = {names[k]: {"price": v["price"], "change_24h": v["chg"], "chg": v["chg"]}
              for k, v in raw.items() if k in names}
    result = {"prices": prices, "ticker": [], "news": {}, "cached_at": int(now)}
    if prices:  # do not cache an empty result
        _market_cache = {"data": result, "ts": now}
    return result

# ── FILE UPLOAD SYSTEM ─────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(request: Request, file: UploadFile = File(...), category: str = Form(default="general")):
    verify_admin_token(request)
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
        url = f"/uploaded_files/{final_name}"
        
        return {
            "ok": True,
            "url": url,
            "filename": orig_name,
            "size": size,
            "file_id": final_name,
        }
    except HTTPException:
        raise
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
                "url": f"/uploaded_files/{fname}",
                "size": size,
            })
    return {"files": sorted(files, key=lambda x: x["name"])}

@app.delete("/api/uploads/{filename}")
@app.delete("/api/uploads/delete/{filename}")
async def delete_upload(filename: str, request: Request):
    verify_admin_token(request)
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
    newsapi = await fetch_newsapi()

    articles = []
    # NewsAPI first — real content with full descriptions
    for item in newsapi:
        articles.append({
            "title": item["title"], "summary": item.get("summary",""),
            "category": item.get("category","Market"), "source": item.get("source",""),
            "url": item.get("url",""), "image": item.get("image",""),
            "dir":"up", "real": True, "badge": "LIVE",
            "time": item.get("time",""),
        })
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
    if category and category != "All":
        articles = [a for a in articles if a["category"].lower()==category.lower()]
    if search:
        sl=search.lower()
        articles = [a for a in articles if sl in a["title"].lower() or sl in a.get("summary","").lower()]
    return {
        "articles": articles,
        "sentiment": [],
        "prices": {"gold":prices.get("XAUUSDT",{}),"btc":prices.get("BTCUSDT",{}),"eurusd":prices.get("EURUSDT",{})},
        "total": len(articles), "has_live": len(finnhub)>0, "updated": int(time.time()),
    }

_groq_model = ""

@app.post("/api/chat")
async def chat(req: ChatReq):
    try:
        try:
            msgs = [m.dict() for m in req.messages]
        except Exception:
            msgs = [m.model_dump() for m in req.messages]

        sysmsg = [{"role": "system", "content": SYSTEM}]
        clean = [{"role": m.get("role"), "content": m.get("content", "")} for m in msgs
                 if m.get("role") in ("user", "assistant") and m.get("content")]

        # 1) OpenRouter, 2) Groq, 3) Anthropic. First one that answers wins.
        async def openai_style(url, key, model, extra_headers=None):
            headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
            headers.update(extra_headers or {})
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(url, headers=headers, json={
                    "model": model, "max_tokens": 800, "messages": sysmsg + clean})
            try:
                rj = r.json()
            except Exception:
                rj = {}
            if r.status_code == 200:
                return rj.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            print(f"{url.split('/')[2]} error {r.status_code}: {str(rj)[:200]}")
            return ""

        OR_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if OR_KEY:
            reply = await openai_style(
                "https://openrouter.ai/api/v1/chat/completions", OR_KEY,
                os.environ.get("OR_MODEL", "meta-llama/llama-3.2-3b-instruct:free"),
                {"HTTP-Referer": "https://www.agtechnicals.com", "X-Title": "AG Technicals"})
            if reply:
                return {"reply": reply}

        GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
        if GROQ_KEY:
            global _groq_model
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            model = _groq_model or os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
            reply = await openai_style(groq_url, GROQ_KEY, model)
            if not reply:
                # The configured model may have been retired or not be enabled for this key.
                # Ask Groq which chat models this key can use and pick the best available one.
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        mr = await client.get("https://api.groq.com/openai/v1/models",
                                              headers={"Authorization": f"Bearer {GROQ_KEY}"})
                    ids = [m.get("id", "") for m in (mr.json().get("data") or []) if m.get("id")]
                except Exception as ex:
                    print(f"groq model list failed: {ex}")
                    ids = []
                skip = ("whisper", "guard", "tts", "playai", "orpheus", "distil", "prompt-guard", "safeguard")
                chat_ids = [i for i in ids if not any(k in i.lower() for k in skip)]
                prefer = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b",
                          "openai/gpt-oss-120b", "meta-llama/llama-4-scout-17b-16e-instruct", "gemma2-9b-it"]
                order = [m for m in prefer if m in chat_ids and m != model] + [m for m in chat_ids if m not in prefer and m != model]
                for m in order[:4]:
                    reply = await openai_style(groq_url, GROQ_KEY, m)
                    if reply:
                        _groq_model = m
                        print(f"groq: using model {m}")
                        break
            if reply:
                return {"reply": reply}

        ANT_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if ANT_KEY and clean:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANT_KEY, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    json={"model": "claude-haiku-4-5-20251001", "max_tokens": 800,
                          "system": SYSTEM, "messages": clean})
            if r.status_code == 200:
                parts = r.json().get("content", [])
                reply = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
                if reply:
                    return {"reply": reply}
            print(f"anthropic error {r.status_code}: {r.text[:200]}")

        return {"reply": "Service unavailable. Please contact us on WhatsApp or Telegram."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chat endpoint exception: {e}")
        return {"reply": "Network error. Please try again."}

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
GMAIL_PASS = os.environ.get("GMAIL_PASS", "")  # App Password (legacy, unused on Railway)
BREVO_API_KEY = (os.environ.get("BREVO_API_KEY") or "").strip()  # Brevo HTTP API — set in Railway env vars, never hardcode
def get_admin_pass():
    """Admin password comes only from the ADMIN_PASS env var. No hardcoded default:
    if it is unset, every admin request is refused."""
    return os.environ.get('ADMIN_PASS', '')

def verify_admin_token(request):
    """Check X-Admin-Token header matches current admin password."""
    token = request.headers.get("X-Admin-Token", "")
    expected = get_admin_pass()
    if not expected or not token or not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.get("/api/admin/verify")
async def admin_verify(request: Request):
    verify_admin_token(request)
    return {"ok": True}

SITE_URL = "https://ag-technicals-production.up.railway.app"

_db_pool = None

async def get_db():
    global _db_pool
    if not _db_pool and DB_URL:
        try:
            _db_pool = await asyncpg.create_pool(DB_URL, ssl='require', min_size=1, max_size=5)
            await init_db()
        except HTTPException:
            raise
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
            CREATE TABLE IF NOT EXISTS ag_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
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
    """Send an email via ZeptoMail (primary) or Brevo (fallback) — see mailer.py."""
    from mailer import send_mail
    try:
        used = send_mail(to_email, subject, body, sender_name="AG Technicals")
        print(f"Email sent via {used}")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        raise Exception("Email service error. Please try again later or contact support@agtechnicals.com")

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
    try:
        print("=" * 50)
        print("AG TECHNICALS — SERVER STARTING")
        print(f"GMAIL_USER: {'SET' if GMAIL_USER else 'MISSING'}")
        from mailer import provider_status as _mail_status
        print(f"Email provider: {_mail_status()}")
        print(f"DATABASE_URL: {'SET' if DB_URL else 'MISSING'}")
        print(f"ADMIN_EMAIL: {os.environ.get('ADMIN_EMAIL','NOT SET')}")
        print(f"NEWSAPI_KEY: {'SET' if os.environ.get('NEWSAPI_KEY') else 'MISSING'}")
        db = await get_db()
        if db:
            print("DB: CONNECTED OK")
        else:
            print("DB: CONNECTION FAILED — products/users won't work (site still runs)")
        print("=" * 50)
    except Exception as e:
        # NEVER crash on startup errors — log and continue
        print(f"STARTUP WARNING: {e} — continuing anyway")

    # ── Support email auto-reply bot (support@agtechnicals.com) ──
    try:
        import asyncio as _asyncio
        from email_bot import email_bot_loop
        _asyncio.create_task(email_bot_loop())
    except Exception as e:
        print(f"[email_bot] failed to start: {e} — continuing anyway")


@app.get("/api/health")
async def health_check():
    db = await get_db()
    return {
        "ok": True,
        "db": "connected" if db else "disconnected",
        "email": __import__("mailer").provider_status(),
        "version": "2.0"
    }

async def _send_signup_otp(conn, email):
    await conn.execute("DELETE FROM ag_otps WHERE email=$1 AND purpose='signup'", email)
    otp = gen_otp()
    expires = datetime.utcnow() + timedelta(minutes=10)
    await conn.execute("INSERT INTO ag_otps (email,otp,purpose,expires_at) VALUES ($1,$2,'signup',$3)", email, otp, expires)
    send_email(email, "AG Technicals — Verify Your Email", otp_email_html(otp, 'signup'))

@app.post("/api/auth/signup")
async def signup(req: SignupReq):
    pool = await get_db()
    if not pool:
        return JSONResponse({"ok": False, "error": "Database unavailable"})
    email = (req.email or '').strip().lower()
    username = (req.username or '').strip()
    if len(req.password) < 6:
        return JSONResponse({"ok": False, "error": "Password must be at least 6 characters"})
    if len(username) < 3:
        return JSONResponse({"ok": False, "error": "Username must be at least 3 characters"})
    try:
        async with pool.acquire() as conn:
            by_email = await conn.fetchrow("SELECT id,verified FROM ag_users WHERE LOWER(email)=$1", email)
            by_user = await conn.fetchrow("SELECT id FROM ag_users WHERE LOWER(username)=LOWER($1)", username)
            if by_email and by_email['verified']:
                return JSONResponse({"ok": False, "error": "This email is already registered — please Login (or use Forgot Password)"})
            if by_user and (not by_email or by_user['id'] != by_email['id']):
                return JSONResponse({"ok": False, "error": "Username already taken — try another username"})
            if by_email:
                # Earlier signup never verified — refresh details and resend OTP
                await conn.execute("UPDATE ag_users SET username=$1, password_hash=$2, email=$3 WHERE id=$4",
                    username, hash_pass(req.password), email, by_email['id'])
            else:
                await conn.execute("INSERT INTO ag_users (username, email, password_hash) VALUES ($1,$2,$3)",
                    username, email, hash_pass(req.password))
            await _send_signup_otp(conn, email)
            return JSONResponse({"ok": True, "msg": "OTP sent to your email"})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})

class ResendReq(BaseModel):
    email: str

@app.post("/api/auth/resend-otp")
async def resend_otp(req: ResendReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    email = (req.email or '').strip().lower()
    async with pool.acquire() as conn:
        u = await conn.fetchrow("SELECT id,verified FROM ag_users WHERE LOWER(email)=$1", email)
        if not u: return JSONResponse({"ok": False, "error": "Email not found — please Sign Up again"})
        if u['verified']: return JSONResponse({"ok": False, "error": "Already verified — please Login"})
        await _send_signup_otp(conn, email)
        return JSONResponse({"ok": True, "msg": "New OTP sent"})

@app.post("/api/auth/verify-otp")
async def verify_otp(req: OtpReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        email = (req.email or '').strip().lower()
        row = await conn.fetchrow("SELECT * FROM ag_otps WHERE LOWER(email)=$1 AND otp=$2 AND purpose='signup' AND used=FALSE AND expires_at > NOW()", email, req.otp.strip())
        if not row: return JSONResponse({"ok": False, "error": "Invalid or expired OTP"})
        await conn.execute("UPDATE ag_otps SET used=TRUE WHERE id=$1", row['id'])
        await conn.execute("UPDATE ag_users SET verified=TRUE WHERE LOWER(email)=$1", email)
        user = await conn.fetchrow("SELECT id,username,email,products FROM ag_users WHERE LOWER(email)=$1", email)
        return JSONResponse({"ok": True, "user": {"id": user['id'], "username": user['username'], "email": user['email'], "products": user['products']}})

@app.post("/api/auth/login")
async def login(req: LoginReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        email = (req.email or '').strip().lower()
        user = await conn.fetchrow("SELECT * FROM ag_users WHERE LOWER(email)=$1", email)
        if not user: return JSONResponse({"ok": False, "error": "No account with this email — please Sign Up"})
        if user['password_hash'] != hash_pass(req.password): return JSONResponse({"ok": False, "error": "Wrong password — try again or use Forgot Password"})
        if not user['verified']: return JSONResponse({"ok": False, "error": "Email not verified — please Sign Up again with same email to get a new OTP"})
        return JSONResponse({"ok": True, "user": {"id": user['id'], "username": user['username'], "email": user['email'], "products": user['products']}})

@app.post("/api/auth/forgot-password")
async def forgot_password(req: ForgotReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        email = (req.email or '').strip().lower()
        user = await conn.fetchrow("SELECT id FROM ag_users WHERE LOWER(email)=$1", email)
        if not user: return JSONResponse({"ok": False, "error": "Email not found"})
        await conn.execute("DELETE FROM ag_otps WHERE LOWER(email)=$1 AND purpose='reset'", email)
        otp = gen_otp()
        expires = datetime.utcnow() + timedelta(minutes=10)
        await conn.execute("INSERT INTO ag_otps (email,otp,purpose,expires_at) VALUES ($1,$2,'reset',$3)", email, otp, expires)
        send_email(email, "AG Technicals — Password Reset OTP", otp_email_html(otp, 'reset'))
        return JSONResponse({"ok": True, "msg": "OTP sent to your email"})

@app.post("/api/auth/reset-password")
async def reset_password(req: ResetReq):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Database unavailable"})
    async with pool.acquire() as conn:
        email = (req.email or '').strip().lower()
        row = await conn.fetchrow("SELECT * FROM ag_otps WHERE LOWER(email)=$1 AND otp=$2 AND purpose='reset' AND used=FALSE AND expires_at > NOW()", email, req.otp.strip())
        if not row: return JSONResponse({"ok": False, "error": "Invalid or expired OTP"})
        if len(req.new_password) < 6: return JSONResponse({"ok": False, "error": "Password too short"})
        await conn.execute("UPDATE ag_otps SET used=TRUE WHERE id=$1", row['id'])
        await conn.execute("UPDATE ag_users SET password_hash=$1 WHERE LOWER(email)=$2", hash_pass(req.new_password), email)
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
async def assign_products(req: AssignReq, request: Request):
    verify_admin_token(request)
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False})
    async with pool.acquire() as conn:
        await conn.execute("UPDATE ag_users SET products=$1 WHERE id=$2", req.products, req.user_id)
        return JSONResponse({"ok": True})

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, request: Request):
    verify_admin_token(request)
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "DB unavailable"})
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM ag_otps WHERE email=(SELECT email FROM ag_users WHERE id=$1)", user_id)
        await conn.execute("DELETE FROM ag_users WHERE id=$1", user_id)
    return JSONResponse({"ok": True})

@app.delete("/api/admin/users/by-email/{email}")
async def admin_delete_user_by_email(email: str, request: Request):
    verify_admin_token(request)
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "DB unavailable"})
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id,username,email,verified FROM ag_users WHERE LOWER(email)=LOWER($1)", email)
        if not row:
            return JSONResponse({"ok": False, "error": "User not found"})
        await conn.execute("DELETE FROM ag_otps WHERE email=$1", row['email'])
        await conn.execute("DELETE FROM ag_users WHERE id=$1", row['id'])
    return JSONResponse({"ok": True, "deleted": {"id": row['id'], "username": row['username'], "email": row['email']}})

# Admin forgot password — OTP to admin email
import random as _random
_admin_otp_store = {}

class AdminForgotReq(BaseModel):
    action: str  # 'send' or 'verify'
    otp: str = ''
    newPass: str = ''

@app.post('/api/admin-forgot-otp')
async def admin_forgot_otp(req: AdminForgotReq):
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', GMAIL_USER)
    if req.action == 'send':
        otp = str(_random.randint(100000, 999999))
        _admin_otp_store['otp'] = otp
        _admin_otp_store['exp'] = __import__('time').time() + 600  # 10 min
        body = f"""<div style='font-family:sans-serif;max-width:500px;margin:auto;padding:30px;background:#0d0d0f;color:#fff;border-radius:12px;'>
<h2 style='color:#e8b84b;'>AG Technicals Admin</h2>
<p>Password reset OTP:</p>
<div style='font-size:36px;font-weight:900;letter-spacing:10px;color:#e8b84b;padding:20px;background:#1a1a1f;border-radius:8px;text-align:center;'>{otp}</div>
<p style='color:#888;font-size:12px;'>Valid for 10 minutes. Do not share.</p>
</div>"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: send_email(ADMIN_EMAIL, 'AG Admin — Password Reset OTP', body))
            return JSONResponse({'ok': True})
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse({'ok': False, 'error': str(e)})
    elif req.action == 'verify':
        stored = _admin_otp_store.get('otp')
        exp = _admin_otp_store.get('exp', 0)
        if not stored:
            return JSONResponse({'ok': False, 'error': 'No OTP sent'})
        if __import__('time').time() > exp:
            return JSONResponse({'ok': False, 'error': 'OTP expired'})
        if req.otp != stored:
            return JSONResponse({'ok': False, 'error': 'Wrong OTP'})
        if not req.newPass or len(req.newPass) < 6:
            return JSONResponse({'ok': False, 'error': 'New password too short (min 6 chars)'})
        _admin_otp_store.clear()
        # Save new password in DB so it persists across redeploys
        try:
            pool = await get_db()
            if pool:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO ag_config(key,value) VALUES('admin_pass',$1) ON CONFLICT(key) DO UPDATE SET value=$1",
                        req.newPass
                    )
            # Also update in-memory so current session works immediately
            import os
            os.environ['ADMIN_PASS'] = req.newPass
        except HTTPException:
            raise
        except Exception as e:
            return JSONResponse({'ok': False, 'error': f'Password save failed: {e}'})
        return JSONResponse({'ok': True})
    return JSONResponse({'ok': False, 'error': 'Invalid action'})

@app.get("/api/config/{key}")
async def get_config(key: str):
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "value": None})
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT value FROM ag_config WHERE key=$1", key)
        if row:
            return JSONResponse({"ok": True, "value": row["value"]})
        return JSONResponse({"ok": False, "value": None})

class ConfigSetReq(BaseModel):
    key: str
    value: str

@app.post("/api/config/set")
async def set_config(req: ConfigSetReq, request: Request):
    verify_admin_token(request)
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False})
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO ag_config(key,value,updated_at) VALUES($1,$2,NOW()) ON CONFLICT(key) DO UPDATE SET value=$2,updated_at=NOW()", req.key, req.value)
        return JSONResponse({"ok": True})

@app.post("/api/admin/backup")
async def admin_backup(request: Request):
    """Save a copy of config data on the server volume (kept: newest 40)."""
    verify_admin_token(request)
    import re
    body = await request.json()
    label = re.sub(r"[^a-zA-Z0-9_-]", "", str(body.get("label", "backup")))[:40] or "backup"
    d = "/var/data/config_backups"
    try:
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{label}-{int(time.time())}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(body.get("data"), f, ensure_ascii=False)
        files = sorted(os.listdir(d))
        for old in files[:-40]:
            try: os.remove(os.path.join(d, old))
            except Exception: pass
        return {"ok": True, "file": os.path.basename(path)}
    except Exception as e:
        print(f"backup failed: {e}")
        return {"ok": False}

@app.get("/api/admin/users")
async def admin_users(request: Request):
    verify_admin_token(request)
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
async def create_bridge_license(req: BridgeLicReq, request: Request):
    verify_admin_token(request)
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
async def delete_bridge_license(lid: str, request: Request):
    verify_admin_token(request)
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
        content_div = _re.search(r'class=["\'](article-body|article-content|post-content|entry-content|story-body|article__body)["\'][^>]*>(.*?)</div>', html, _re.DOTALL|_re.IGNORECASE)
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
        og_img = _re.search('<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html, _re.IGNORECASE)
        img = og_img.group(1) if og_img else ""
        # Extract title
        og_title = _re.search('<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, _re.IGNORECASE)
        title = og_title.group(1) if og_title else ""
        # If content too short, use AI to expand
        if len(text) < 200 and ANTHROPIC_KEY:
            try:
                async with httpx.AsyncClient(timeout=20) as ai_client:
                    ai_resp = await ai_client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                        json={"model": "claude-haiku-4-5-20251001", "max_tokens": 600,
                              "messages": [{"role": "user", "content": f"Write a detailed 3-4 paragraph trading news analysis for a trader audience about this headline: \"{title or url}\"\n\nContext: {text}\n\nFocus on market impact, what traders should watch, and key levels. Be specific and informative."}]}
                    )
                    if ai_resp.status_code == 200:
                        ai_data = ai_resp.json()
                        ai_text = ai_data.get("content", [{}])[0].get("text", "")
                        if ai_text:
                            text = ai_text
            except Exception:
                pass
        return JSONResponse({"ok": True, "content": text[:3000], "image": img, "title": title})
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)})


# ══════════════════════════════════════════════════════════════════════════════
# PAYMENTS — Razorpay Checkout (orders created on the server, prices from admin catalog)
# Env: RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET  (set in Railway only)
# ══════════════════════════════════════════════════════════════════════════════
import hmac as _hmac, re as _re_pay, html as _html_pay

def _rzp_id():      return os.environ.get("RAZORPAY_KEY_ID", "").strip()
def _rzp_secret():  return os.environ.get("RAZORPAY_KEY_SECRET", "").strip()
def _rzp_whsec():   return os.environ.get("RAZORPAY_WEBHOOK_SECRET", "").strip()
def _pay_enabled(): return bool(_rzp_id() and _rzp_secret())

_orders_ready = False
async def _ensure_orders(conn):
    global _orders_ready
    if _orders_ready: return
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ag_orders (
            id SERIAL PRIMARY KEY,
            order_id TEXT UNIQUE NOT NULL,
            product_key TEXT NOT NULL,
            product_name TEXT NOT NULL,
            amount_paise INTEGER NOT NULL,
            currency TEXT DEFAULT 'INR',
            name TEXT, email TEXT, phone TEXT,
            status TEXT DEFAULT 'created',
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            paid_at TIMESTAMP
        )""")
    await conn.execute("ALTER TABLE ag_orders ADD COLUMN IF NOT EXISTS product_code TEXT")
    _orders_ready = True

async def _pay_catalog(conn):
    row = await conn.fetchrow("SELECT value FROM ag_config WHERE key=$1", "ag_pricing")
    try:
        items = json.loads(row["value"]) if row and row["value"] else []
    except Exception:
        items = []
    out = []
    for it in items if isinstance(items, list) else []:
        try:
            price = float(it.get("price", 0))
        except Exception:
            price = 0
        key = str(it.get("key", "")).strip()
        if key and price > 0 and it.get("active", True):
            out.append({"key": key, "code": key, "name": str(it.get("name", key))[:120], "price": price,
                        "desc": str(it.get("desc", ""))[:400]})
    return out

async def _pay_resolve(conn, key: str):
    """Find a payable item. Price always comes from the server: either the Admin price list,
    or an Algo (MT5) plan stored in the product data (key format  ea:<name>:<3|6|12>)."""
    key = (key or "").strip()
    item = next((i for i in await _pay_catalog(conn) if i["key"] == key), None)
    if item or not key.startswith("ea:"):
        return item
    try:
        _, rest = key.split(":", 1)
        name, months = rest.rsplit(":", 1)
        months = int(months)
    except Exception:
        return None
    if months not in (3, 6, 12):
        return None
    row = await conn.fetchrow("SELECT value FROM ag_config WHERE key=$1", "ag_products")
    try:
        prods = json.loads(row["value"]) if row and row["value"] else []
    except Exception:
        prods = []
    algo = next((p for p in prods if isinstance(p, dict) and p.get("id") == "algo"), None)
    eas = (algo or {}).get("items") or []
    ea = next((e for e in eas if isinstance(e, dict) and not e.get("hidden") and str(e.get("name", "")).strip().lower() == name.strip().lower()), None)
    if not ea:
        return None
    defaults = {3: 30000, 6: 54000, 12: 100000}
    field = {3: "price3m", 6: "price6m", 12: "price12m"}[months]
    try:
        price = float(ea.get(field) or defaults[months])
    except Exception:
        price = float(defaults[months])
    if price <= 0:
        return None
    return {"key": key, "code": str(ea.get("pid") or "")[:30], "name": f"{str(ea.get('name'))[:90]} — {months} months", "price": price, "desc": ""}

@app.get("/api/pay/catalog")
async def pay_catalog():
    pool = await get_db()
    if not pool: return JSONResponse({"ok": True, "enabled": False, "items": []})
    async with pool.acquire() as conn:
        items = await _pay_catalog(conn)
    return JSONResponse({"ok": True, "enabled": _pay_enabled(), "key_id": _rzp_id() if _pay_enabled() else "", "items": items})

class PayOrderReq(BaseModel):
    product_key: str
    name: str
    email: str
    phone: str = ""

@app.post("/api/pay/create-order")
async def pay_create_order(req: PayOrderReq):
    if not _pay_enabled():
        return JSONResponse({"ok": False, "error": "Online payments are not enabled yet. Please contact us on WhatsApp or Telegram."})
    name = req.name.strip()[:80]; email = req.email.strip().lower()[:120]; phone = _re_pay.sub(r"[^0-9+]", "", req.phone)[:15]
    if len(name) < 2: return JSONResponse({"ok": False, "error": "Please enter your name."})
    if not _re_pay.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email): return JSONResponse({"ok": False, "error": "Please enter a valid email."})
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "error": "Service busy. Please try again."})
    async with pool.acquire() as conn:
        await _ensure_orders(conn)
        item = await _pay_resolve(conn, req.product_key)
        if not item: return JSONResponse({"ok": False, "error": "This item is not available."})
        amount = int(round(item["price"] * 100))
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post("https://api.razorpay.com/v1/orders", auth=(_rzp_id(), _rzp_secret()),
                    json={"amount": amount, "currency": "INR", "receipt": (_re_pay.sub(r"[^A-Za-z0-9_-]", "", item.get("code", ""))[:20] + "_" if item.get("code") else "agt_") + uuid.uuid4().hex[:12],
                          "notes": {"product_key": item["key"], "product_code": item.get("code", ""), "product": item["name"], "email": email}})
            rj = r.json()
        except Exception as e:
            print(f"Razorpay create-order error: {e}")
            return JSONResponse({"ok": False, "error": "Could not start payment. Please try again."})
        if r.status_code != 200 or not rj.get("id"):
            print(f"Razorpay order error {r.status_code}: {str(rj)[:200]}")
            return JSONResponse({"ok": False, "error": "Could not start payment. Please try again."})
        await conn.execute(
            "INSERT INTO ag_orders (order_id,product_key,product_name,amount_paise,name,email,phone,product_code) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
            rj["id"], item["key"], item["name"], amount, name, email, phone, item.get("code", ""))
    return JSONResponse({"ok": True, "order_id": rj["id"], "amount": amount, "currency": "INR",
                         "key_id": _rzp_id(), "name": item["name"] + (f" ({item['code']})" if item.get("code") else "")})

import asyncio
async def _pay_mark_paid(order_id: str, payment_id: str):
    """Idempotent: mark paid, grant access, send emails. Safe to call from verify AND webhook."""
    pool = await get_db()
    if not pool: return None
    async with pool.acquire() as conn:
        await _ensure_orders(conn)
        row = await conn.fetchrow("SELECT * FROM ag_orders WHERE order_id=$1", order_id)
        if not row: return None
        if row["status"] == "paid": return row
        await conn.execute("UPDATE ag_orders SET status='paid', payment_id=$1, paid_at=NOW() WHERE order_id=$2 AND status<>'paid'", payment_id, order_id)
        # grant access if a user with this email exists
        user = await conn.fetchrow("SELECT id,products FROM ag_users WHERE LOWER(email)=$1", (row["email"] or "").lower())
        if user:
            cur = [p.strip() for p in (user["products"] or "").split(",") if p.strip()]
            if row["product_key"] not in cur:
                cur.append(row["product_key"])
                await conn.execute("UPDATE ag_users SET products=$1 WHERE id=$2", ",".join(cur), user["id"])
    amt = f"₹{row['amount_paise']/100:,.2f}"
    e = _html_pay.escape
    try:
        await asyncio.to_thread(send_email, row["email"], "Payment received — AG Technicals",
            f"<div style='font-family:Arial,sans-serif;max-width:480px'><h2>Thank you, {e(row['name'] or '')}!</h2>"
            f"<p>We received your payment of <b>{amt}</b> for <b>{e(row['product_name'])}</b>{(' (Code: ' + e(row['product_code']) + ')') if row['product_code'] else ''}.</p>"
            f"<p>Order ID: {e(order_id)}<br>Payment ID: {e(payment_id)}</p>"
            f"<p>We will contact you shortly with access details. Questions? Write to support@agtechnicals.com or message us on WhatsApp/Telegram.</p>"
            f"<p style='color:#888;font-size:12px'>AG Technicals is a software and education provider. Refunds follow our Refund Policy on agtechnicals.com.</p></div>")
    except Exception as ex:
        print(f"receipt email failed: {ex}")
    admin_to = os.environ.get("ADMIN_EMAIL", "").strip()
    if admin_to:
        try:
            await asyncio.to_thread(send_email, admin_to, f"New order: {('[' + row['product_code'] + '] ') if row['product_code'] else ''}{row['product_name']} {amt}",
                f"<p>{e(row['name'] or '')} ({e(row['email'] or '')}, {e(row['phone'] or '')}) paid {amt} for <b>{e(row['product_name'])}</b>{(' · Code ' + e(row['product_code'])) if row['product_code'] else ''}.<br>Order {e(order_id)} · Payment {e(payment_id)}</p>")
        except Exception as ex:
            print(f"admin order email failed: {ex}")
    return row

class PayVerifyReq(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@app.post("/api/pay/verify")
async def pay_verify(req: PayVerifyReq):
    if not _pay_enabled(): return JSONResponse({"ok": False})
    expected = _hmac.new(_rzp_secret().encode(), f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(), "sha256").hexdigest()
    if not _hmac.compare_digest(expected, req.razorpay_signature):
        return JSONResponse({"ok": False, "error": "Payment could not be verified. If money was deducted, contact support@agtechnicals.com with your payment ID."})
    row = await _pay_mark_paid(req.razorpay_order_id, req.razorpay_payment_id)
    return JSONResponse({"ok": bool(row)})

@app.post("/api/pay/webhook")
async def pay_webhook(request: Request):
    secret = _rzp_whsec()
    body = await request.body()
    sig = request.headers.get("X-Razorpay-Signature", "")
    if not secret or not sig:
        return JSONResponse({"ok": False}, status_code=400)
    expected = _hmac.new(secret.encode(), body, "sha256").hexdigest()
    if not _hmac.compare_digest(expected, sig):
        return JSONResponse({"ok": False}, status_code=400)
    try:
        ev = json.loads(body)
        if ev.get("event") in ("payment.captured", "order.paid"):
            pay = (ev.get("payload", {}).get("payment", {}) or {}).get("entity", {}) or {}
            oid, pid = pay.get("order_id"), pay.get("id")
            if oid and pid:
                await _pay_mark_paid(oid, pid)
    except Exception as ex:
        print(f"webhook error: {ex}")
    return JSONResponse({"ok": True})

@app.get("/api/admin/orders")
async def admin_orders(request: Request):
    verify_admin_token(request)
    pool = await get_db()
    if not pool: return JSONResponse({"ok": False, "orders": []})
    async with pool.acquire() as conn:
        await _ensure_orders(conn)
        rows = await conn.fetch("SELECT order_id,product_name,product_code,amount_paise,name,email,phone,status,payment_id,created_at,paid_at FROM ag_orders ORDER BY created_at DESC LIMIT 200")
    return JSONResponse({"ok": True, "enabled": _pay_enabled(), "orders": [
        {"order_id": r["order_id"], "product": r["product_name"], "code": r["product_code"] or "", "amount": r["amount_paise"]/100, "name": r["name"], "email": r["email"],
         "phone": r["phone"], "status": r["status"], "payment_id": r["payment_id"],
         "created": str(r["created_at"])[:16], "paid": str(r["paid_at"])[:16] if r["paid_at"] else ""} for r in rows]})
