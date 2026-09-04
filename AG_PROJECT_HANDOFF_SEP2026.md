# AG Technicals — Full Project Handoff
*Last updated: Sep 4, 2026 | Claude Sonnet 4.6 session*

---

## Live URLs
- **Site:** https://ag-technicals.onrender.com
- **Admin:** https://ag-technicals.onrender.com/admin.html (password: `ridhima2307`)
- **User Login:** https://ag-technicals.onrender.com/user-login.html
- **User Dashboard:** https://ag-technicals.onrender.com/user-dashboard.html
- **News Feed:** https://ag-technicals.onrender.com/news.html
- **Guide Page:** https://ag-technicals.onrender.com/guide.html
- **Education:** https://ag-technicals.onrender.com/education.html
- **AI Backend:** https://ag-assistant-api.onrender.com
- **Repo:** https://github.com/ridhi-trader/AG-TECHNICALS (branch: main)

## Render Services
- **Static Site:** workspace `tea-d9aibol8nd3s738id2n0` | service `srv-da7fpp2d0e5s73ef148g`
- **AG Assistant API (FastAPI):** workspace `tea-d9aibol8nd3s738id2n0` | service `srv-daatkj2fngtc73adbhmg`

## GitHub PAT
- Current: `[YOUR-PAT-HERE]`
- **Regenerate each session** at github.com/settings/tokens

## Deploy Flow
```bash
cd /tmp && git clone https://[PAT]@github.com/ridhi-trader/AG-TECHNICALS.git
cd AG-TECHNICALS
git config user.email "ag@agtechnicals.com"
git config user.name "AG Technicals"
# edit files
git add -A && git commit -m "msg" && git push https://[PAT]@github.com/ridhi-trader/AG-TECHNICALS.git main
# Render auto-deploys: site ~2min, API ~3min
```

---

## Full File Structure
```
index.html                    — Main site (localStorage CMS, product cards, hero, news, FAQ)
admin.html                    — Admin panel (password: ridhima2307)
user-login.html               — User signup/login/OTP/forgot-password
user-dashboard.html           — User dashboard (products, profile, logout)
news.html                     — Live news feed (search, categories, TV chart, 5min refresh)
guide.html                    — Guides page (cards → fullscreen reader)
education.html                — Education landing (course cards)
education-foundation.html     — Basic To Pro course (Hindi+English)
education-smc.html            — SMC Complete Course (17 chapters)
real-trading-journey.html     — Real Trading Journey course
swing-ema-guide.html          — AG Swing EMA RR EA full guide
atr-grid-guide.html           — AG ATR Grid EA guide
smc-feature-guide.html        — AG SMC Feature Guide
tv-indicators.html            — TradingView indicators page
algo.html                     — MT5 EA marketplace (5 EAs + video modals)
bridge.html                   — Bridge landing page
bridge-guide.html             — Bridge setup guide
gold-dossier.html             — Gold dossier page (COT, DXY, institutional)
ag-assistant.js               — AI assistant widget (all non-admin pages)
chat_backend.py               — FastAPI backend (all API endpoints)
bridge_module.py              — Pure Python bridge (TV→MT5 signal relay)
video_module.py               — Video serving module
requirements.txt              — fastapi, uvicorn, httpx, pydantic, python-multipart, aiofiles, asyncpg, passlib, python-jose, emails
logo.png, img-smc.png, img-orderflow.png, img-esb.png
SMC_EA_demo.mp4, AG_OrderFlow_EA_demo.mp4, AG_3LOGIC_GRID_EA_demo.mp4, AG_ATR_GRID_EA_demo.mp4, AG_SWING_EMA_RR_EA_demo.mp4
```

---

## Color System
```css
--bg:#0d0d0f  --card:#141318  --g5:#e8b84b  --g4:#c9960c
--t1:#fff  --t2:#c8c4d0  --t3:#a0a0b8  --border:#2a2736
--red:#f26d6d  --green:#4ade80
Fonts: Space Grotesk (headings) + Inter (body) + JetBrains Mono (code)
```

---

## Architecture — CMS

All site content stored in **localStorage**, read at page load.

### localStorage Keys
| Key | Controls |
|-----|---------|
| `ag_products` | 7 products (id, name, icon, sub, badge, desc, cta, type, url, img, fileUrl, fileName, hidden, items[]) |
| `ag_indicators` | TV indicator cards |
| `ag_users` | Local user tracking (admin-added) |
| `ag_hero` | Hero section content |
| `ag_ticker` | Ticker pills |
| `ag_contact` | Contact cards |
| `ag_faq` | FAQ items |
| `ag_about` | About section |
| `ag_news` | News dossier settings |
| `ag_admin_pass` | Admin password (default: ridhima2307) |
| `ag_bio_id` | Biometric credential ID |
| `productPrices` | Product prices for revenue calc |
| `csSent` | Custom strategy sent history |
| `uploadedFiles` | Locally stored file metadata |

