/* AG Technicals — hero price-action field
 *
 * A decorative candlestick chart that draws itself once across the hero, then idles with a live-forming
 * last candle. The cursor adds a crosshair. It is generative artwork: no prices, no labels, not data.
 * Respects prefers-reduced-motion (final frame, no animation).
 */
(function () {
  var hero = document.getElementById('home');
  if (!hero) return;

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var canvas = document.createElement('canvas');
  canvas.className = 'hero-field';
  canvas.setAttribute('aria-hidden', 'true');
  hero.insertBefore(canvas, hero.firstChild);
  var ctx = canvas.getContext('2d');

  var UP = '46,230,166', DOWN = '255,92,108', GOLD = '245,197,66';
  var W = 0, H = 0, dpr = 1, candles = [], ma = [], cw = 18, gap = 6;
  var start = 0, DURATION = 2600, done = false, raf = 0, mouse = null, last = 0;

  // Seeded generator so the chart looks designed, not random noise, and is identical on every visit.
  function rng(seed) { return function () { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; }; }

  function build() {
    var rand = rng(20261025);
    var n = Math.max(24, Math.floor(W / (cw + gap)));
    candles = [];
    var p = 0, drift = 0;
    for (var i = 0; i < n; i++) {
      drift = drift * 0.82 + (rand() - 0.38) * 0.9;           // an uptrend with pullbacks: starts low on the left, breaks out at the right
      var o = p, c = o + drift + (rand() - 0.5) * 1.1;
      var hi = Math.max(o, c) + rand() * 1.3, lo = Math.min(o, c) - rand() * 1.3;
      candles.push({ o: o, c: c, h: hi, l: lo });
      p = c;
    }
    var min = Infinity, max = -Infinity;
    candles.forEach(function (k) { min = Math.min(min, k.l); max = Math.max(max, k.h); });
    var top = H * 0.10, bottom = H * 0.94, span = max - min || 1;
    candles.forEach(function (k) {
      ['o', 'c', 'h', 'l'].forEach(function (f) { k[f] = bottom - ((k[f] - min) / span) * (bottom - top); });
    });
    ma = candles.map(function (k, i) {
      var s = 0, m = 0;
      for (var j = Math.max(0, i - 8); j <= i; j++) { s += candles[j].c; m++; }
      return s / m;
    });
  }

  function resize() {
    var r = hero.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = Math.max(1, Math.floor(r.width)); H = Math.max(1, Math.floor(r.height));
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cw = W < 700 ? 10 : 18; gap = W < 700 ? 4 : 6;
    build();
    paint(done ? 1 : Math.max(0, Math.min(1, (performance.now() - start) / DURATION)));
  }

  function ease(t) { return 1 - Math.pow(1 - t, 3); }

  function paint(t) {
    ctx.clearRect(0, 0, W, H);
    var n = candles.length, shown = ease(t) * n, step = cw + gap, x0 = (W - n * step) / 2 + gap / 2;
    for (var i = 0; i < n; i++) {
      var grow = Math.min(1, Math.max(0, shown - i));
      if (grow <= 0) break;
      var k = candles[i], x = x0 + i * step, mid = x + cw / 2, up = k.c <= k.o;
      var col = up ? UP : DOWN, mix = function (v) { return k.o + (v - k.o) * grow; };
      var yo = k.o, yc = mix(k.c), yh = mix(k.h), yl = mix(k.l);
      // the live-forming last candle breathes once the intro has finished
      if (done && i === n - 1) { var b = Math.sin(performance.now() / 700) * 5; yc += b; yh = Math.min(yh, yc - 4); yl = Math.max(yl, yo + 4); }
      ctx.strokeStyle = 'rgba(' + col + ',0.45)'; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(mid, yh); ctx.lineTo(mid, yl); ctx.stroke();
      ctx.fillStyle = 'rgba(' + col + ',0.26)'; ctx.strokeStyle = 'rgba(' + col + ',0.7)';
      var top = Math.min(yo, yc), hgt = Math.max(2, Math.abs(yc - yo));
      ctx.fillRect(x, top, cw, hgt); ctx.strokeRect(x + 0.5, top + 0.5, cw - 1, hgt - 1);
    }
    // moving average, drawn with the candles
    ctx.save();
    ctx.lineWidth = 2; ctx.lineJoin = 'round'; ctx.strokeStyle = 'rgba(' + GOLD + ',0.9)';
    ctx.shadowColor = 'rgba(' + GOLD + ',0.55)'; ctx.shadowBlur = 14;
    ctx.beginPath();
    var started = false;
    for (var j = 0; j < n; j++) {
      var g = Math.min(1, Math.max(0, shown - j)); if (g <= 0) break;
      var px = x0 + j * step + cw / 2, py = ma[j];
      if (!started) { ctx.moveTo(px, py); started = true; } else ctx.lineTo(px, py);
    }
    ctx.stroke(); ctx.restore();

    if (mouse && done) {
      ctx.save(); ctx.setLineDash([4, 6]); ctx.lineWidth = 1; ctx.strokeStyle = 'rgba(' + GOLD + ',0.5)';
      ctx.beginPath(); ctx.moveTo(mouse.x, 0); ctx.lineTo(mouse.x, H); ctx.moveTo(0, mouse.y); ctx.lineTo(W, mouse.y); ctx.stroke();
      ctx.restore();
      ctx.fillStyle = 'rgba(' + GOLD + ',0.95)'; ctx.beginPath(); ctx.arc(mouse.x, mouse.y, 3, 0, 6.2832); ctx.fill();
    }
  }

  function finish() {
    done = true;
    hero.classList.add('fx-done');
  }

  function frame(now) {
    var t = Math.max(0, Math.min(1, (now - start) / DURATION));
    paint(t);
    if (t >= 1 && !done) finish();
    // after the intro only keep animating when something moves (idle candle ~ every 50ms is plenty)
    if (done && now - last < 50) { raf = requestAnimationFrame(frame); return; }
    last = now;
    raf = requestAnimationFrame(frame);
  }

  hero.classList.add('fx-armed');
  resize();
  var rt; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(resize, 120); });

  if (reduce) { done = true; paint(1); hero.classList.add('fx-done'); return; }

  // pause when the hero is off-screen or the tab is hidden
  var visible = true;
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      visible = es[0].isIntersecting;
      if (visible && !raf) raf = requestAnimationFrame(frame);
      if (!visible) { cancelAnimationFrame(raf); raf = 0; }
    }).observe(hero);
  }
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) { cancelAnimationFrame(raf); raf = 0; }
    else if (visible && !raf) raf = requestAnimationFrame(frame);
  });

  hero.addEventListener('mousemove', function (e) {
    var r = hero.getBoundingClientRect();
    mouse = { x: e.clientX - r.left, y: e.clientY - r.top };
  }, { passive: true });
  hero.addEventListener('mouseleave', function () { mouse = null; });

  start = performance.now() + 250;   // short beat so the page settles before the chart draws
  raf = requestAnimationFrame(frame);
})();
