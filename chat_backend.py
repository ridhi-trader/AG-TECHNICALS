"""
AG Assistant Chat Backend
FastAPI proxy → Anthropic API + Market Data
"""
import os, httpx, json, time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

from bridge_module import bridge_router, add_strategy, add_license
app.include_router(bridge_router)

from video_module import video_router, add_video
app.include_router(video_router)

# EA Demo Videos
import os as _os
_base = _os.path.dirname(_os.path.abspath(__file__))
add_video("smc_ea",       _os.path.join(_base, "SMC_EA_demo.mp4"))
add_video("orderflow_ea", _os.path.join(_base, "AG_OrderFlow_EA_demo.mp4"))
add_video("grid3_ea",     _os.path.join(_base, "AG_3LOGIC_GRID_EA_demo.mp4"))
add_video("atr_ea",       _os.path.join(_base, "AG_ATR_GRID_EA_demo.mp4"))
add_video("swing_ea",     _os.path.join(_base, "AG_SWING_EMA_RR_EA_demo.mp4"))

# Default strategy + license
add_strategy(sid="agbridge", secret="ag-bridge-secret-2026", name="AG TradeBridge")
add_license(lid="LIC-0001", days=365)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM = """You are AG Assistant — the official AI assistant for AG Technicals (ag-technicals.onrender.com).

AG Technicals is a professional trading analysis platform offering:

PRODUCTS:
1. TradingView Indicator — 3 custom Pine Script indicators: AG SMC, AG Order Flow, AG-ESB. Auto-detect key levels and zones in real time. Page: /tv-indicators.html
2. Algo (MT5) — Automated trading system for MetaTrader 5.
3. Bridge — TradingView → MT5 signal connector. Sends TV alerts directly to MT5 EA.
4. Education — Structured courses: "Basic To Pro" (beginner) and "SMC Complete Course" (17 chapters, advanced). Page: /education.html
5. Guide — Written trading playbooks.
6. Custom Strategy — Personalized trading strategy built by AG Technicals analysts.
7. News — AG Intel live market dossiers, COT analysis, DXY watch. Page: /gold-dossier.html

CONTACT:
- Telegram: @agtechnical | https://t.me/agtechnical
- WhatsApp: +91 98765 43210 | https://wa.me/919876543210
- Instagram: @agtechnical | https://instagram.com/agtechnical

ABOUT:
- 9+ years of real screen time across every major market
- Covers Forex, Crypto, Indices, and Commodities
- Not financial advice — educational and analytical content only

RULES:
- NEVER share passwords, admin details, admin.html URL, GitHub info, backend/internal details
- NEVER share personal details about team members
- For pricing: say "contact us on WhatsApp or Telegram for pricing"
- Respond in the same language the user writes in (Hinglish, Hindi, or English)
- Keep answers concise (under 150 words) unless detail is needed
- Always end with relevant CTA when appropriate
- Be professional, warm, and helpful"""

# ── MARKET DATA CACHE ──
_market_cache = {"data": None, "ts": 0}
CACHE_TTL = 3600  # 1 hour cache

async def fetch_prices():
    """Fetch live prices from Binance + fallback static"""
    prices = {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Binance - crypto + XAUUSDT
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

    # Fallback / supplement with static if needed
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
    """Use Claude to generate current market news items based on live prices"""
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
Today's date: {time.strftime('%B %d, %Y')}.

Generate realistic market news for a trading website. Return ONLY valid JSON, no markdown:
{{
  "latest": [
    {{"title": "headline about forex or macro news", "time": "Xh ago · Forex", "dir": "up"}},
    {{"title": "headline about crypto", "time": "Xh ago · Crypto", "dir": "up"}},
    {{"title": "headline about gold/commodities", "time": "Xh ago · Commodities", "dir": "dn"}},
    {{"title": "headline about indices", "time": "Xh ago · Indices", "dir": "up"}}
  ],
  "analysis": [
    {{"title": "EUR/USD analysis based on price", "time": "Xh ago · AG Analysis", "dir": "up"}},
    {{"title": "Gold/XAU analysis based on price", "time": "Xh ago · AG Analysis", "dir": "dn"}},
    {{"title": "GBP/USD analysis", "time": "Xh ago · AG Analysis", "dir": "up"}},
    {{"title": "BTC/crypto analysis", "time": "Xh ago · AG Analysis", "dir": "up"}}
  ],
  "sentiment": [
    {{"label": "Forex", "pct": 65, "dir": "up"}},
    {{"label": "Crypto", "pct": 72, "dir": "up"}},
    {{"label": "Gold", "pct": 55, "dir": "up"}},
    {{"label": "Indices", "pct": 60, "dir": "up"}},
    {{"label": "Crude Oil", "pct": 45, "dir": "neutral"}}
  ],
  "ticker_extra": [
    "relevant macro event or central bank note"
  ]
}}

Use the actual prices above. Make headlines realistic and specific. dir must be up/dn/neutral. pct 20-85. time format like "2h ago · Forex"."""

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 800,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
        data = r.json()
        text = data.get("content", [{}])[0].get("text", "")
        # Strip markdown if any
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as e:
        return None

@app.get("/api/market-data")
async def market_data():
    """Live market data + AI news — cached 1hr"""
    global _market_cache
    now = time.time()
    
    if _market_cache["data"] and (now - _market_cache["ts"]) < CACHE_TTL:
        return _market_cache["data"]
    
    prices = await fetch_prices()
    news_ai = await fetch_news_ai(prices)
    
    # Build ticker pills from live prices
    def arrow(chg):
        return "▲" if chg >= 0 else "▼"
    
    def fmt_price(sym, label, decimals=2):
        p = prices.get(sym, {})
        pr = p.get("price", 0)
        ch = p.get("chg", 0)
        return f"{label}  {pr:.{decimals}f}  {arrow(ch)} {abs(ch):.2f}%"

    ticker = [
        {"text": fmt_price("XAUUSDT", "XAU/USD", 2), "type": "gold"},
        {"text": fmt_price("BTCUSDT", "BTCUSD", 0), "type": "default"},
        {"text": fmt_price("ETHUSDT", "ETHUSD", 0), "type": "default"},
        {"text": fmt_price("EURUSDT", "EUR/USD", 4), "type": "default"},
        {"text": fmt_price("GBPUSDT", "GBP/USD", 4), "type": "default"},
        {"text": "COT · Managed Money tracking institutional flow", "type": "cot"},
        {"text": "AG INTEL · Gold Dossier — Read ↗", "type": "gold"},
    ]
    
    # Add AI event if available
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
    
    _market_cache = {"data": result, "ts": now}
    return result


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
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 500,
                "system": SYSTEM,
                "messages": [m.dict() for m in req.messages],
            }
        )
    data = r.json()
    reply = data.get("content", [{}])[0].get("text", "Sorry, please try again.")
    return {"reply": reply}

@app.get("/")
def root():
    return {"status": "AG Assistant API running"}
