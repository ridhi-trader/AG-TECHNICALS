/* AG Technicals - live price strip. Real prices only (from /api/market-data); hides itself if none are available. */
(function () {
  var SYMBOLS = [
    { key: 'XAU/USD', icon: '🥇', color: '#f5c542' },
    { key: 'BTC/USD', icon: '₿', color: '#f7931a' },
    { key: 'ETH/USD', icon: 'Ξ', color: '#627eea' },
    { key: 'EUR/USD', icon: '€', color: '#4ade80' },
    { key: 'GBP/USD', icon: '£', color: '#a78bfa' }
  ];
  function build(prices) {
    var parts = [];
    SYMBOLS.forEach(function (s) {
      var d = prices[s.key];
      if (!d || !d.price) return;
      var p = parseFloat(d.price).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: s.key.indexOf('/USD') > 0 && d.price < 10 ? 4 : 2 });
      var c = typeof d.change_24h === 'number' ? d.change_24h : null;
      var chg = c === null ? '' : ' <span style="color:' + (c >= 0 ? '#4ade80' : '#f26d6d') + ';font-size:11px;">' + (c >= 0 ? '▲ +' : '▼ ') + Math.abs(c).toFixed(2) + '%</span>';
      parts.push('<span style="margin:0 24px;white-space:nowrap;"><span style="color:' + s.color + ';font-weight:700;">' + s.icon + ' ' + s.key + '</span> <span style="color:#fff;">' + p + '</span>' + chg + '</span>');
    });
    return parts.join('<span style="color:#262626;margin:0 8px;">|</span>');
  }
  function refresh() {
    var track = document.getElementById('tickerTrack');
    if (!track) return;
    var wrap = track.closest ? track.closest('.ticker-wrap') : null;
    fetch('/api/market-data').then(function (r) { return r.json(); }).then(function (d) {
      var html = build((d && d.prices) || {});
      if (!html) { if (wrap) wrap.style.display = 'none'; return; }
      track.innerHTML = html + html;
      if (wrap) wrap.style.display = '';
    }).catch(function () { if (wrap) wrap.style.display = 'none'; });
  }
  refresh();
  setInterval(refresh, 300000);
})();
