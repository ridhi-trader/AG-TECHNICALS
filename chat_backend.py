"""
AG Assistant Chat Backend
Simple FastAPI proxy → Anthropic API
"""
import os, httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

from bridge_module import bridge_router, add_strategy, add_license
app.include_router(bridge_router)

from video_module import video_router
app.include_router(video_router)

# Default strategy + license
add_strategy(sid="agbridge", secret="ag-bridge-secret-2026", name="AG TradeBridge")
add_license(lid="LIC-0001", days=365)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST","OPTIONS"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY","")

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
    reply = data.get("content",[{}])[0].get("text","Sorry, please try again.")
    return {"reply": reply}

@app.get("/")
def root():
    return {"status": "AG Assistant API running"}
