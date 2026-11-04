function v30Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function v30StatusClass(s){s=String(s||'UNKNOWN').toUpperCase();return ['PASS','OK','HEALTHY','ELIGIBLE_FOR_REVIEW','PROMOTION_REVIEW','PAPER_ELIGIBLE'].includes(s)?'up':['WARN','WATCH','PAPER_INCUBATION','RESEARCH_ONLY'].includes(s)?'amber':'down'}
function v30Card(title,value,sub){return '<div class="stat"><span>'+v30Esc(title)+'</span><b class="'+v30StatusClass(value)+'">'+v30Esc(value??'—')+'</b><small>'+v30Esc(sub||'')+'</small></div>'}
function researchControlView30(){
 return '<div class="grid2">'+
 '<section class="panel"><div class="panelHead"><div><h2>Araştırma Bütünlük Merkezi</h2><p>Ledger · lineage · PIT universe · model reproducibility · protected features · forward scorecard</p></div><button id="integrityRefresh30" class="toolbtn">Yenile</button></div><div id="integrityBox30"><div class="loading">Bütünlük kontrolleri yükleniyor…</div></div></section>'+
 '<section class="panel"><div class="panelHead"><div><h2>Otonom Araştırma Döngüsü</h2><p>Walk-forward doğrulama → maliyet/kapasite gerçeği → paper tournament → forward governance</p></div><button id="researchRun30" class="toolbtn">Araştırma Döngüsünü Çalıştır</button></div>'+
 '<div class="warningBox">Bu motor yalnızca araştırma ve sanal portföy katmanında çalışır. Broker emri üretmez, canlı işlem yetkisi vermez ve geçmiş backtest sonucuyla strateji terfi ettirmez.</div>'+
 '<div class="stats">'+v30Card('Evren limiti','120','varsayılan')+v30Card('Train','252 gün','walk-forward')+v30Card('Test','63 gün','prospektif pencere')+v30Card('Tek yön maliyet','20 bps','işlem maliyeti')+'</div>'+
 '<div id="researchRunBox30"><div class="loading">Son araştırma kayıtları yükleniyor…</div></div></section></div>';
}
async function loadIntegrity30(){
 const box=$('#integrityBox30'); if(!box)return;
 box.innerHTML='<div class="loading">Bütünlük kontrolleri yenileniyor…</div>';
 try{
  const d=await getJSON('/api/research-integrity');
  const panels=(d.panels||[]).map(p=>'<tr><td><b>'+v30Esc(p.name)+'</b></td><td class="'+v30StatusClass(p.status)+'">'+v30Esc(p.status||'UNKNOWN')+'</td><td>'+(p.healthy?'✓':'—')+'</td></tr>').join('');
  box.innerHTML='<div class="hero"><small>Genel durum</small><b class="'+v30StatusClass(d.status)+'">'+v30Esc(d.status||'UNKNOWN')+'</b><small>'+v30Esc((d.blockers||[]).length+' blocker · '+(d.warnings||[]).length+' warning')+'</small></div>'+
  '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Kontrol</th><th>Durum</th><th>Sağlıklı</th></tr></thead><tbody>'+panels+'</tbody></table></div>'+
  ((d.blockers||[]).length?'<div class="warningBox"><b>Blokerler:</b> '+v30Esc(d.blockers.join(' · '))+'</div>':'')+
  ((d.warnings||[]).length?'<p class="muted">Uyarılar: '+v30Esc(d.warnings.join(' · '))+'</p>':'')+
  '<p class="muted">'+v30Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v30Esc(e.message)+'</div>'}
}
function runRow30(x){
 const dt=x.created_epoch?new Date(x.created_epoch*1000).toLocaleString('tr-TR'):'—';
 return '<tr><td>'+v30Esc(dt)+'</td><td class="'+v30StatusClass(x.status)+'"><b>'+v30Esc(x.status||'—')+'</b></td><td><code>'+v30Esc(String(x.config_hash||'').slice(0,12))+'</code></td></tr>';
}
async function loadResearchStatus30(){
 const box=$('#researchRunBox30'); if(!box)return;
 try{
  const d=await getJSON('/api/autonomous-research/status?limit=12');
  const rows=(d.runs||[]).map(runRow30).join('');
  box.innerHTML='<div class="tableWrap"><table class="stockTable"><thead><tr><th>Zaman</th><th>Durum</th><th>Konfigürasyon</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v30Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v30Esc(e.message)+'</div>'}
}
async function runResearch30(){
 const btn=$('#researchRun30'),box=$('#researchRunBox30'); if(!btn||!box)return;
 btn.disabled=true;btn.textContent='Araştırma çalışıyor…';box.innerHTML='<div class="loading">Walk-forward doğrulama ve paper governance çalıştırılıyor…</div>';
 try{
  const r=await fetch('/api/autonomous-research/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:120,train_days:252,test_days:63,purge_days:5,embargo_days:5,one_way_cost_bps:20,rebalance_every:5,portfolio_value:1000000,adv_limit_pct:1,auto_create_paper:true,force_rebalance:false})});
  if(!r.ok)throw new Error(r.status+' /api/autonomous-research/run');
  const d=await r.json();
  const v=d.validation||{};
  box.innerHTML='<div class="hero"><small>Döngü sonucu</small><b class="'+v30StatusClass(d.status)+'">'+v30Esc(d.status||'UNKNOWN')+'</b><small>Tournament '+v30Esc(d.tournament_id??'oluşturulmadı')+'</small></div>'+
    '<div class="stats">'+
      v30Card('Net 5g spread',v.net_mean_spread_5d==null?'—':Number(v.net_mean_spread_5d).toFixed(4),'maliyet sonrası')+
      v30Card('Rebalance',v.rebalances??'—','walk-forward')+
      v30Card('Kapasite flag',v.capacity_flagged_rebalances??'—','likidite kontrolü')+
      v30Card('Uygun challenger',(d.eligible_challengers||[]).length,'forward review')+
    '</div>'+
    ((d.reasons||[]).length?'<div class="warningBox"><b>Geçit nedenleri:</b> '+v30Esc(d.reasons.join(' · '))+'</div>':'')+
    '<p class="muted">'+v30Esc(d.policy||'')+'</p>';
  await loadIntegrity30();
 }catch(e){box.innerHTML='<div class="empty">'+v30Esc(e.message)+'</div>'}
 finally{btn.disabled=false;btn.textContent='Araştırma Döngüsünü Çalıştır'}
}
const render30=render;
render=function(...args){
 render30(...args);
 if(state.view==='researchcontrol'){
  els.title.textContent='Araştırma Kontrol Merkezi';
  els.subtitle.textContent='Forward-only doğrulama · bütünlük denetimi · otonom paper araştırma';
  els.content.innerHTML=researchControlView30();
  $('#integrityRefresh30').onclick=loadIntegrity30;
  $('#researchRun30').onclick=runResearch30;
  loadIntegrity30();loadResearchStatus30();
 }
};
