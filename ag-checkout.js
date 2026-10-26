/* AG Technicals — shared Razorpay checkout popup.
   Usage: AGCheckout.open({key:'ea:AG ATR GRID:3', name:'AG ATR GRID — 3 months', price:30000})
   The price shown is only a label; the server decides the real amount from its own data. */
(function(){
  if(window.AGCheckout) return;
  var WA='917357032456', cur=null, built=false, $;
  function inr(n){return '₹'+Number(n).toLocaleString('en-IN',{maximumFractionDigits:2});}
  function build(){
    if(built) return; built=true;
    var st=document.createElement('style');
    st.textContent='.agc-ov{position:fixed;inset:0;background:rgba(0,0,0,.82);display:none;align-items:center;justify-content:center;padding:16px;z-index:100000;font-family:Inter,system-ui,sans-serif}.agc-ov.on{display:flex}'+
    '.agc{background:#111;border:1px solid rgba(245,197,66,.35);border-radius:16px;max-width:420px;width:100%;padding:24px;color:#eee;max-height:92vh;overflow:auto}'+
    '.agc h3{margin:0 0 4px;font-size:20px;color:#fff}.agc .s{font-size:13px;color:#f5c542;margin-bottom:16px}'+
    '.agc label{display:block;font-size:12px;color:#aaa;margin:10px 0 4px}'+
    '.agc input[type=text],.agc input[type=email],.agc input[type=tel]{width:100%;box-sizing:border-box;padding:11px 12px;border-radius:9px;border:1px solid #333;background:#0a0a0a;color:#fff;font-size:14px}'+
    '.agc input:focus{outline:2px solid #f5c542;outline-offset:1px}'+
    '.agc .t{display:flex;gap:8px;align-items:flex-start;font-size:12px;color:#bbb;margin:14px 0;line-height:1.5}.agc .t input{margin-top:3px}.agc .t a{color:#f5c542}'+
    '.agc .go{width:100%;padding:13px;border:none;border-radius:10px;background:linear-gradient(135deg,#c9960c,#f5c542);color:#000;font-weight:800;font-size:15px;cursor:pointer}.agc .go:disabled{opacity:.6;cursor:wait}'+
    '.agc .x{float:right;background:none;border:none;color:#aaa;font-size:24px;cursor:pointer;line-height:1}'+
    '.agc .e{color:#f26d6d;font-size:13px;min-height:18px;margin-top:8px}.agc .n{font-size:11px;color:#888;margin-top:12px;line-height:1.5;text-align:center}'+
    '.agc .ok{text-align:center;padding:12px 0}.agc .ok b{display:block;font-size:20px;color:#4ade80;margin-bottom:8px}';
    document.head.appendChild(st);
    var d=document.createElement('div'); d.className='agc-ov'; d.id='agcOv'; d.setAttribute('role','dialog'); d.setAttribute('aria-modal','true');
    d.innerHTML='<div class="agc"><button class="x" id="agcX" aria-label="Close">×</button><div id="agcForm"><h3>Complete your purchase</h3><div class="s" id="agcSub"></div>'+
    '<label for="agcN">Full name</label><input id="agcN" type="text" autocomplete="name">'+
    '<label for="agcE">Email (receipt and access details come here)</label><input id="agcE" type="email" autocomplete="email">'+
    '<label for="agcP">WhatsApp / phone</label><input id="agcP" type="tel" autocomplete="tel">'+
    '<div class="t"><input type="checkbox" id="agcA"><span>I agree to the <a href="/terms" target="_blank" rel="noopener">Terms</a>, <a href="/refund-policy" target="_blank" rel="noopener">Refund Policy</a> and <a href="/risk-disclaimer" target="_blank" rel="noopener">Risk Disclaimer</a>. This is software only, not investment advice.</span></div>'+
    '<button class="go" id="agcGo" type="button">Pay now</button><div class="e" id="agcErr" role="alert"></div>'+
    '<div class="n">Secure payment by Razorpay (UPI, cards, netbanking). We never see your card details.</div></div>'+
    '<div class="ok" id="agcOk" hidden><b>Payment received</b>Thank you. A receipt is on its way to your email. We will contact you shortly with your access details.<br><br><button class="go" id="agcDone" type="button">Close</button></div></div>';
    document.body.appendChild(d);
    $=function(i){return document.getElementById(i);};
    $('agcX').onclick=close; $('agcDone').onclick=close;
    d.addEventListener('click',function(e){if(e.target===d)close();});
    document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});
    $('agcGo').onclick=pay;
  }
  function close(){ if($) $('agcOv').classList.remove('on'); }
  function reset(){ $('agcGo').disabled=false; $('agcGo').textContent='Pay now'; }
  function loadRzp(cb){
    if(window.Razorpay) return cb();
    var s=document.createElement('script'); s.src='https://checkout.razorpay.com/v1/checkout.js'; s.onload=cb;
    s.onerror=function(){ $('agcErr').textContent='Could not load the payment window. Check your connection and try again.'; reset(); };
    document.head.appendChild(s);
  }
  function waFallback(msg){
    $('agcErr').innerHTML=(msg||'Online payment is not available right now.')+' You can <a style="color:#f5c542" target="_blank" rel="noopener" href="https://wa.me/'+WA+'?text='+encodeURIComponent('Hi AG Technicals! I want to buy: '+cur.name)+'">order on WhatsApp</a>.';
  }
  function pay(){
    var n=$('agcN').value.trim(), e=$('agcE').value.trim(), p=$('agcP').value.trim();
    if(n.length<2){ $('agcErr').textContent='Please enter your name.'; return; }
    if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e)){ $('agcErr').textContent='Please enter a valid email.'; return; }
    if(!$('agcA').checked){ $('agcErr').textContent='Please accept the Terms and Refund Policy.'; return; }
    $('agcErr').textContent=''; $('agcGo').disabled=true; $('agcGo').textContent='Starting payment…';
    fetch('/api/pay/create-order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_key:cur.key,name:n,email:e,phone:p})})
    .then(function(r){return r.json();}).then(function(j){
      if(!j.ok){ if(/not enabled/i.test(j.error||'')) waFallback(j.error); else $('agcErr').textContent=j.error||'Could not start payment.'; reset(); return; }
      loadRzp(function(){
        var rz=new Razorpay({key:j.key_id,amount:j.amount,currency:j.currency,order_id:j.order_id,name:'AG Technicals',description:j.name,
          prefill:{name:n,email:e,contact:p},theme:{color:'#c9960c'},modal:{ondismiss:reset},
          handler:function(res){
            $('agcGo').textContent='Confirming…';
            fetch('/api/pay/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(res)})
            .then(function(r){return r.json();}).then(function(v){
              if(v.ok){ $('agcForm').hidden=true; $('agcOk').hidden=false; }
              else $('agcErr').textContent=v.error||'We could not confirm the payment. If money was deducted, write to support@agtechnicals.com with payment ID: '+res.razorpay_payment_id;
              reset();
            }).catch(function(){ $('agcErr').textContent='Network issue while confirming. If money was deducted, write to support@agtechnicals.com with payment ID: '+res.razorpay_payment_id; reset(); });
          }});
        rz.on('payment.failed',function(){ $('agcErr').textContent='Payment failed. You were not charged. Please try again.'; reset(); });
        rz.open();
      });
    }).catch(function(){ $('agcErr').textContent='Network error. Please try again.'; reset(); });
  }
  window.AGCheckout={open:function(it){
    build(); cur=it; $('agcSub').textContent=it.name+(it.price?' · '+inr(it.price):'');
    $('agcErr').textContent=''; $('agcForm').hidden=false; $('agcOk').hidden=true; reset();
    $('agcOv').classList.add('on'); setTimeout(function(){$('agcN').focus();},50);
  }};
})();
