/* AG Technicals — website language switcher (all pages).
   Uses Google Website Translator. The chosen language is kept in the "googtrans" cookie + localStorage.
   English = original page, no translator script is loaded at all (no speed cost). */
(function () {
  if (window.__agLangLoaded) return; window.__agLangLoaded = true;
  if (/troublepie|admin/i.test(location.pathname)) return; // never translate the admin panel
  var LANGS = [
    ['en','English','English'],['hi','हिन्दी','Hindi'],['bn','বাংলা','Bengali'],['mr','मराठी','Marathi'],['gu','ગુજરાતી','Gujarati'],
    ['ta','தமிழ்','Tamil'],['te','తెలుగు','Telugu'],['kn','ಕನ್ನಡ','Kannada'],['ml','മലയാളം','Malayalam'],['pa','ਪੰਜਾਬੀ','Punjabi'],
    ['ur','اردو','Urdu'],['ne','नेपाली','Nepali'],['or','ଓଡ଼ିଆ','Odia'],['as','অসমীয়া','Assamese'],
    ['ar','العربية','Arabic'],['es','Español','Spanish'],['fr','Français','French'],['de','Deutsch','German'],['pt','Português','Portuguese'],
    ['ru','Русский','Russian'],['zh-CN','中文','Chinese'],['ja','日本語','Japanese'],['ko','한국어','Korean'],['id','Bahasa Indonesia','Indonesian'],
    ['ms','Bahasa Melayu','Malay'],['tr','Türkçe','Turkish'],['it','Italiano','Italian'],['th','ไทย','Thai'],['vi','Tiếng Việt','Vietnamese'],
    ['fa','فارسی','Persian'],['sw','Kiswahili','Swahili'],['nl','Nederlands','Dutch'],['pl','Polski','Polish'],['uk','Українська','Ukrainian']
  ];
  function lsGet(k){ try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v){ try { localStorage.setItem(k, v); } catch (e) {} }
  function cookieLang(){
    var m = /(?:^|;\s*)googtrans=\/[^\/]*\/([^;]+)/.exec(document.cookie || '');
    return m ? decodeURIComponent(m[1]) : '';
  }
  var cur = cookieLang() || 'en';
  if (cur === 'en') cur = 'en';
  function find(code){ for (var i = 0; i < LANGS.length; i++) if (LANGS[i][0] === code) return LANGS[i]; return LANGS[0]; }
  window.agSiteLang = function(){ var l = find(cur); return { code: l[0], name: l[2] }; };

  function setCookie(val){
    var host = location.hostname, parts = host.split('.'), doms = [''];
    if (parts.length > 1) { doms.push(host); doms.push('.' + parts.slice(-2).join('.')); }
    doms.forEach(function (d) {
      var base = 'googtrans=' + (val || '') + ';path=/' + (d ? ';domain=' + d : '');
      document.cookie = base + (val ? '' : ';expires=Thu, 01 Jan 1970 00:00:00 GMT');
    });
  }
  function choose(code){
    lsSet('ag_site_lang', code);
    setCookie(code === 'en' ? '' : '/en/' + code);
    location.reload();
  }

  // keep brand names untouched by the translator
  function protect(){
    ['.brand','.brand-txt','.lp-name','#ag-footer-pw','.jd','.ag-ai-hdr-name'].forEach(function (s) {
      var n = document.querySelectorAll(s);
      for (var i = 0; i < n.length; i++) { n[i].classList.add('notranslate'); n[i].setAttribute('translate', 'no'); }
    });
  }

  function css(){
    var s = document.createElement('style');
    s.textContent =
      '.goog-te-banner-frame,.skiptranslate>iframe,#goog-gt-tt,.goog-te-balloon-frame{display:none!important}' +
      'body{top:0!important;position:static!important}.goog-text-highlight{background:none!important;box-shadow:none!important}' +
      '#google_translate_element{position:absolute;left:-9999px;top:0;height:0;overflow:hidden}' +
      '#ag-lang-btn{position:fixed;left:16px;bottom:18px;z-index:99990;display:flex;align-items:center;gap:8px;padding:11px 16px;border-radius:99px;background:#0b0b0b;border:1.5px solid rgba(245,197,66,.65);color:#f5c542;font:800 14px Inter,system-ui,sans-serif;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.6),0 0 18px rgba(245,197,66,.25);}' +
      '#ag-lang-btn:hover{background:#17130a}' +
      '#ag-lang-pop{position:fixed;left:16px;bottom:72px;z-index:99991;width:260px;max-height:min(60vh,420px);overflow:auto;background:#0b0b0b;border:1.5px solid rgba(245,197,66,.6);border-radius:16px;box-shadow:0 18px 50px rgba(0,0,0,.8);padding:8px;display:none;font-family:Inter,system-ui,sans-serif;}' +
      '#ag-lang-pop.on{display:block}' +
      '#ag-lang-pop .t{padding:8px 10px 10px;font-size:11px;font-weight:800;letter-spacing:1.2px;color:#aaa;text-transform:uppercase}' +
      '#ag-lang-pop button{display:flex;justify-content:space-between;align-items:center;width:100%;padding:10px 12px;border:0;border-radius:10px;background:transparent;color:#eee;font:600 14px Inter,system-ui,sans-serif;cursor:pointer;text-align:left}' +
      '#ag-lang-pop button:hover{background:rgba(245,197,66,.14)}' +
      '#ag-lang-pop button.sel{background:rgba(245,197,66,.22);color:#f5c542}' +
      '#ag-lang-pop button small{color:#999;font-weight:500;font-size:12px}' +
      '@media(max-width:600px){#ag-lang-btn{left:10px;bottom:14px;padding:10px 13px}#ag-lang-pop{left:10px;bottom:66px}}';
    document.head.appendChild(s);
  }

  function ui(){
    css();
    var b = document.createElement('button');
    b.id = 'ag-lang-btn'; b.type = 'button'; b.setAttribute('aria-label', 'Change language'); b.className = 'notranslate'; b.setAttribute('translate', 'no');
    b.innerHTML = '🌐 <span>' + find(cur)[1] + '</span>';
    var p = document.createElement('div');
    p.id = 'ag-lang-pop'; p.className = 'notranslate'; p.setAttribute('translate', 'no');
    p.innerHTML = '<div class="t">🌐 Language / भाषा</div>' + LANGS.map(function (l) {
      return '<button type="button" data-c="' + l[0] + '"' + (l[0] === cur ? ' class="sel"' : '') + '>' + l[1] + '<small>' + (l[1] === l[2] ? '' : l[2]) + '</small></button>';
    }).join('');
    b.addEventListener('click', function (e) { e.stopPropagation(); p.classList.toggle('on'); });
    p.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('button[data-c]') : null;
      if (t) choose(t.getAttribute('data-c'));
    });
    document.addEventListener('click', function () { p.classList.remove('on'); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') p.classList.remove('on'); });
    document.body.appendChild(b); document.body.appendChild(p);
  }

  function loadTranslator(){
    var d = document.createElement('div'); d.id = 'google_translate_element'; document.body.appendChild(d);
    window.agGTInit = function () {
      try {
        new google.translate.TranslateElement({
          pageLanguage: 'en', autoDisplay: false,
          includedLanguages: LANGS.map(function (l) { return l[0]; }).join(',')
        }, 'google_translate_element');
      } catch (e) {}
    };
    var s = document.createElement('script');
    s.src = 'https://translate.google.com/translate_a/element.js?cb=agGTInit';
    s.async = true; document.head.appendChild(s);
  }

  function start(){
    protect(); ui();
    if (cur !== 'en') { loadTranslator(); setTimeout(protect, 1500); }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
