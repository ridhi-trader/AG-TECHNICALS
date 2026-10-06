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

  var LINKS = [
    { label: 'Privacy Policy',   href: 'privacy-policy' },
    { label: 'Terms Of Service', href: 'terms' },
    { label: 'Contact Us',       href: onHome ? '#contact' : 'index#contact' },
    { label: 'Risk Disclaimer',  href: 'risk-disclaimer' },
    { label: 'Support',          href: 'mailto:' + SUPPORT_EMAIL, id: 'ag-footer-support' }
  ];

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
    document.body.appendChild(f);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();
})();
