/* ── ADMIN SAFETY: products always come from the database, save errors are visible ──
   Admin used to read products only from this browser's localStorage (or built-in defaults),
   so another browser / cleared storage showed stale data and a save could overwrite the DB. */
(function () {
  if (!/troublepie|admin/i.test(location.pathname)) return;
  var synced = false, tries = 0;

  function say(msg, bad) { try { toast(msg, bad ? 'err' : undefined); } catch (e) {} }

  async function syncProducts() {
    try {
      var r = await adminFetch('/api/config/ag_products');
      var j = await r.json();
      if (j && j.ok && j.value) {
        var list = JSON.parse(j.value);
        if (Array.isArray(list) && list.length) {
          // keep this browser's old copy on the server, in case it holds something the DB does not
          var local = localStorage.getItem('ag_products');
          if (local && local !== j.value) {
            try { await ccServerBackup('products-browser-copy-' + Date.now(), JSON.parse(local)); } catch (e) {}
          }
          try { await ccServerBackup('products-db-copy-' + Date.now(), list); } catch (e) {}
          localStorage.setItem('ag_products', j.value);
          products = list;
          synced = true;
          try { renderProds(); renderSidebarProducts(); } catch (e) {}
          say('Products loaded from database ✓');
          return;
        }
      }
      say('Database se products load nahi hue. Save karne se pehle puchega.', true);
    } catch (e) {
      say('Database se products load nahi hue. Save karne se pehle puchega.', true);
    }
  }

  window.save = function (k, v) {
    if (k === 'ag_products' && !synced) {
      if (!confirm('Database ke products load nahi hue. Is browser ki copy se save karoge to database overwrite ho sakta hai. Phir bhi save karna hai?')) {
        say('Save roka gaya', true);
        return;
      }
    }
    localStorage.setItem(k, JSON.stringify(v));
    adminFetch('/api/config/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: k, value: JSON.stringify(v) })
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (!j || !j.ok) say('DATABASE SAVE FAIL (' + k + '). Sirf is browser me saved hai, site pe nahi dikhega.', true);
    }).catch(function () {
      say('DATABASE SAVE FAIL (' + k + '). Sirf is browser me saved hai, site pe nahi dikhega.', true);
    });
  };

  var t = setInterval(function () {
    tries++;
    if (sessionStorage.getItem('ag_auth') === '1' && typeof adminFetch === 'function' && typeof products !== 'undefined') {
      clearInterval(t);
      syncProducts();
    } else if (tries > 600) clearInterval(t);
  }, 500);
})();
