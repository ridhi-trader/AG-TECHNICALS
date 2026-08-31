/* ══════════════════════════════════════
   AG ASSISTANT — Shared AI Chat Widget
   Loads on every page of AG Technicals
   ══════════════════════════════════════ */

(function(){
  // ── STYLES ──────────────────────────────
  const css = `
  #ag-ai-bubble{
    position:fixed;bottom:28px;right:28px;
    width:54px;height:54px;border-radius:50%;
    background:linear-gradient(135deg,#c9960c,#e8b84b);
    border:none;cursor:pointer;
    display:flex;align-items:center;justify-content:center;
    font-size:22px;box-shadow:0 4px 20px rgba(232,184,75,0.45);
    z-index:9999;transition:transform .2s,box-shadow .2s;
    animation:ag-pop-in .4s cubic-bezier(.34,1.56,.64,1) both;
  }
  @keyframes ag-pop-in{from{transform:scale(0);opacity:0;}to{transform:scale(1);opacity:1;}}
  #ag-ai-bubble:hover{transform:scale(1.1);box-shadow:0 6px 28px rgba(232,184,75,0.6);}
  #ag-ai-bubble .ag-notif{
    position:absolute;top:-2px;right:-2px;
    width:14px;height:14px;border-radius:50%;
    background:#f26d6d;border:2px solid #0d0d0f;
    display:none;
  }
  #ag-ai-panel{
    position:fixed;bottom:94px;right:28px;
    width:360px;max-height:540px;
    background:#16141c;border:1px solid #2a2736;border-radius:20px;
    display:none;flex-direction:column;
    z-index:9998;box-shadow:0 20px 60px rgba(0,0,0,0.7);
    overflow:hidden;
    animation:ag-slide-up .25s ease both;
  }
  @keyframes ag-slide-up{from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:translateY(0);}}
  #ag-ai-panel.ag-open{display:flex;}
  .ag-ai-hdr{
    display:flex;align-items:center;gap:12px;
    padding:16px 18px;border-bottom:1px solid #2a2736;
    background:#1a1724;flex-shrink:0;
  }
  .ag-ai-hdr-icon{
    width:36px;height:36px;border-radius:50%;
    background:linear-gradient(135deg,#c9960c,#e8b84b);
    display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0;
  }
  .ag-ai-hdr-text{flex:1;}
  .ag-ai-hdr-name{font-weight:700;font-size:14px;color:#fff;font-family:'Space Grotesk','Inter',sans-serif;}
  .ag-ai-hdr-sub{font-size:11px;color:#a0a0b8;margin-top:1px;}
  .ag-ai-close{background:none;border:none;color:#a0a0b8;font-size:18px;cursor:pointer;padding:4px;line-height:1;transition:color .2s;}
  .ag-ai-close:hover{color:#fff;}
  .ag-ai-quick{
    display:flex;flex-wrap:wrap;gap:6px;padding:12px 14px 4px;flex-shrink:0;
  }
  .ag-ai-chip{
    font-size:11px;padding:5px 11px;border-radius:20px;
    border:1px solid rgba(232,184,75,0.25);color:#e8b84b;
    background:rgba(232,184,75,0.07);cursor:pointer;
    transition:all .15s;white-space:nowrap;font-family:'Inter',sans-serif;
  }
  .ag-ai-chip:hover{background:rgba(232,184,75,0.15);border-color:rgba(232,184,75,0.5);}
  #ag-ai-msgs{
    flex:1;overflow-y:auto;padding:14px 14px 8px;
    display:flex;flex-direction:column;gap:10px;min-height:160px;
  }
  #ag-ai-msgs::-webkit-scrollbar{width:3px;}
  #ag-ai-msgs::-webkit-scrollbar-thumb{background:#2a2736;border-radius:3px;}
  .ag-msg{
    max-width:88%;font-size:13.5px;line-height:1.55;
    padding:10px 13px;border-radius:14px;word-break:break-word;
    font-family:'Inter',sans-serif;
  }
  .ag-msg.bot{
    background:#211f2d;color:#c8c4d0;
    border-radius:14px 14px 14px 3px;align-self:flex-start;
  }
  .ag-msg.user{
    background:linear-gradient(135deg,rgba(232,184,75,0.18),rgba(201,150,12,0.12));
    color:#fff;border:1px solid rgba(232,184,75,0.18);
    border-radius:14px 14px 3px 14px;align-self:flex-end;
  }
  .ag-msg.typing{color:#a0a0b8;font-style:italic;}
  .ag-msg a{color:#e8b84b;text-decoration:underline;}
  .ag-ai-input-row{
    display:flex;gap:8px;padding:12px;
    border-top:1px solid #2a2736;background:#1a1724;flex-shrink:0;
  }
  #ag-ai-input{
    flex:1;background:#0d0d0f;border:1px solid #2a2736;border-radius:10px;
    color:#fff;font-size:13px;padding:9px 13px;outline:none;
    font-family:'Inter',sans-serif;resize:none;line-height:1.4;
    transition:border-color .2s;
  }
  #ag-ai-input:focus{border-color:rgba(232,184,75,0.4);}
  #ag-ai-input::placeholder{color:#a0a0b8;}
  #ag-ai-send{
    width:36px;height:36px;border-radius:9px;border:none;
    background:linear-gradient(135deg,#c9960c,#e8b84b);
    color:#0d0d0f;font-size:15px;cursor:pointer;
    display:flex;align-items:center;justify-content:center;
    flex-shrink:0;transition:opacity .2s;align-self:flex-end;
  }
  #ag-ai-send:hover{opacity:.85;}
  #ag-ai-send:disabled{opacity:.35;cursor:not-allowed;}
  @media(max-width:640px){
    #ag-ai-panel{width:calc(100vw - 32px);right:16px;bottom:84px;}
    #ag-ai-bubble{bottom:20px;right:16px;}
  }
  `;

  const styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── HTML ────────────────────────────────
  const html = `
  <button id="ag-ai-bubble" onclick="agAI.toggle()" title="Ask AG Assistant">
    🤖<span class="ag-notif" id="ag-notif"></span>
  </button>
  <div id="ag-ai-panel">
    <div class="ag-ai-hdr">
      <div class="ag-ai-hdr-icon">⚡</div>
      <div class="ag-ai-hdr-text">
        <div class="ag-ai-hdr-name">AG Assistant</div>
        <div class="ag-ai-hdr-sub">Ask Anything About AG Technicals</div>
      </div>
      <button class="ag-ai-close" onclick="agAI.toggle()">✕</button>
    </div>
    <div class="ag-ai-quick" id="ag-chips">
      <span class="ag-ai-chip" onclick="agAI.chip('What products does AG Technicals offer?')">Products</span>
      <span class="ag-ai-chip" onclick="agAI.chip('How do I contact AG Technicals?')">Contact</span>
      <span class="ag-ai-chip" onclick="agAI.chip('Tell me about the SMC course')">SMC Course</span>
      <span class="ag-ai-chip" onclick="agAI.chip('What are the TradingView indicators?')">Indicators</span>
      <span class="ag-ai-chip" onclick="agAI.chip('What is the Algo MT5?')">Algo MT5</span>
    </div>
    <div id="ag-ai-msgs">
      <div class="ag-msg bot">Namaste! 👋 Main <strong>AG Assistant</strong> hun. AG Technicals ke baare mein kuch bhi pucho — products, courses, contact, indicators — sab bata dunga!</div>
    </div>
    <div class="ag-ai-input-row">
      <textarea id="ag-ai-input" rows="1" placeholder="Kuch bhi pucho..."></textarea>
      <button id="ag-ai-send" onclick="agAI.send()">➤</button>
    </div>
  </div>
  `;

  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  document.body.appendChild(wrapper);

  // ── SYSTEM PROMPT ────────────────────────
  const SYSTEM = `You are AG Assistant — the official AI assistant for AG Technicals (website: ag-technicals.onrender.com).

AG Technicals is a professional trading analysis platform offering:

PRODUCTS:
1. TradingView Indicator — 3 custom Pine Script indicators: AG SMC, AG Order Flow, AG-ESB. Auto-detect key levels and zones in real time. Page: /tv-indicators.html
2. Algo (MT5) — Automated trading system for MetaTrader 5. Sub-items include SMC Algo and Gold Algo.
3. Bridge — TradingView → MT5 signal connector. Sends TV alerts directly to MT5 EA.
4. Education — Structured courses: "Basic To Pro" (beginner, Hinglish/Hindi/English) and "SMC Complete Course" (17 chapters, advanced). Page: /education.html
5. Guide — Written trading playbooks.
6. Custom Strategy — Personalized trading strategy built by AG Technicals analysts.
7. News — AG Intel live market dossiers, COT analysis, DXY watch. Page: /gold-dossier.html

CONTACT:
- Telegram: @agtechnical | https://t.me/agtechnical
- WhatsApp: +91 98765 43210 | https://wa.me/919876543210
- Instagram: @agtechnical | https://instagram.com/agtechnical

ABOUT AG TECHNICALS:
- 9+ years of real screen time across every major market
- Covers Forex, Crypto, Indices, and Commodities
- Institutional-grade analysis, live signals, real-time charts
- Not financial advice — educational and analytical content only

RULES — STRICTLY FOLLOW:
- NEVER share any passwords, admin panel details, admin.html URL, localStorage keys, GitHub repo, PAT tokens, or any backend/internal technical details
- NEVER share any personal details about team members
- DO NOT claim specific prices — say "contact us on WhatsApp/Telegram for pricing"
- Respond in the same language the user writes in (Hinglish, Hindi, or English)
- Keep answers concise (under 150 words) unless a detailed explanation is needed
- Always end with a relevant CTA (contact link or page link) when appropriate
- You represent AG Technicals professionally — be helpful, warm, and knowledgeable`;

  // ── STATE ────────────────────────────────
  const agAI = {
    msgs: [],
    open: false,

    toggle(){
      const panel = document.getElementById('ag-ai-panel');
      this.open = !this.open;
      panel.classList.toggle('ag-open', this.open);
      document.getElementById('ag-notif').style.display = 'none';
      if(this.open) setTimeout(()=> document.getElementById('ag-ai-input').focus(), 100);
    },

    chip(text){
      document.getElementById('ag-chips').style.display = 'none';
      this._sendText(text);
    },

    send(){
      const inp = document.getElementById('ag-ai-input');
      const txt = inp.value.trim();
      if(!txt) return;
      inp.value = ''; inp.style.height = 'auto';
      document.getElementById('ag-chips').style.display = 'none';
      this._sendText(txt);
    },

    async _sendText(txt){
      this._addMsg(txt, 'user');
      this.msgs.push({role:'user', content: txt});

      const sendBtn = document.getElementById('ag-ai-send');
      sendBtn.disabled = true;
      const typingEl = this._addMsg('Typing...', 'bot typing');

      try{
        const res = await fetch('https://ag-chat-box.onrender.com/api/ai-chat',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ messages: this.msgs })
        });
        const data = await res.json();
        const reply = data.reply || 'Sorry, kuch problem ho gayi. Dobara try karo ya WhatsApp karo: wa.me/919876543210';
        typingEl.innerHTML = reply.replace(/\n/g,'<br>');
        typingEl.classList.remove('typing');
        this.msgs.push({role:'assistant', content: reply});
        // Keep context window manageable
        if(this.msgs.length > 20) this.msgs = this.msgs.slice(-16);
      } catch(e){
        typingEl.textContent = 'Network error. Please try again.';
        typingEl.classList.remove('typing');
      }
      sendBtn.disabled = false;
      this._scroll();
    },

    _addMsg(text, cls){
      const el = document.createElement('div');
      el.className = 'ag-msg ' + cls;
      el.textContent = text;
      const box = document.getElementById('ag-ai-msgs');
      box.appendChild(el);
      this._scroll();
      return el;
    },

    _scroll(){
      const box = document.getElementById('ag-ai-msgs');
      if(box) box.scrollTop = 99999;
    }
  };

  window.agAI = agAI;

  // Input auto-resize + Enter to send
  document.getElementById('ag-ai-input').addEventListener('input', function(){
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 100) + 'px';
  });
  document.getElementById('ag-ai-input').addEventListener('keydown', function(e){
    if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); agAI.send(); }
  });

  // Show notification dot after 8s if panel not opened
  setTimeout(()=>{
    if(!agAI.open){
      document.getElementById('ag-notif').style.display = 'block';
    }
  }, 8000);

})();
