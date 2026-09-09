/* AG Technicals — Content Protection */
(function(){
  document.addEventListener('contextmenu', function(e){ e.preventDefault(); });
  document.addEventListener('selectstart', function(e){ e.preventDefault(); });
  document.addEventListener('keydown', function(e){
    if(e.key==='PrintScreen'){ navigator.clipboard.writeText(''); }
    if(e.ctrlKey && ['s','p','u','a'].includes(e.key.toLowerCase())){ e.preventDefault(); }
    if(e.key==='F12'){ e.preventDefault(); }
  });
  var style = document.createElement('style');
  style.innerHTML =
    'body { -webkit-user-select:none; -moz-user-select:none; user-select:none; }' +
    'img { pointer-events:none; -webkit-user-drag:none; }' +
    '@media print { body::before { content:"© AG Technicals — Confidential"; position:fixed; top:50%; left:50%; transform:translate(-50%,-50%) rotate(-45deg); font-size:48px; color:rgba(232,184,75,0.3); font-weight:900; z-index:99999; } }';
  document.head.appendChild(style);
})();


/* ══════════════════════════════════════
   AG ASSISTANT — Shared AI Chat Widget
   ══════════════════════════════════════ */

(function(){
  const css = `
  /* ── Bubble ── */
  #ag-ai-bubble {
    position:fixed; bottom:28px; right:28px;
    width:60px; height:60px; border-radius:50%;
    background:#0d0d0f;
    border:2px solid rgba(232,184,75,0.6);
    cursor:pointer; display:flex; align-items:center; justify-content:center;
    z-index:9999; transition:transform .2s, box-shadow .2s, border-color .2s;
    box-shadow: 0 0 0 0 rgba(232,184,75,0.4);
    animation: ag-pop-in .4s cubic-bezier(.34,1.56,.64,1) both, ag-glow 3s ease-in-out 2s infinite;
  }
  @keyframes ag-pop-in { from{transform:scale(0);opacity:0;} to{transform:scale(1);opacity:1;} }
  @keyframes ag-glow {
    0%,100% { box-shadow: 0 0 0 0 rgba(232,184,75,0.0); }
    50%      { box-shadow: 0 0 0 8px rgba(232,184,75,0.18); }
  }
  #ag-ai-bubble:hover {
    transform:scale(1.08);
    border-color:#e8b84b;
    box-shadow: 0 0 20px rgba(232,184,75,0.35);
  }
  /* Avatar face SVG inside bubble */
  #ag-ai-bubble svg { width:34px; height:34px; }

  .ag-notif {
    position:absolute; top:-3px; right:-3px;
    width:15px; height:15px; border-radius:50%;
    background:#f26d6d; border:2px solid #0d0d0f;
    display:none;
    animation: ag-bounce 1s ease infinite;
  }
  @keyframes ag-bounce { 0%,100%{transform:scale(1);} 50%{transform:scale(1.2);} }

  /* ── Panel ── */
  #ag-ai-panel {
    position:fixed; bottom:100px; right:28px;
    width:360px; max-height:560px;
    background:#111018;
    border:1px solid rgba(232,184,75,0.18);
    border-radius:20px;
    display:none; flex-direction:column;
    z-index:9998;
    box-shadow: 0 24px 64px rgba(0,0,0,0.8), 0 0 0 1px rgba(232,184,75,0.06);
    overflow:hidden;
    animation: ag-slide-up .25s ease both;
  }
  @keyframes ag-slide-up { from{opacity:0;transform:translateY(14px);} to{opacity:1;transform:translateY(0);} }
  #ag-ai-panel.ag-open { display:flex; }

  /* ── Header ── */
  .ag-ai-hdr {
    display:flex; align-items:center; gap:12px;
    padding:14px 16px;
    background: linear-gradient(135deg, #161320 0%, #1a1628 100%);
    border-bottom:1px solid rgba(232,184,75,0.1);
    flex-shrink:0;
  }
  /* Mini avatar in header */
  .ag-hdr-avatar {
    width:40px; height:40px; border-radius:50%;
    background:#0d0d0f;
    border:1.5px solid rgba(232,184,75,0.5);
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
  }
  .ag-hdr-avatar svg { width:22px; height:22px; }
  .ag-ai-hdr-text { flex:1; }
  .ag-ai-hdr-name {
    font-weight:700; font-size:14px; color:#fff;
    font-family:'Space Grotesk','Inter',sans-serif;
    letter-spacing:.2px;
  }
  .ag-online-row { display:flex; align-items:center; gap:5px; margin-top:2px; }
  .ag-online-dot {
    width:7px; height:7px; border-radius:50%;
    background:#4ade80;
    box-shadow: 0 0 6px rgba(74,222,128,0.6);
    animation: ag-pulse-dot 2s ease infinite;
  }
  @keyframes ag-pulse-dot { 0%,100%{opacity:1;} 50%{opacity:.5;} }
  .ag-online-txt { font-size:11px; color:#a0a0b8; font-family:'Inter',sans-serif; }
  .ag-ai-close {
    background:none; border:none; color:#a0a0b8;
    font-size:17px; cursor:pointer; padding:4px;
    line-height:1; transition:color .2s; border-radius:6px;
  }
  .ag-ai-close:hover { color:#fff; background:rgba(255,255,255,0.06); }

  /* ── Quick chips ── */
  .ag-ai-quick {
    display:flex; flex-wrap:wrap; gap:6px;
    padding:12px 14px 2px; flex-shrink:0;
  }
  .ag-ai-chip {
    font-size:11px; padding:5px 12px; border-radius:20px;
    border:1px solid rgba(232,184,75,0.2); color:#e8b84b;
    background:rgba(232,184,75,0.06); cursor:pointer;
    transition:all .15s; white-space:nowrap;
    font-family:'Inter',sans-serif; font-weight:500;
  }
  .ag-ai-chip:hover { background:rgba(232,184,75,0.14); border-color:rgba(232,184,75,0.45); }

  /* ── Messages ── */
  #ag-ai-msgs {
    flex:1; overflow-y:auto; padding:12px 14px 6px;
    display:flex; flex-direction:column; gap:10px; min-height:160px;
  }
  #ag-ai-msgs::-webkit-scrollbar { width:3px; }
  #ag-ai-msgs::-webkit-scrollbar-thumb { background:#2a2736; border-radius:3px; }

  .ag-msg-row { display:flex; align-items:flex-end; gap:8px; }
  .ag-msg-row.user { flex-direction:row-reverse; }
  .ag-msg-avatar {
    width:26px; height:26px; border-radius:50%; flex-shrink:0;
    background:#0d0d0f; border:1px solid rgba(232,184,75,0.3);
    display:flex; align-items:center; justify-content:center;
  }
  .ag-msg-avatar svg { width:14px; height:14px; }

  .ag-msg {
    max-width:82%; font-size:13.5px; line-height:1.55;
    padding:10px 13px; word-break:break-word;
    font-family:'Inter',sans-serif;
  }
  .ag-msg.bot {
    background:#1c1a28; color:#c8c4d0;
    border:1px solid rgba(255,255,255,0.05);
    border-radius:14px 14px 14px 3px;
  }
  .ag-msg.user {
    background:linear-gradient(135deg,rgba(232,184,75,0.16),rgba(201,150,12,0.1));
    color:#fff; border:1px solid rgba(232,184,75,0.15);
    border-radius:14px 14px 3px 14px;
  }
  .ag-msg.typing { color:#a0a0b8; }
  .ag-typing-dots { display:inline-flex; gap:4px; align-items:center; padding:2px 0; }
  .ag-typing-dots span {
    width:6px; height:6px; border-radius:50%; background:#e8b84b; opacity:0.4;
    animation:ag-dot 1.2s ease infinite;
  }
  .ag-typing-dots span:nth-child(2){animation-delay:.2s;}
  .ag-typing-dots span:nth-child(3){animation-delay:.4s;}
  @keyframes ag-dot { 0%,80%,100%{opacity:.3;transform:scale(.8);} 40%{opacity:1;transform:scale(1);} }
  .ag-msg a { color:#e8b84b; text-decoration:underline; }

  /* ── Input row ── */
  .ag-ai-input-row {
    display:flex; gap:8px; padding:10px 12px;
    border-top:1px solid rgba(255,255,255,0.06);
    background:#0f0d18; flex-shrink:0; align-items:flex-end;
  }
  #ag-ai-input {
    flex:1; background:#1a1828; border:1px solid rgba(232,184,75,0.15);
    border-radius:12px; color:#fff; font-size:13px;
    padding:9px 13px; outline:none;
    font-family:'Inter',sans-serif; resize:none; line-height:1.4;
    transition:border-color .2s;
  }
  #ag-ai-input:focus { border-color:rgba(232,184,75,0.4); }
  #ag-ai-input::placeholder { color:#555470; }
  #ag-ai-mic {
    width:36px; height:36px; border-radius:10px; flex-shrink:0;
    background:rgba(232,184,75,0.08);
    border:1px solid rgba(232,184,75,0.2);
    color:#e8b84b; font-size:15px; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:background .2s;
  }
  #ag-ai-mic:hover { background:rgba(232,184,75,0.15); }
  #ag-ai-mic.recording { background:rgba(242,109,109,.15); border-color:#f26d6d; color:#f26d6d; animation:ag-pulse 1s infinite; }
  @keyframes ag-pulse { 0%,100%{opacity:1;} 50%{opacity:.5;} }
  #ag-ai-send {
    width:36px; height:36px; border-radius:10px; border:none; flex-shrink:0;
    background:linear-gradient(135deg,#b8820a,#e8b84b);
    color:#0d0d0f; font-size:15px; cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:opacity .2s, transform .15s;
  }
  #ag-ai-send:hover { opacity:.9; transform:scale(1.05); }
  #ag-ai-send:disabled { opacity:.3; cursor:not-allowed; transform:none; }

  @media(max-width:640px){
    #ag-ai-panel{ width:calc(100vw - 28px); right:14px; bottom:86px; }
    #ag-ai-bubble{ bottom:20px; right:14px; }
  }
  `;

  const styleEl = document.createElement('style');
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  /* ── SVG Avatar (cute robot face) ── */
  const AVATAR_LG = `<svg viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
    <!-- Head -->
    <rect x="6" y="9" width="22" height="18" rx="5" fill="#1a1628" stroke="#e8b84b" stroke-width="1.5"/>
    <!-- Antenna -->
    <line x1="17" y1="4" x2="17" y2="9" stroke="#e8b84b" stroke-width="1.5" stroke-linecap="round"/>
    <circle cx="17" cy="3.5" r="1.8" fill="#e8b84b"/>
    <!-- Eyes -->
    <rect x="10" y="14" width="5" height="5" rx="1.5" fill="#e8b84b" opacity="0.9"/>
    <rect x="19" y="14" width="5" height="5" rx="1.5" fill="#e8b84b" opacity="0.9"/>
    <!-- Eye shine -->
    <rect x="11" y="15" width="1.5" height="1.5" rx=".5" fill="#fff" opacity="0.6"/>
    <rect x="20" y="15" width="1.5" height="1.5" rx=".5" fill="#fff" opacity="0.6"/>
    <!-- Mouth smile -->
    <path d="M12 22 Q17 26 22 22" stroke="#e8b84b" stroke-width="1.5" stroke-linecap="round" fill="none"/>
    <!-- Ear bolts -->
    <rect x="3" y="15" width="3" height="5" rx="1.5" fill="#e8b84b" opacity="0.5"/>
    <rect x="28" y="15" width="3" height="5" rx="1.5" fill="#e8b84b" opacity="0.5"/>
  </svg>`;

  const AVATAR_SM = `<svg viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="6" width="16" height="13" rx="4" fill="#1a1628" stroke="#e8b84b" stroke-width="1.2"/>
    <line x1="11" y1="2.5" x2="11" y2="6" stroke="#e8b84b" stroke-width="1.2" stroke-linecap="round"/>
    <circle cx="11" cy="2" r="1.3" fill="#e8b84b"/>
    <rect x="6" y="9.5" width="3.5" height="3.5" rx="1" fill="#e8b84b" opacity="0.9"/>
    <rect x="12.5" y="9.5" width="3.5" height="3.5" rx="1" fill="#e8b84b" opacity="0.9"/>
    <path d="M7.5 15.5 Q11 18 14.5 15.5" stroke="#e8b84b" stroke-width="1.2" stroke-linecap="round" fill="none"/>
  </svg>`;

  const USER_ICON = `<svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="7" cy="5" r="3" fill="rgba(232,184,75,0.5)"/>
    <path d="M1 13c0-3 2.5-5 6-5s6 2 6 5" stroke="rgba(232,184,75,0.5)" stroke-width="1.2" stroke-linecap="round" fill="none"/>
  </svg>`;

  /* ── HTML ── */
  const html = `
  <button id="ag-ai-bubble" onclick="agAI.toggle()" title="Ask AG Assistant">
    ${AVATAR_LG}
    <span class="ag-notif" id="ag-notif"></span>
  </button>
  <div id="ag-ai-panel">
    <div class="ag-ai-hdr">
      <div class="ag-hdr-avatar">${AVATAR_SM}</div>
      <div class="ag-ai-hdr-text">
        <div class="ag-ai-hdr-name">AG Assistant</div>
        <div class="ag-online-row">
          <span class="ag-online-dot"></span>
          <span class="ag-online-txt">Online — Ask Me Anything</span>
        </div>
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
      <div class="ag-msg-row">
        <div class="ag-msg-avatar">${AVATAR_SM}</div>
        <div class="ag-msg bot">Namaste! 👋 Main <strong>AG Assistant</strong> hun. AG Technicals ke baare mein kuch bhi pucho — products, courses, indicators, bridge — sab bata dunga!</div>
      </div>
    </div>
    <div class="ag-ai-input-row">
      <textarea id="ag-ai-input" rows="1" placeholder="Kuch bhi pucho..."></textarea>
      <button id="ag-ai-mic" onclick="agAI.startMic()" title="Voice input">🎤</button>
      <button id="ag-ai-send" onclick="agAI.send()">
        <svg viewBox="0 0 16 16" fill="none" width="16" height="16"><path d="M2 8l12-6-5 6 5 6z" fill="currentColor"/></svg>
      </button>
    </div>
  </div>
  `;

  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  document.body.appendChild(wrapper);

  /* ── Logic ── */
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
      const typingEl = this._addTyping();

      try{
        const controller = new AbortController();
        const timeout = setTimeout(()=>controller.abort(), 60000);
        const res = await fetch('https://ag-technicals-production.up.railway.app/api/chat',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ messages: this.msgs }),
          signal: controller.signal
        });
        clearTimeout(timeout);
        const data = await res.json();
        const reply = data.reply || 'Sorry, kuch problem ho gayi. WhatsApp karo: wa.me/919876543210';
        typingEl.innerHTML = reply.replace(/\n/g,'<br>');
        typingEl.classList.remove('typing');
        this.msgs.push({role:'assistant', content: reply});
        if(this.msgs.length > 20) this.msgs = this.msgs.slice(-16);
      } catch(e){
        typingEl.textContent = 'Network error. Please try again.';
        typingEl.classList.remove('typing');
      }
      sendBtn.disabled = false;
      this._scroll();
    },

    _addMsg(text, type){
      const isUser = type === 'user';
      const row = document.createElement('div');
      row.className = 'ag-msg-row' + (isUser ? ' user' : '');

      const avatar = document.createElement('div');
      avatar.className = 'ag-msg-avatar';
      avatar.innerHTML = isUser ? USER_ICON : AVATAR_SM;

      const bubble = document.createElement('div');
      bubble.className = 'ag-msg ' + (isUser ? 'user' : 'bot');
      bubble.textContent = text;

      if(isUser){ row.appendChild(bubble); row.appendChild(avatar); }
      else { row.appendChild(avatar); row.appendChild(bubble); }

      document.getElementById('ag-ai-msgs').appendChild(row);
      this._scroll();
      return bubble;
    },

    _addTyping(){
      const row = document.createElement('div');
      row.className = 'ag-msg-row';
      const avatar = document.createElement('div');
      avatar.className = 'ag-msg-avatar';
      avatar.innerHTML = AVATAR_SM;
      const bubble = document.createElement('div');
      bubble.className = 'ag-msg bot typing';
      bubble.innerHTML = '<div class="ag-typing-dots"><span></span><span></span><span></span></div>';
      row.appendChild(avatar); row.appendChild(bubble);
      document.getElementById('ag-ai-msgs').appendChild(row);
      this._scroll();
      return bubble;
    },

    _scroll(){
      const box = document.getElementById('ag-ai-msgs');
      if(box) box.scrollTop = 99999;
    },

    startMic(){
      if(!('webkitSpeechRecognition' in window||'SpeechRecognition' in window)){
        alert('Voice input supported in Chrome only.');
        return;
      }
      const SR = window.SpeechRecognition||window.webkitSpeechRecognition;
      const rec = new SR();
      rec.lang = 'hi-IN';
      rec.interimResults = false;
      const btn = document.getElementById('ag-ai-mic');
      btn.classList.add('recording');
      btn.textContent = '⏹';
      rec.onresult = (e) => {
        const txt = e.results[0][0].transcript;
        document.getElementById('ag-ai-input').value = txt;
        btn.classList.remove('recording'); btn.textContent = '🎤';
        agAI.send();
      };
      rec.onerror = rec.onend = () => {
        btn.classList.remove('recording'); btn.textContent = '🎤';
      };
      rec.start();
    }
  };

  window.agAI = agAI;

  document.getElementById('ag-ai-input').addEventListener('input', function(){
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 100) + 'px';
  });
  document.getElementById('ag-ai-input').addEventListener('keydown', function(e){
    if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); agAI.send(); }
  });

  setTimeout(()=>{
    if(!agAI.open) document.getElementById('ag-notif').style.display = 'block';
  }, 8000);

  // Keep backend warm
  setInterval(()=>{ fetch('https://ag-technicals-production.up.railway.app/',{method:'GET'}).catch(()=>{}); }, 4*60*1000);
  setTimeout(()=>{ fetch('https://ag-technicals-production.up.railway.app/',{method:'GET'}).catch(()=>{}); }, 2000);

})();
