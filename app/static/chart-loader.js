(function(){
  function load(src,onerror){
    var s=document.createElement('script');s.src=src;s.async=false;
    if(onerror)s.onerror=onerror;document.head.appendChild(s);
  }
  load('/static/vendor/lightweight-charts.standalone.production.js',function(){
    console.warn('Local chart vendor unavailable; using network fallback.');
    load('https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js');
  });
})();