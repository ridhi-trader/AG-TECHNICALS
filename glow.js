/* AG Technicals — cursor glow effect */
(function(){
  var el = document.createElement('div');
  el.id = 'ag-cursor-glow';
  el.style.cssText = [
    'position:fixed',
    'pointer-events:none',
    'z-index:99998',
    'width:420px',
    'height:420px',
    'border-radius:50%',
    'background:radial-gradient(circle,rgba(245,197,66,0.13) 0%,rgba(245,197,66,0.05) 35%,transparent 70%)',
    'transform:translate(-50%,-50%)',
    'transition:opacity 0.4s',
    'opacity:0',
    'top:0',
    'left:0',
    'will-change:transform,left,top'
  ].join(';');
  document.body.appendChild(el);

  var cx = -999, cy = -999, tx = -999, ty = -999;
  var raf, active = false;

  function lerp(a,b,t){return a+(b-a)*t;}

  function tick(){
    cx = lerp(cx, tx, 0.10);
    cy = lerp(cy, ty, 0.10);
    el.style.left = cx + 'px';
    el.style.top  = cy + 'px';
    raf = requestAnimationFrame(tick);
  }

  document.addEventListener('mousemove', function(e){
    tx = e.clientX;
    ty = e.clientY;
    if(!active){
      active = true;
      cx = tx; cy = ty;
      el.style.opacity = '1';
      raf = requestAnimationFrame(tick);
    }
  }, {passive:true});

  document.addEventListener('mouseleave', function(){
    el.style.opacity = '0';
    active = false;
    cancelAnimationFrame(raf);
  });

  /* extra: subtle glow burst on click */
  document.addEventListener('mousedown', function(){
    el.style.background = 'radial-gradient(circle,rgba(245,197,66,0.28) 0%,rgba(245,197,66,0.09) 30%,transparent 65%)';
  });
  document.addEventListener('mouseup', function(){
    el.style.background = 'radial-gradient(circle,rgba(245,197,66,0.13) 0%,rgba(245,197,66,0.05) 35%,transparent 70%)';
  });
})();
