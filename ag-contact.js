/* AG Technicals — Dynamic Contact Loader
   Reads contact links from admin localStorage and updates all pages */
(function(){
  var DEFAULT = [
    {name:'WhatsApp', icon:'💬', url:'https://wa.me/919876543210', handle:'+91 98765 43210'},
    {name:'Telegram', icon:'✈️', url:'https://t.me/agtechnical', handle:'@agtechnical'},
    {name:'Instagram', icon:'📸', url:'https://instagram.com/agtechnical', handle:'@agtechnical'}
  ];

  function getContacts(){
    try{ return JSON.parse(localStorage.getItem('contact')) || DEFAULT; }
    catch(e){ return DEFAULT; }
  }

  function getByName(contacts, name){
    return contacts.find(function(c){ return c.name.toLowerCase().indexOf(name.toLowerCase()) > -1; });
  }

  function updateLinks(){
    var contacts = getContacts();
    var wa = getByName(contacts, 'whatsapp');
    var tg = getByName(contacts, 'telegram');
    var ig = getByName(contacts, 'instagram');

    // Update all WhatsApp links
    document.querySelectorAll('a[href*="wa.me"]').forEach(function(el){
      if(wa) el.href = wa.url;
    });

    // Update all Telegram links
    document.querySelectorAll('a[href*="t.me"]').forEach(function(el){
      if(tg) el.href = tg.url;
    });

    // Update all Instagram links
    document.querySelectorAll('a[href*="instagram.com"]').forEach(function(el){
      if(ig) el.href = ig.url;
    });

    // Update displayed handles/text
    document.querySelectorAll('[data-contact="whatsapp"]').forEach(function(el){
      if(wa) el.textContent = wa.handle;
    });
    document.querySelectorAll('[data-contact="telegram"]').forEach(function(el){
      if(tg) el.textContent = tg.handle;
    });
    document.querySelectorAll('[data-contact="instagram"]').forEach(function(el){
      if(ig) el.textContent = ig.handle;
    });

    // Update logo from admin
    var logoUrl = localStorage.getItem('ag_logo_url');
    if(logoUrl){
      document.querySelectorAll('img.site-logo, img[data-logo]').forEach(function(el){
        el.src = logoUrl;
      });
    }
  }

  // Run on DOM ready
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', updateLinks);
  } else {
    updateLinks();
  }
})();

/* ── Mouse Glow Effect ── */
(function(){
  var glow = document.createElement('div');
  glow.style.cssText = 'position:fixed;pointer-events:none;z-index:99998;width:300px;height:300px;border-radius:50%;background:radial-gradient(circle,rgba(232,184,75,0.08) 0%,rgba(232,184,75,0.03) 40%,transparent 70%);transform:translate(-50%,-50%);transition:opacity 0.3s;opacity:0;';
  document.body.appendChild(glow);

  var mx=0, my=0, ax=0, ay=0;
  document.addEventListener('mousemove', function(e){
    mx = e.clientX; my = e.clientY;
    glow.style.opacity = '1';
  });
  document.addEventListener('mouseleave', function(){ glow.style.opacity = '0'; });

  function animate(){
    ax += (mx - ax) * 0.12;
    ay += (my - ay) * 0.12;
    glow.style.left = ax + 'px';
    glow.style.top = ay + 'px';
    requestAnimationFrame(animate);
  }
  animate();
})();
