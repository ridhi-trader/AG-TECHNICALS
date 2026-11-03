/* AG Technicals — theme switcher (Auto / Dark / Light / Sunlight). Shown on every public page. */
(function () {
  if (window.__agThemeLoaded) return; window.__agThemeLoaded = true;
  if (/troublepie|admin/i.test(location.pathname)) return;
  var OPTS = [
    ['auto', '🌓', 'Auto', 'Follows your phone/PC'],
    ['dark', '🌙', 'Dark', 'Best at night / low light'],
    ['light', '☀️', 'Light', 'Soft white'],
    ['sun', '🔆', 'Sunlight', 'High contrast, readable outdoors']
  ];
  function get() { try { return localStorage.getItem('ag_theme') || 'dark'; } catch (e) { return 'dark'; } }
  function resolve(t) {
    if (t === 'auto') { try { return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'; } catch (e) { return 'dark'; } }
    return t;
  }
  function apply(t) {
    var r = resolve(t);
    if (r === 'dark') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', r);
  }
  function fab() {
    var f = document.getElementById('ag-fab-left');
    if (!f) {
      f = document.createElement('div'); f.id = 'ag-fab-left';
      f.style.cssText = 'position:fixed;left:16px;bottom:18px;z-index:99990;display:flex;gap:8px;align-items:center;';
      document.body.appendChild(f);
    }
    return f;
  }
  function icon(t) { for (var i = 0; i < OPTS.length; i++) if (OPTS[i][0] === t) return OPTS[i][1]; return '🌙'; }

  function ui() {
    var st = document.createElement('style');
    st.textContent =
      '#ag-theme-btn{display:flex;align-items:center;justify-content:center;width:46px;height:46px;border-radius:50%;background:#0b0b0b;border:1.5px solid rgba(245,197,66,.65);font-size:21px;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.6),0 0 18px rgba(245,197,66,.25);color:#f5c542;padding:0}' +
      '#ag-theme-pop{position:fixed;left:16px;bottom:72px;z-index:99991;width:270px;background:#0b0b0b;border:1.5px solid rgba(245,197,66,.6);border-radius:16px;box-shadow:0 18px 50px rgba(0,0,0,.8);padding:8px;display:none;font-family:Inter,system-ui,sans-serif}' +
      '#ag-theme-pop.on{display:block}#ag-theme-pop .t{padding:8px 10px;font-size:11px;font-weight:800;letter-spacing:1.2px;color:#aaa;text-transform:uppercase}' +
      '#ag-theme-pop button{display:flex;gap:12px;align-items:center;width:100%;padding:10px 12px;border:0;border-radius:10px;background:transparent;color:#eee;font:700 14px Inter,system-ui,sans-serif;cursor:pointer;text-align:left}' +
      '#ag-theme-pop button:hover{background:rgba(245,197,66,.14)}#ag-theme-pop button.sel{background:rgba(245,197,66,.22);color:#f5c542}' +
      '#ag-theme-pop button i{font-style:normal;font-size:20px}#ag-theme-pop button small{display:block;color:#999;font-weight:500;font-size:11px}' +
      '@media(max-width:600px){#ag-fab-left{left:10px!important;bottom:14px!important}#ag-theme-pop{left:10px;bottom:66px}}';
    document.head.appendChild(st);
    var b = document.createElement('button');
    b.id = 'ag-theme-btn'; b.type = 'button'; b.className = 'notranslate'; b.setAttribute('translate', 'no');
    b.setAttribute('aria-label', 'Change theme'); b.textContent = icon(get());
    var p = document.createElement('div'); p.id = 'ag-theme-pop'; p.className = 'notranslate'; p.setAttribute('translate', 'no');
    function draw() {
      var cur = get();
      p.innerHTML = '<div class="t">Theme</div>' + OPTS.map(function (o) {
        return '<button type="button" data-t="' + o[0] + '"' + (o[0] === cur ? ' class="sel"' : '') + '><i>' + o[1] + '</i><span>' + o[2] + '<small>' + o[3] + '</small></span></button>';
      }).join('');
    }
    draw();
    b.addEventListener('click', function (e) { e.stopPropagation(); p.classList.toggle('on'); });
    p.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('button[data-t]') : null; if (!t) return;
      var v = t.getAttribute('data-t');
      try { localStorage.setItem('ag_theme', v); } catch (x) {}
      apply(v); b.textContent = icon(v); draw(); p.classList.remove('on');
    });
    document.addEventListener('click', function () { p.classList.remove('on'); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') p.classList.remove('on'); });
    fab().insertBefore(b, fab().firstChild); document.body.appendChild(p);
    try { window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', function () { if (get() === 'auto') apply('auto'); }); } catch (e) {}
  }
  apply(get());
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ui); else ui();
})();