### Product IDs + Sub-items
| Product | ID | Type | URL | Sub-items |
|---------|-----|------|-----|-----------|
| Bridge | bridge | page | bridge.html | BRG-0001 to BRG-0004 (guide + licenses) |
| Algo (MT5) | algo | page | algo.html | EA-0001 to EA-0005 (5 EAs) |
| TradingView Indicator | tvindicator | page | tv-indicators.html | TVI-0003 to TVI-0005 |
| Education | education | page | education.html | EDU-0001 to EDU-0003 |
| Guide | guide | page | guide.html | GD-0001 to GD-0003 |
| Custom Strategy | custom | modal | — | none |
| News | news | page | news.html | NEWS-0001 |

### Force Fix (auto-runs on page load)
index.html + admin.html both have force-fix code that:
- Sets guide/education/bridge/algo to correct `type:'page'` and URL
- Merges D_PRODS default items into stored products if items array is empty
- Fixes stale localStorage data automatically

---

## Backend (chat_backend.py) — All Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET/HEAD | Health check |
| `/api/chat` | POST | AI assistant (Claude Haiku) |
| `/api/market-data` | GET | Live prices (Binance) + AI news — 5min cache |
| `/api/news` | GET | News feed (Finnhub if key set + AI) — params: category, search |
| `/api/upload` | POST | File upload to server disk |
| `/uploads/{filename}` | GET | Serve uploaded file |
| `/api/uploads/list` | GET | List all uploaded files |
| `/api/uploads/{filename}` | DELETE | Delete uploaded file |
| `/api/cache/clear` | GET | Force clear market data cache |
| `/api/auth/signup` | POST | User signup (saves to Neon DB) |
| `/api/auth/verify-otp` | POST | Verify email OTP |
| `/api/auth/login` | POST | User login |
| `/api/auth/forgot-password` | POST | Send reset OTP |
| `/api/auth/reset-password` | POST | Reset password with OTP |
| `/api/auth/user/{id}` | GET | Get user profile |
| `/api/admin/users` | GET | All registered users (admin) |
| `/api/admin/assign-products` | POST | Assign products to user |
| `/master/{sid}` | POST | Bridge webhook from TradingView |
| `/api/pull/{lid}` | GET | Bridge EA poll |
| `/api/bridge/status` | GET | Bridge status |
| `/video/{id}.mp4` | GET | EA demo video (range requests) |

### Render Environment Variables Needed
| Variable | Value | Status |
|----------|-------|--------|
| `ANTHROPIC_API_KEY` | sk-ant-... | ✅ Set |
| `DATABASE_URL` | postgresql://... (Neon) | ⚠️ Need to set |
| `GMAIL_USER` | gmail address | ⚠️ Need for OTP email |
| `GMAIL_PASS` | Gmail App Password (16 digit) | ⚠️ Need for OTP email |
| `FINNHUB_API_KEY` | finnhub.io free key | ⚠️ Optional — for real news |

**Without Gmail credentials:** OTP prints to Render logs (can copy from there)
**Without DATABASE_URL:** User auth returns "Database unavailable"
**Without FINNHUB_KEY:** News uses AI-generated headlines only

---

## Admin Panel — Sidebar Tabs

| Tab | Function |
|-----|---------|
| 🎯 Products & Services | Edit all 7 products — name, icon, badge, desc, CTA, type, URL, image upload, file upload, sub-items |
| 📈 TV Indicators | Add/edit/hide/delete TV indicator cards |
| 👥 Users & Access | Add local users, assign products; Load From DB button for registered users |
| 📊 Analytics & Revenue | Stats, product prices for revenue estimate, 7-day activity |
| ⚙️ Custom Strategy Sender | Build + send strategy via WhatsApp/Telegram, attach file, sent history |
| 🏠 Hero Section | Badge, H1, sub, CTA button text, video URL |
| 📡 Ticker Strip | Add/remove ticker pills with color types |
| 📞 Contact Links | Platform, icon, URL, handle |
| 👤 About Us | Title, who text, markets, video |
| ❓ FAQ | Add/remove FAQ items |
| 📰 News & Dossier | Force refresh live news cache, dossier card settings |
| 📁 File Uploads | Upload any file to server, view all server files, copy URL |
| 📦 Export / Backup | Download/restore all data as JSON |
| 🔐 Security | Biometric setup, change password |

### Admin Login
- Password: `ridhima2307`
- Stored in `localStorage['ag_admin_pass']` (changeable from Security tab)
- Session-based (clears on tab close)
- Biometric: WebAuthn — setup from Security tab, device-specific
- Body `visibility:hidden` until auth — no content flash

---

## User Auth System

### Flow
1. Signup → POST /api/auth/signup → OTP email sent
2. Verify OTP → POST /api/auth/verify-otp → user verified, session set
3. Login → POST /api/auth/login → session set → dashboard
4. Forgot → POST /api/auth/forgot-password → OTP → POST /api/auth/reset-password

### Database (Neon PostgreSQL)
Tables auto-created on startup:
- `ag_users` — id, username, email, password_hash, products (CSV), created_at, verified
- `ag_otps` — id, email, otp, purpose, expires_at, used

