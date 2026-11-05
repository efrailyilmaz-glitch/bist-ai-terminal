function v55e(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function v55Posture(){
 const r=String(state.market.regime||'NÖTR').toUpperCase(),b=Number(state.market.breadth||0);
 if(r.includes('RISK-OFF')||r.includes('BEAR'))return {label:'DEFANSİF / SEÇİCİ',tone:'down',note:'Yeni araştırma adaylarında güçlü teyit ve düşük risk öncelikli.'};
 if(r.includes('RISK-ON')||r.includes('BULL'))return {label:'FIRSAT ARA',tone:'up',note:'Pozitif rejim; yine de Nihai Karar Kapısı ve risk kontrolleri zorunlu.'};
 return {label:'TEYİT BEKLE',tone:'amber',note:'Geçiş/nötr rejim; kalite ve doğrulama skoru düşük adaylarda acele yok.'};
}
function v55Top(rows,key,n=5){return [...rows].filter(x=>Number.isFinite(Number(x[key]))).sort((a,b)=>Number(b[key])-Number(a[key])).slice(0,n)}
function commandCenter55(){
 const all=[...state.scan.values()],p=v55Posture(),short=v55Top(all,'short_score',5),long=v55Top(all,'long_score',5);
 const risky=[...all].sort((a,b)=>Number(b.risk||0)+Number(b.anomaly_score||0)-Number(a.risk||0)-Number(a.anomaly_score||0)).slice(0,6);
 const strong=all.filter(x=>Number(x.alpha_score||0)>=75&&x.signal_guard?.status==='CLEAR').length;
 const blocked=all.filter(x=>x.signal_guard?.status==='BLOCK'||x.trap_defense?.status==='BLOCK').length;
 return '<div class="command55">'+
 '<section class="commandHero55"><div><span>BUGÜNÜN ARAŞTIRMA DURUŞU</span><b class="'+p.tone+'">'+v55e(p.label)+'</b><p>'+v55e(p.note)+'</p></div>'+
 '<div class="commandKpis55"><div><span>Rejim</span><b>'+v55e(state.market.regime||'—')+'</b></div><div><span>Breadth</span><b>%'+v55e(state.market.breadth||0)+'</b></div><div><span>Güçlü + CLEAR</span><b>'+strong+'</b></div><div><span>Bloklanan</span><b>'+blocked+'</b></div></div></section>'+
 '<div class="grid2"><section class="panel"><div class="panelHead"><div><h2>En Güçlü Kısa Vade Adayları</h2><p>Ham skor değil; karar öncesi araştırma kuyruğu</p></div><button class="toolbtn" onclick="state.view=\'opportunity\';render()">Fırsat Avcısı</button></div>'+candidateList(short,'short_score')+'</section>'+
 '<section class="panel"><div class="panelHead"><div><h2>Sistem Güveni</h2><p>Veri, ledger, feature, confidence ve research governance</p></div><button class="toolbtn" onclick="state.view=\'integritymaster\';render()">Integrity Master</button></div><div id="commandIntegrity55"><div class="loading">Güven durumu yükleniyor…</div></div></section></div>'+
 '<div class="grid2"><section class="panel"><div class="panelHead"><div><h2>Uzun Vade Kalite Adayları</h2><p>Trend + relatif güç + momentum + risk dengesi</p></div></div>'+candidateList(long,'long_score')+'</section>'+
 '<section class="panel"><div class="panelHead"><div><h2>Risk Radarı</h2><p>Risk + anomali skoru yüksek adaylar</p></div><button class="toolbtn" onclick="state.view=\'trapdefense\';render()">Tuzak Savunması</button></div><div class="riskList55">'+risky.map(x=>'<div onclick="openStock(\''+v55e(x.ticker)+'\')"><b>'+v55e(x.ticker)+'</b><span>Risk '+v55e(x.risk??'—')+' · Anomali '+v55e(x.anomaly_score??'—')+'</span><em class="'+(Number(x.risk||0)>=70?'down':'amber')+'">'+v55e(x.signal_guard?.status||'—')+'</em></div>').join('')+'</div></section></div>'+
 '<section class="panel"><div class="panelHead"><div><h2>Operasyon & Robot Durumu</h2><p>Tarama kapsamı, supervisor ve paper/research sınırı</p></div></div><div id="commandOps55"><div class="loading">Operasyon durumu yükleniyor…</div></div></section>'+
 '</div>';
}
async function loadCommand55(){
 const ib=document.querySelector('#commandIntegrity55'),ob=document.querySelector('#commandOps55');if(!ib||!ob)return;
 try{
  const [i,b]=await Promise.all([getJSON('/api/research-integrity-master'),getJSON('/api/background/status')]);
  if(document.querySelector('#commandIntegrity55')!==ib)return;
  ib.innerHTML='<div class="stats"><div class="stat"><span>Sistem güveni</span><b class="'+(i.status==='PASS'?'up':i.status==='BLOCK'?'down':'amber')+'">'+v55e(i.system_trust_score??'—')+'/100</b></div><div class="stat"><span>Araştırma</span><b class="'+(i.research_decision_allowed?'up':'down')+'">'+(i.research_decision_allowed?'AÇIK':'BLOKE')+'</b></div><div class="stat"><span>Blocker</span><b>'+v55e((i.blockers||[]).length)+'</b></div><div class="stat"><span>Uyarı</span><b>'+v55e((i.warnings||[]).length)+'</b></div></div><p class="muted">'+v55e((i.blockers||[]).join(' · ')||(i.warnings||[]).join(' · ')||'Kritik bütünlük uyarısı yok')+'</p>';
  ob.innerHTML='<div class="commandOpsGrid55"><div><span>Tarama</span><b>'+v55e(state.scan.size)+' / '+v55e(state.total)+'</b><small>güncel fiyat/teknik kapsamı</small></div><div><span>Supervisor</span><b class="'+(b.running?'up':'amber')+'">'+(b.running?'ÇALIŞIYOR':'DURUYOR')+'</b><small>'+v55e(b.market_phase||'—')+'</small></div><div><span>Son radar</span><b>'+v55e(b.radar_last_scan||'—')+'</b><small>'+v55e(b.opportunity_count||0)+' fırsat</small></div><div><span>Canlı işlem</span><b class="down">KAPALI</b><small>research + paper only</small></div></div>';
 }catch(e){ib.innerHTML='<div class="empty">'+v55e(e.message)+'</div>';ob.innerHTML='<div class="empty">'+v55e(e.message)+'</div>'}
}
const render55=render;
render=function(...args){
 render55(...args);
 if(state.view==='overview'){
  els.title.textContent='Premium Command Center';
  els.subtitle.textContent='Bugünün araştırma duruşu · fırsatlar · risk · sistem güveni · robot operasyonu';
  els.content.innerHTML=commandCenter55();
  loadCommand55();
 }
};