# AG Technicals — Project Notes
*Last updated: Aug 2026*

## Live URLs
- Site: https://ag-technicals.onrender.com
- Repo: https://github.com/ridhi-trader/AG-TECHNICALS (branch: main)
- Render: workspace `tea-d9aibol8nd3s738id2n0` | service `srv-da7fpp2d0e5s73ef148g`

## Deploy Flow
Clone → edit → `git push origin main` → Render auto-deploys ~2min
PAT: **REGENERATE** (was exposed in chat)

## File Structure
```
index.html          — main site
gold-dossier.html   — news/dossier page
tv-indicators.html  — TV indicators page
about.html          — standalone about (unused, about section is inline in index)
privacy-policy.html
terms.html
risk-disclaimer.html
logo.png
img-smc.png / img-orderflow.png / img-esb.png
```

## Color System (Gold Theme)
```
--dark: #08070a      bg
--d2:   #141119      panel
--d3:   #1c1824      panel2
--card: #1c1824
--g4:   #f7c04a      gold accent (was green)
--g5:   #d98e2b      gold deep
--t1:   #f4efe6      text primary (warm cream)
--t2:   #9d95a6      text muted
--t3:   #5c5368      text faint
--red:  #f26d6d
--border: #2a2536
Fonts: Space Grotesk (headings) + Inter (body)
```

## Site Sections (index.html, top→bottom)
1. Nav — logo (logo.png), Services / News / About Us / Contact links + Login/Join Now
2. Ticker — colored pills: price (white), DXY (blue), Jackson Hole (orange), COT (green), AG Intel (gold)
3. Hero — left text + TradingView chart right | gold radial glow bg
4. Products — 7 buttons (4+3 grid):
   - Bridge (modal) | Algo (modal) | TV Indicator → tv-indicators.html | Education (modal)
   - Guide (modal) | Custom Strategy (modal) | News → gold-dossier.html
5. News — featured Gold Dossier card + 3-col news grid
6. About Us — inline section: Who We Are, What We Do, Markets (6 cells), (Core Expertise removed)
7. FAQ — accordion, 7 questions
8. Contact — 3 cards: Telegram / WhatsApp / Instagram (links = placeholders, need real ones)
9. Disclaimer box (red border)
10. Footer — logo + copyright + Privacy/Terms/Contact/Risk Disclaimer links

## TV Indicators Page (tv-indicators.html)
3-col grid cards. Image click → lightbox fullscreen. Body/button click → detail modal + WhatsApp CTA.
- AG SMC (TVI-0003) | AG Order Flow (TVI-0004) | AG-ESB (TVI-0005)
- WhatsApp link = placeholder `919876543210`

## Legal Pages
- privacy-policy.html, terms.html, risk-disclaimer.html — all linked from footer

## Pending / TODO
- [ ] Real WhatsApp number + Telegram + Instagram links
- [ ] Modal content for: Bridge, Algo, Education, Guide, Custom Strategy
- [ ] GitHub PAT needs regeneration
- [ ] Caveman mode active (/caveman)
