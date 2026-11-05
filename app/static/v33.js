function v33Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function v33Tone(s){s=String(s||'').toUpperCase();if(['USEFUL','PASS','OK'].includes(s))return 'up';if(['MONITOR','INSUFFICIENT','WATCH'].includes(s))return 'amber';return 'down'}
function decisionLearningShell33(){
 return '<div class="grid2">'+
 '<section class="panel"><div class="panelHead"><div><h2>Karar Sonuç Kalibrasyonu</h2><p>PASS / WATCH / NO_TRADE kararlarının 5/20/60 günlük forward sonuçları</p></div><button id="settleDecisions33" class="toolbtn">Vadesi Dolanları Güncelle</button></div><div id="decisionCalibrationBox33"><div class="loading">Karar sonuçları yükleniyor…</div></div></section>'+
 '<section class="panel"><div class="panelHead"><div><h2>Gate Fayda Analizi</h2><p>Gate PASS ile FAIL gruplarının benchmark üstü forward sonuç farkı</p></div><select id="gateHorizon33"><option value="5">5 gün</option><option value="20" selected>20 gün</option><option value="60">60 gün</option></select></div><div class="warningBox">Bu ekran ilişki ölçer, nedensellik kanıtlamaz. “Fazla katı” etiketi gate’i otomatik değiştirmez; yalnızca yeniden doğrulama adayı yapar.</div><div id="gateCalibrationBox33"><div class="loading">Gate kalibrasyonu yükleniyor…</div></div></section></div>';
}
function metric33(x){if(!x||!x.n)return '<span>n=0</span>';return '<span>n='+v33Esc(x.n)+' · hit %'+v33Esc(x.hit_rate_pct)+' · ort '+v33Esc(x.mean_excess_pct)+'% · med '+v33Esc(x.median_excess_pct)+'%</span>'}
async function loadDecisionCalibration33(){
 const box=$('#decisionCalibrationBox33');if(!box)return;
 try{
  const d=await getJSON('/api/experience/calibration');
  const groups=['PASS','WATCH','NO_TRADE'];
  box.innerHTML='<div class="stats">'+
   '<div class="stat"><span>Toplam kayıt</span><b>'+v33Esc(d.total_signals??0)+'</b><small>prospektif ledger</small></div>'+
   '<div class="stat"><span>20g genel</span><b>'+v33Esc(d.overall?.['20d']?.mean_excess_pct??'—')+'%</b><small>'+v33Esc(d.overall?.['20d']?.n??0)+' settle</small></div>'+
   '<div class="stat"><span>60g genel</span><b>'+v33Esc(d.overall?.['60d']?.mean_excess_pct??'—')+'%</b><small>'+v33Esc(d.overall?.['60d']?.n??0)+' settle</small></div></div>'+
   '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Komite kararı</th><th>20 gün</th><th>60 gün</th></tr></thead><tbody>'+
   groups.map(g=>'<tr><td><b>'+g+'</b></td><td>'+metric33(d.by_committee?.[g]?.['20d'])+'</td><td>'+metric33(d.by_committee?.[g]?.['60d'])+'</td></tr>').join('')+
   '</tbody></table></div><p class="muted">'+v33Esc(d.note||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v33Esc(e.message)+'</div>'}
}
async function loadGateCalibration33(){
 const box=$('#gateCalibrationBox33'),sel=$('#gateHorizon33');if(!box||!sel)return;
 box.innerHTML='<div class="loading">Gate sonuçları hesaplanıyor…</div>';
 try{
  const d=await getJSON('/api/decision-calibration?horizon='+encodeURIComponent(sel.value)+'&min_samples=8');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v33Esc(x.gate)+'</b></td><td>'+v33Esc(x.hard?'HARD':'SOFT')+'</td><td>'+v33Esc(x.pass_n)+'</td><td>'+v33Esc(x.fail_n)+'</td><td>'+v33Esc(x.pass_mean_excess_pct??'—')+'%</td><td>'+v33Esc(x.fail_mean_excess_pct??'—')+'%</td><td>'+v33Esc(x.delta_pass_minus_fail_pct??'—')+'%</td><td>'+v33Esc(x.delta_ci_low??'—')+' / '+v33Esc(x.delta_ci_high??'—')+'</td><td class="'+v33Tone(x.label)+'"><b>'+v33Esc(x.label)+'</b></td></tr>').join('');
  box.innerHTML='<div class="stats">'+
    '<div class="stat"><span>Settled signal</span><b>'+v33Esc(d.settled_signals??0)+'</b><small>'+v33Esc(d.horizon)+' günlük horizon</small></div>'+
    '<div class="stat"><span>Faydalı gate</span><b class="up">'+v33Esc((d.useful_gates||[]).length)+'</b><small>bootstrap destekli</small></div>'+
    '<div class="stat"><span>Tekrar incele</span><b class="'+((d.review_candidates||[]).length?'down':'up')+'">'+v33Esc((d.review_candidates||[]).length)+'</b><small>otomatik değişiklik yok</small></div></div>'+
    '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Gate</th><th>Tip</th><th>PASS n</th><th>FAIL n</th><th>PASS excess</th><th>FAIL excess</th><th>Δ</th><th>%95 CI</th><th>Etiket</th></tr></thead><tbody>'+rows+'</tbody></table></div>'+
    '<p class="muted">'+v33Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v33Esc(e.message)+'</div>'}
}
async function settleDecisions33(){
 const b=$('#settleDecisions33');if(!b)return;b.disabled=true;b.textContent='Güncelleniyor…';
 try{
  const r=await fetch('/api/experience/settle',{method:'POST'});if(!r.ok)throw new Error(r.status+' settle');
  const d=await r.json();b.textContent=(d.updated||0)+' sonuç güncellendi';await loadDecisionCalibration33();await loadGateCalibration33();
 }catch(e){b.textContent='Hata: '+e.message}
 finally{setTimeout(()=>{b.disabled=false;b.textContent='Vadesi Dolanları Güncelle'},1800)}
}
const render33=render;
render=function(...args){
 render33(...args);
 if(state.view==='decisionlearning'){
  els.title.textContent='Karar Öğrenme & Kalibrasyon';
  els.subtitle.textContent='Prospektif kararların gerçek forward sonuçlarıyla doğrulanması';
  els.content.innerHTML=decisionLearningShell33();
  $('#settleDecisions33').onclick=settleDecisions33;
  $('#gateHorizon33').onchange=loadGateCalibration33;
  loadDecisionCalibration33();loadGateCalibration33();
 }
};
