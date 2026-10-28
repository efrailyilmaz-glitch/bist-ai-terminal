try{V15_GUIDES.trapdefense='Tuzak Savunması V2, çok barlı fiyat/hacim davranışında sahte kırılım, tek-bar breakout reddi, zayıf marjlı breakout, gap-up fade, yüksek hacim-düşük ilerleme, hacim zirvesi-küçük gövde, üst fitil kümeleri, parabolik uzama, volatilite şoku ve pump-fade benzeri riskleri arar. BLOCK olan hisseler güçlü teknik skor üretse bile karar motorunda veto edilir. OHLCV ile spoofing veya niyet doğrulanamaz.'}catch(e){}
function trapBadge29(t){const s=t?.status||'UNKNOWN',c=s==='CLEAR'?'up':s==='WAIT'?'amber':'down';return '<b class="'+c+'">'+s+' · '+(t?.score??'—')+'/100</b>'}
function trapView29(){return '<section class="panel"><div class="panelHead"><div><h2>Tuzak Savunması</h2><p>Sahte breakout · tek-bar rejection · gap fade · marjinal breakout · hacim churn · küçük gövde/hacim zirvesi · pump-fade</p></div><button id="trapRefresh29" class="toolbtn">Tüm BIST kontrol et</button></div><div class="warningBox">Bu ekran “tahtacı” veya belirli kişi/kurum tespiti yapmaz. Level-2 / AKDE / emir ekleme-iptal verisi olmadan spoofing kesin doğrulanamaz. Ama OHLCV ile modeli kandırabilecek yaygın fiyat-hacim yapıları karar öncesi veto edilir.</div><div id="trapBox29"><div class="loading">Tuzak riskleri yükleniyor…</div></div></section>'}
async function trapLoad29(){
 const b=$('#trapBox29');
 try{
  const d=await getJSON('/api/trap-defense-radar?limit=100');
  const rows=(d.rows||[]).map(x=>{
   const t=x.trap_defense||{};
   const codes=(t.flags||[]).slice(0,3).map(f=>f.code).join(' · ')||'—';
   return `<tr data-trap-stock="${x.ticker}"><td><b>${x.ticker}</b></td><td>${trapBadge29(t)}</td><td>${t.score??'—'}</td><td>${x.short_score??'—'}</td><td>${x.long_score??'—'}</td><td>${x.alpha_score??'—'}</td><td>${x.risk??'—'}</td><td>${codes}</td></tr>`;
  }).join('');
  b.innerHTML='<div class="tableWrap"><table class="stockTable"><thead><tr><th>Kod</th><th>Tuzak Durumu</th><th>Skor</th><th>Kısa</th><th>Uzun</th><th>Alpha</th><th>Risk</th><th>İşaretler</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+d.note+'</p>';
  b.querySelectorAll('[data-trap-stock]').forEach(el=>el.onclick=()=>openStock(el.dataset.trapStock));
  if(typeof v15SortTables==='function')v15SortTables();
 }catch(e){b.innerHTML='<div class="empty">'+e.message+'</div>'}
}
function trapDetailHTML29(r){const t=r?.trap_defense;if(!t)return '<div class="guardCard"><b>Trap Defense verisi yok</b><p>Güvenli kabul edilmez; taramayı yenileyin.</p></div>';const persist='<p>İki-bar teyit · Bull '+(r?.bull_persistence_2??'—')+'/3 · Bear '+(r?.bear_persistence_2??'—')+'/3</p>';return '<div class="guardCard"><b>Tuzak Savunması · '+trapBadge29(t)+'</b>'+persist+(t.flags||[]).map(f=>'<p>• '+v19Esc(f.message)+'</p>').join('')+'<small>'+v19Esc(t.limits||'')+'</small></div>'}
const detail29=detailShell;detailShell=function(){return detail29().replace('<div id="guardDetail">','<div id="trapDetail29">'+trapDetailHTML29(state.scan.get(state.current))+'</div><div id="guardDetail">')};
const metrics29=refreshDetailMetrics;refreshDetailMetrics=function(t){metrics29(t);if(state.view==='detail'&&state.current===t&&$('#trapDetail29'))$('#trapDetail29').innerHTML=trapDetailHTML29(state.scan.get(t));};
const render29=render;render=function(...args){render29(...args);if(state.view==='trapdefense'){els.title.textContent='Tuzak Savunması';els.content.innerHTML=trapView29();$('#trapRefresh29').onclick=trapLoad29;trapLoad29();}}
