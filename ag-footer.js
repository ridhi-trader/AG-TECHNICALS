/* AG Technicals — shared site footer
 *
 * One place to edit the footer links for the whole site.
 *  - Pages that already have a ".f-links" row (index.html) just get the extra links appended.
 *  - Pages with a <footer> but no links row (gold-dossier) get a links row added inside it.
 *  - Every other page gets a standard footer appended to <body>.
 *
 * nginx injects this script into every HTML response (see nginx.conf, sub_filter), so brand-new
 * pages and products get the footer automatically. The guard below makes double loading harmless.
 */
(function () {
  if (window.__agFooterLoaded) return;
  window.__agFooterLoaded = true;

  // Skip pages shown inside an iframe (e.g. guides opened in the education modal) and admin pages.
  try { if (window.top !== window.self) return; } catch (e) { return; }
  var path = (location.pathname || '').toLowerCase();
  if (/(^|\/)(admin|troublepie-[a-z0-9]+)(\.html)?$/.test(path)) return;

  var SUPPORT_EMAIL = 'support@agtechnicals.com';
  var onHome = /(^|\/)(index)?(\.html)?$/.test(path) || path === '';

  // WhatsApp / Telegram come from the same admin-editable 'contact' list that ag-contact.js uses.
  var CONTACT_DEFAULT = [
    { name: 'WhatsApp', url: 'https://wa.me/917357032456' },
    { name: 'Telegram', url: 'https://t.me/AG_Technical_fx' }
  ];
  function contactUrl(name) {
    var list = CONTACT_DEFAULT;
    try { var saved = JSON.parse(localStorage.getItem('contact')); if (saved && saved.length) list = saved; } catch (e) {}
    for (var i = 0; i < list.length; i++) {
      if ((list[i].name || '').toLowerCase().indexOf(name.toLowerCase()) > -1 && list[i].url && !list[i].hidden) return list[i].url;
    }
    for (var j = 0; j < CONTACT_DEFAULT.length; j++) {
      if (CONTACT_DEFAULT[j].name === name) return CONTACT_DEFAULT[j].url;
    }
    return '';
  }

  var LINKS = [
    { label: 'Privacy Policy',   href: 'privacy-policy' },
    { label: 'Terms Of Service', href: 'terms' },
    { label: 'Contact Us',       href: onHome ? '#contact' : 'index#contact' },
    { label: 'Risk Disclaimer',  href: 'risk-disclaimer' },
    { label: 'Support',          href: 'mailto:' + SUPPORT_EMAIL, id: 'ag-footer-support' },
    { label: 'WhatsApp',         href: contactUrl('WhatsApp'), ext: true },
    { label: 'Telegram',         href: contactUrl('Telegram'), ext: true }
  ].filter(function (l) { return l.href; });

  function addStyle() {
    if (document.getElementById('ag-footer-style')) return;
    var css =
      '#ag-site-footer{background:#000;border-top:1px solid #262626;padding:28px 48px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;font-family:Inter,sans-serif;}' +
      '#ag-site-footer .ag-f-copy{font-size:12px;color:#bdbdbd;}' +
      '.ag-f-links{display:flex;gap:20px;flex-wrap:wrap;}' +
      '.ag-f-links a,.f-links a#ag-footer-support{font-size:12px;color:#bdbdbd;text-decoration:none;transition:color .2s;}' +
      '.ag-f-links a:hover,.f-links a#ag-footer-support:hover{color:#f5c542;}' +
      /* keep the last row clear of the floating AI assistant bubble (bottom-right) */
      'footer,#ag-site-footer{padding-bottom:96px !important;}' +
      '@media(max-width:900px){#ag-site-footer{padding:24px 20px;padding-bottom:96px !important;}}';
    var s = document.createElement('style');
    s.id = 'ag-footer-style';
    s.textContent = css;
    document.head.appendChild(s);
  }

  function makeLink(l) {
    var a = document.createElement('a');
    a.href = l.href;
    a.textContent = l.label;
    if (l.id) a.id = l.id;
    if (l.ext) { a.target = '_blank'; a.rel = 'noopener'; }
    return a;
  }

  function build() {
    if (document.getElementById('ag-footer-support')) return;
    addStyle();

    // 1) Existing links row (index.html): append only what is missing.
    var row = document.querySelector('footer .f-links, .f-links');
    if (row) {
      LINKS.forEach(function (l) {
        var present = Array.prototype.some.call(row.querySelectorAll('a'), function (a) {
          return (a.getAttribute('href') || '').toLowerCase() === l.href.toLowerCase() ||
                 a.textContent.trim().toLowerCase() === l.label.toLowerCase();
        });
        if (!present) row.appendChild(makeLink(l));
      });
      return;
    }

    // 2) A footer exists but has no links row: add one inside it.
    var existing = document.querySelector('footer');
    var holder = document.createElement('div');
    holder.className = 'ag-f-links';
    LINKS.forEach(function (l) { holder.appendChild(makeLink(l)); });
    if (existing) {
      holder.style.marginTop = '12px';
      holder.style.justifyContent = 'center';
      existing.appendChild(holder);
      return;
    }

    // 3) No footer at all: add the standard one.
    var f = document.createElement('footer');
    f.id = 'ag-site-footer';
    var copy = document.createElement('div');
    copy.className = 'ag-f-copy';
    copy.textContent = '© ' + new Date().getFullYear() + ' AG Technicals. All rights reserved.';
    f.appendChild(copy);
    f.appendChild(holder);

    // Pages whose <body> is a side-by-side flex/grid layout (guide pages with a sidebar) would
    // squeeze the content if the footer became another column, so put it inside the content area.
    var host = document.body;
    var bs = getComputedStyle(document.body);
    var sideBySide = (bs.display === 'flex' || bs.display === 'inline-flex') && bs.flexDirection.indexOf('column') !== 0;
    if (sideBySide || bs.display === 'grid') {
      host = document.querySelector('#main, .main, main, #content, .content');
      if (!host) return; // unknown layout: better no footer than a broken page
    }
    host.appendChild(f);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
