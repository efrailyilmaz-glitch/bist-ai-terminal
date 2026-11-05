function v31Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function v31Tone(s){s=String(s||'').toUpperCase();if(['ELIGIBLE','STABLE','PASS','OK','NOMINATE'].includes(s))return 'up';if(['OBSERVE','WATCH','HOLD','INSUFFICIENT','NOT_STARTED'].includes(s))return 'amber';return 'down'}
function v31TrustCenter(){
 return '<div class="grid2">'+
 '<section class="panel"><div class="panelHead"><div><h2>Robot Güven Sıralaması</h2><p>Forward paper performansı · benchmark · drawdown · işlem sayısı · decay · governance</p></div><button id="robotTrustRefresh31" class="toolbtn">Yenile</button></div><div id="robotTrustBox31"><div class="loading">Robot güven verileri yükleniyor…</div></div></section>'+
 '<section class="panel"><div class="panelHead"><div><h2>Model Registry & Reproducibility</h2><p>Model parmak izi · feature schema · data fingerprint · dependency fingerprint</p></div><button id="modelRegistryRefresh31" class="toolbtn">Yenile</button></div><div id="modelRegistryBox31"><div class="loading">Model kayıtları yükleniyor…</div></div></section>'+
 '</div><section class="panel"><div class="panelHead"><div><h2>Karar Açıklaması</h2><p>“Neden bu robot önde?” sorusuna tek satırlık governance açıklaması</p></div></div><div id="robotExplain31"><div class="loading">Açıklama hazırlanıyor…</div></div></section>';
}
function v31ReasonText(r){
 const map={MIN_90_DAYS:'90 günlük ileri test süresi dolmadı',MIN_30_TRADES:'30 kapanmış işlem eşiği dolmadı',DRAWDOWN:'Azami düşüş sınırı aşıldı',PROFIT_FACTOR:'Kâr faktörü yetersiz',BENCHMARK:'Benchmark üzerinde getiri üretmedi',STRATEGY_DECAY:'Strateji decay sinyali verdi'};
 return (r||[]).map(x=>map[x]||x).join(' · ')||'Governance engeli yok';
}
async function loadRobotTrust31(){
 const box=$('#robotTrustBox31'),ex=$('#robotExplain31');if(!box)return;
 try{
  let a=null;
  if(typeof autoToken==='function'&&autoToken()){
    try{a=await arenaAPI('account')}catch(e){}
  }
  if(!a||!a.exists){
    const c=await getJSON('/api/robot-arena/catalog');
    box.innerHTML='<div class="warningBox">Henüz aktif forward-paper laboratuvarı yok. Güven sıralaması yalnız prospektif deney verisi oluşunca hesaplanır.</div>'+
      '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Robot</th><th>Kural</th></tr></thead><tbody>'+((c.bots||[]).map(b=>'<tr><td><b>'+v31Esc(b.name)+'</b></td><td>'+v31Esc(b.rules||'')+'</td></tr>').join(''))+'</tbody></table></div>';
    ex.innerHTML='<p>Geçmiş backtest veya katalog bilgisi tek başına şampiyon seçmek için kullanılmaz. Önce aynı sermaye ve aynı masraflarla forward paper deneyinin başlaması gerekir.</p>';
    return;
  }
  const ranking=(a.meta_governance||{}).ranking||[];
  const byId=Object.fromEntries((a.bots||[]).map(b=>[b.id,b]));
  const rows=ranking.map((r,i)=>{
    const b=byId[r.id]||{},m=b.metrics||{},d=b.decay||{};
    return '<tr><td>'+(i+1)+'</td><td><b>'+v31Esc(r.name||r.id)+'</b></td><td class="'+v31Tone(r.status)+'">'+v31Esc(r.status)+'</td><td>'+v31Esc(r.score)+'</td><td>'+v31Esc(m.return_pct??'—')+'%</td><td>'+v31Esc(m.max_drawdown_pct??'—')+'%</td><td>'+v31Esc(m.closed_trades??0)+'</td><td>'+v31Esc(m.profit_factor??'—')+'</td><td class="'+v31Tone(d.status)+'">'+v31Esc(d.status||'—')+'</td><td>'+v31Esc(v31ReasonText(r.reasons))+'</td></tr>';
  }).join('');
  box.innerHTML='<div class="hero"><small>Forward paper gün sayısı</small><b>'+v31Esc((a.meta_governance||{}).days??0)+'</b><small>Benchmark cash-adjusted '+v31Esc(a.benchmark?.cash_adjusted_pct??'—')+'%</small></div>'+
   '<div class="tableWrap"><table class="stockTable"><thead><tr><th>#</th><th>Robot</th><th>Durum</th><th>Güven skoru</th><th>Getiri</th><th>Max DD</th><th>İşlem</th><th>PF</th><th>Decay</th><th>Neden</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
  const dec=(a.meta_governance||{}).decision||{};
  const top=ranking[0];
  ex.innerHTML='<div class="stats">'+
    '<div class="stat"><span>Governance aksiyonu</span><b class="'+v31Tone(dec.action)+'">'+v31Esc(dec.action||'HOLD')+'</b><small>'+v31Esc(dec.reason||'—')+'</small></div>'+
    '<div class="stat"><span>Öndeki robot</span><b>'+v31Esc(top?.name||'—')+'</b><small>Skor '+v31Esc(top?.score??'—')+'</small></div>'+
    '<div class="stat"><span>Uygun robot</span><b>'+ranking.filter(x=>x.status==='ELIGIBLE').length+'</b><small>'+ranking.length+' toplam aday</small></div>'+
    '<div class="stat"><span>Canlı işlem</span><b class="down">KAPALI</b><small>forward paper only</small></div></div>'+
    '<p>'+v31Esc(top?((top.status==='ELIGIBLE'?'Öndeki robot governance eşiklerini geçmiş durumda. ':'Öndeki robot henüz tam uygun değil. ')+v31ReasonText(top.reasons)):'Henüz sıralama oluşmadı.')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v31Esc(e.message)+'</div>';ex.innerHTML='<div class="empty">'+v31Esc(e.message)+'</div>'}
}
async function loadModelRegistry31(){
 const box=$('#modelRegistryBox31');if(!box)return;
 try{
  const d=await getJSON('/api/model-registry?limit=20');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v31Esc(x.model_name||'—')+'</b></td><td>'+v31Esc(x.model_version||'—')+'</td><td>'+v31Esc(x.as_of||'—')+'</td><td><code>'+v31Esc(String(x.model_fingerprint||'').slice(0,12))+'</code></td><td><code>'+v31Esc(String(x.data_fingerprint||'').slice(0,10))+'</code></td><td><code>'+v31Esc(String(x.feature_schema_hash||'').slice(0,10))+'</code></td></tr>').join('');
  box.innerHTML=rows?'<div class="tableWrap"><table class="stockTable"><thead><tr><th>Model</th><th>Sürüm</th><th>As-of</th><th>Model FP</th><th>Data FP</th><th>Feature FP</th></tr></thead><tbody>'+rows+'</tbody></table></div>':'<div class="empty">Henüz kayıtlı model artifact yok.</div>';
 }catch(e){box.innerHTML='<div class="empty">'+v31Esc(e.message)+'</div>'}
}
const render31=render;
render=function(...args){
 render31(...args);
 if(state.view==='modeltrust'){
  els.title.textContent='Model / Robot Güven Merkezi';
  els.subtitle.textContent='Forward performans · decay · benchmark · governance · reproducibility';
  els.content.innerHTML=v31TrustCenter();
  $('#robotTrustRefresh31').onclick=loadRobotTrust31;
  $('#modelRegistryRefresh31').onclick=loadModelRegistry31;
  loadRobotTrust31();loadModelRegistry31();
 }
};