### Session Storage
User stored in `sessionStorage['ag_user']` as JSON: `{id, username, email, products}`

### Admin: Assign Products to User
Admin → Users tab → "Load From DB" → "Assign Products" button → checkbox overlay → Save
Calls POST /api/admin/assign-products with `{user_id, products: "bridge,algo,tvindicator"}`

---

## Bridge System (bridge_module.py)

**Pure Python** — no .so dependency, works on Python 3.14+

### Signal Flow
```
TradingView → POST /master/{sid} → validate → queue → PENDING[lid]
MT5 EA → GET /api/pull/{lid}?account=12345&ea=MyEA&v=1.22 → get signal
```

### Default Credentials
- Strategy ID: `agbridge` | Secret: `ag-bridge-secret-2026`
- License: `LIC-0001` (365 days)
- Webhook: `https://ag-assistant-api.onrender.com/master/agbridge`

### Signal Response Format
```
buy,XAUUSD,2634.5,2630.0,,   ← action,symbol,price,sl,tp,lot
OK|License activated on this account
ERROR|Invalid License ID
CONFIG|manual=0              ← EA v1.22+, every 60s
```

---

## News System

### news.html
- Search bar — instant filter across all articles
- Category buttons — All/Gold/Forex/Crypto/Indices/Macro/Commodities/Analysis
- 5-minute auto-refresh
- Sidebar: live prices, sentiment bars, TradingView chart embed, external source links
- Video cards — YouTube articles get thumbnail + play
- LIVE badge = Finnhub real news | AG badge = AI-generated

### To Enable Real News (Finnhub)
1. Go to finnhub.io → free signup → copy API key
2. Render → AG Assistant API → Environment → Add `FINNHUB_API_KEY`
3. Real forex/crypto/general news will appear with LIVE badge

---

## File Upload System

### How it works
- Admin → File Uploads tab → choose file → Upload
- XHR upload with real progress % display
- Files saved to `uploaded_files/` on Render disk
- URL returned: `https://ag-assistant-api.onrender.com/uploads/{filename}`
- **LIMITATION:** Render free plan = ephemeral disk — files deleted on restart

### For Videos (MP4)
- Render free plan times out on large files (>50MB)
- **Use YouTube Unlisted** → paste URL in Video URL field
- Small videos (<20MB) can upload directly

### File URL Usage
- Product image → paste in Image URL field in product editor
- Product file → paste in File URL field
- Sub-item file → paste in sub-item file URL field

---

## Live Market Data

### Ticker + Prices
- Binance API → BTC, ETH, XAU, EUR/USD, GBP/USD live prices
- 5-minute cache (backend)
- Frontend auto-refresh every 5 min
- Dossier card shows live XAU price

### News Generation
- Claude Haiku generates 12 realistic market headlines based on live prices
- Includes articles array, sentiment data, ticker_extra
- Cache: 5 min if news generated, 10 min if AI failed (retry sooner)

---

## Key Rules
- Site name: **AG Technicals** (always with S)
- Product: **TradingView Indicator** (not "TV Indicator"), **Algo (MT5)**
- First letter of every word capitalized in UI text
- Core words highlighted in gold (#e8b84b)
- Always push to GitHub — never deliver as download
- AG communicates in **Hinglish** — reply in same style
- AG uses **caveman/terse mode** — short, action-focused responses

## Editing Patterns
```bash
# Clone fresh each session
cd /tmp && git clone https://[PAT]@github.com/ridhi-trader/AG-TECHNICALS.git
cd AG-TECHNICALS && git config user.email "ag@agtechnicals.com" && git config user.name "AG Technicals"

# Always syntax check JS before push
node --check /tmp/chk.js

# Complex JS edits → Python str.replace (avoids quote/backslash issues)
python3 << 'PYEOF'
with open('file.html','r') as f: c=f.read()
c = c.replace(old, new)
with open('file.html','w') as f: f.write(c)
PYEOF

# Push
git add -A && git commit -m "msg" && git push https://[PAT]@github.com/ridhi-trader/AG-TECHNICALS.git main
```

## Known Issues / Pending
- [ ] Gmail SMTP not configured — OTP goes to Render logs only
- [ ] Neon DATABASE_URL not set — user auth returns "unavailable"
- [ ] Finnhub API key not set — news is AI-generated only
- [ ] Render free plan = ephemeral disk — uploaded files lost on restart
- [ ] WhatsApp: 919876543210 (placeholder), Telegram: @agtechnical (placeholder), Instagram: @agtechnical
- [ ] Video uploads >50MB timeout on free plan — use YouTube instead
- [ ] PAT needs regeneration each session

## Render Network Note
- Claude bash_tool CANNOT reach `ag-technicals.onrender.com` or `ag-assistant-api.onrender.com`
- This is Claude-side restriction — NOT a site issue
- Use `Render:list_logs` and `Render:list_deploys` MCP tools for debugging

## Caveman Mode
AG prefers short, terse, action-focused responses in Hinglish.
Load `/mnt/skills/user/caveman/SKILL.md` when `/caveman` prefix used.
