function v33Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function v33Tone(s){s=String(s||'').toUpperCase();if(['USEFUL','PASS','OK'].includes(s))return 'up';if(['MONITOR','INSUFFICIENT','WATCH'].includes(s))return 'amber';return 'down'}
function decisionLearningShell33(){
 return '<div class="grid2">'+
 '<section class="panel"><div class="panelHead"><div><h2>Karar Sonuç Kalibrasyonu</h2><p>PASS / WATCH / NO_TRADE kararlarının 5/20/60 günlük forward sonuçları</p></div><button id="settleDecisions33" class="toolbtn">Vadesi Dolanları Güncelle</button></div><div id="decisionCalibrationBox33"><div class="loading">Karar sonuçları yükleniyor…</div></div></section>'+
 '<section class="panel"><div class="panelHead"><div><h2>Gate Fayda Analizi</h2><p>Gate PASS ile FAIL gruplarının benchmark üstü forward sonuç farkı</p></div><select id="gateHorizon33"><option value="5">5 gün</option><option value="20" selected>20 gün</option><option value="60">60 gün</option></select></div><div class="warningBox">Bu ekran ilişki ölçer, nedensellik kanıtlamaz. “Fazla katı” etiketi gate’i otomatik değiştirmez; yalnızca yeniden doğrulama adayı yapar.</div><div id="gateCalibrationBox33"><div class="loading">Gate kalibrasyonu yükleniyor…</div></div></section></div>'+ 
 '<section class="panel"><div class="panelHead"><div><h2>Kaçırılan Fırsat Denetimi</h2><p>NO_TRADE sonrası benchmark üzerinde güçlü giden hisseler ve bunları bloke eden hard gate kümeleri</p></div></div><div id="missedOpportunityBox33"><div class="loading">Kaçırılan fırsatlar analiz ediliyor…</div></div></section>'+ 
 '<section class="panel"><div class="panelHead"><div><h2>Gate Net Fayda</h2><p>Engellenen kötü sonuçlar ile kaçırılan iyi sonuçların aynı forward örneklemde dengesi</p></div></div><div class="warningBox">Aynı sinyalde birden fazla gate başarısız olabilir. Bu nedenle net fayda ortak-atıflı tanısal bir ölçümdür; nedensel PnL değildir.</div><div id="gateUtilityBox33"><div class="loading">Net fayda hesaplanıyor…</div></div></section>'+ 
 '<section class="panel"><div class="panelHead"><div><h2>Rejim Bazlı Gate Davranışı</h2><p>Aynı gate farklı piyasa rejimlerinde koruyucu mu, fırsat maliyetli mi?</p></div></div><div id="gateRegimeBox33"><div class="loading">Rejim analizi yükleniyor…</div></div></section>'+ 
 '<section class="panel"><div class="panelHead"><div><h2>Decision Policy Challengers</h2><p>Incumbent, Strict Defense ve Adaptive politikalarının aynı snapshot üzerindeki forward shadow yarışı</p></div></div><div class="warningBox">Challenger yalnız inceleme durumuna ulaşabilir. Ana politika ve canlı işlem yolu otomatik olarak değişmez.</div><div id="policyChallengerBox33"><div class="loading">Shadow challenger sonuçları yükleniyor…</div></div></section>';
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
async function loadMissedOpportunity33(){
 const box=$('#missedOpportunityBox33'),sel=$('#gateHorizon33');if(!box||!sel)return;
 try{
  const d=await getJSON('/api/decision-calibration/missed-opportunities?horizon='+encodeURIComponent(sel.value)+'&min_excess_pct=3&min_samples=3');
  const gates=(d.gate_summary||[]).map(x=>'<tr><td><b>'+v33Esc(x.gate)+'</b></td><td>'+v33Esc(x.misses)+'</td><td>'+v33Esc(x.unique_tickers)+'</td><td>'+v33Esc(x.mean_missed_excess_pct??'—')+'%</td><td>'+v33Esc(x.max_missed_excess_pct??'—')+'%</td><td class="'+(x.review?'down':'amber')+'">'+(x.review?'İNCELE':'İZLE')+'</td></tr>').join('');
  const recent=(d.recent_misses||[]).slice(0,15).map(x=>'<tr><td><b>'+v33Esc(x.ticker)+'</b></td><td>'+v33Esc(x.created_at||'—')+'</td><td>'+v33Esc(x.excess_pct)+'%</td><td>'+v33Esc((x.failed_hard_gates||[]).join(' · ')||'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>NO_TRADE settle</span><b>'+v33Esc(d.settled_no_trade??0)+'</b><small>'+v33Esc(d.horizon)+' günlük</small></div><div class="stat"><span>Kaçırılan fırsat</span><b>'+v33Esc(d.missed_opportunities??0)+'</b><small>≥ '+v33Esc(d.threshold_excess_pct)+'% excess</small></div><div class="stat"><span>Kaçırma oranı</span><b>'+v33Esc(d.miss_rate_pct??0)+'%</b><small>tanısal ölçüm</small></div></div><h3>Gate kümeleri</h3><div class="tableWrap"><table class="stockTable"><thead><tr><th>Gate</th><th>Miss</th><th>Hisse</th><th>Ort. excess</th><th>Max excess</th><th>Durum</th></tr></thead><tbody>'+gates+'</tbody></table></div><h3>Son örnekler</h3><div class="tableWrap"><table class="stockTable"><thead><tr><th>Hisse</th><th>Karar zamanı</th><th>Excess</th><th>Başarısız hard gate</th></tr></thead><tbody>'+recent+'</tbody></table></div><p class="muted">'+v33Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v33Esc(e.message)+'</div>'}
}
async function loadGateUtility33(){
 const box=$('#gateUtilityBox33'),sel=$('#gateHorizon33');if(!box||!sel)return;
 try{
  const d=await getJSON('/api/decision-calibration/net-utility?horizon='+encodeURIComponent(sel.value)+'&bad_excess_pct=-3&good_excess_pct=3&min_samples=8');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v33Esc(x.gate)+'</b></td><td>'+v33Esc(x.failed_n)+'</td><td>'+v33Esc(x.bad_n)+'</td><td>'+v33Esc(x.good_n)+'</td><td>'+v33Esc(x.protection_rate_pct)+'%</td><td>'+v33Esc(x.miss_rate_pct)+'%</td><td>'+v33Esc(x.avoided_downside_sum_pct)+'%</td><td>'+v33Esc(x.missed_upside_sum_pct)+'%</td><td>'+v33Esc(x.net_utility_per_failure_pct)+'%</td><td class="'+(x.label==='NET_PROTECTIVE'?'up':x.label==='NET_COSTLY'?'down':'amber')+'"><b>'+v33Esc(x.label)+'</b></td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Koruyucu gate</span><b class="up">'+v33Esc((d.protective_gates||[]).length)+'</b><small>net pozitif</small></div><div class="stat"><span>İnceleme adayı</span><b class="'+((d.review_candidates||[]).length?'down':'up')+'">'+v33Esc((d.review_candidates||[]).length)+'</b><small>net maliyetli</small></div><div class="stat"><span>Eşikler</span><b>'+v33Esc(d.bad_excess_threshold_pct)+' / +'+v33Esc(d.good_excess_threshold_pct)+'</b><small>benchmark excess %</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Gate</th><th>Fail n</th><th>Kötü</th><th>İyi</th><th>Koruma %</th><th>Miss %</th><th>Önlenen downside</th><th>Kaçan upside</th><th>Net / fail</th><th>Sonuç</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v33Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v33Esc(e.message)+'</div>'}
}
async function loadGateRegime33(){
 const box=$('#gateRegimeBox33'),sel=$('#gateHorizon33');if(!box||!sel)return;
 try{
  const d=await getJSON('/api/decision-calibration/regime-utility?horizon='+encodeURIComponent(sel.value)+'&bad_excess_pct=-3&good_excess_pct=3&min_samples=5');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v33Esc(x.gate)+'</b></td><td>'+v33Esc(x.regime)+'</td><td>'+v33Esc(x.n)+'</td><td>'+v33Esc(x.bad_n)+'</td><td>'+v33Esc(x.good_n)+'</td><td>'+v33Esc(x.protection_rate_pct)+'%</td><td>'+v33Esc(x.miss_rate_pct)+'%</td><td class="'+(x.label==='PROTECTIVE'?'up':x.label==='COSTLY'?'down':'amber')+'"><b>'+v33Esc(x.label)+'</b></td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Rejim çatışmalı gate</span><b class="'+((d.regime_conflict_gates||[]).length?'down':'up')+'">'+v33Esc((d.regime_conflict_gates||[]).length)+'</b><small>'+v33Esc((d.regime_conflict_gates||[]).join(' · ')||'yok')+'</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Gate</th><th>Rejim</th><th>n</th><th>Kötü</th><th>İyi</th><th>Koruma %</th><th>Miss %</th><th>Etiket</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v33Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v33Esc(e.message)+'</div>'}
}
async function loadPolicyChallengers33(){
 const box=$('#policyChallengerBox33'),sel=$('#gateHorizon33');if(!box||!sel)return;
 try{
  const d=await getJSON('/api/decision-policy-challengers?horizon='+encodeURIComponent(sel.value)+'&min_settled=12');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v33Esc(x.name)+'</b><br><small>'+v33Esc(x.id)+'</small></td><td class="'+(x.status==='MATURE'?'up':'amber')+'">'+v33Esc(x.status)+'</td><td>'+v33Esc(x.settled_n)+'</td><td>'+v33Esc(x.selected_n)+'</td><td>'+v33Esc(x.pass_n)+'</td><td>'+v33Esc(x.watch_n)+'</td><td>'+v33Esc(x.no_trade_n)+'</td><td>'+v33Esc(x.selected_mean_excess_pct??'—')+'%</td><td>'+v33Esc(x.selected_hit_rate_pct??'—')+'%</td><td>'+v33Esc(x.protected_bad_n)+'</td><td>'+v33Esc(x.missed_good_n)+'</td><td><b>'+v33Esc(x.shadow_score)+'</b></td></tr>').join('');
  const dec=d.decision||{};const paired=(d.paired_comparisons||[]).map(x=>'<tr><td><b>'+v33Esc(x.name)+'</b></td><td>'+v33Esc(x.paired_n)+'</td><td>'+v33Esc(x.mean_utility_delta??'—')+'</td><td>'+v33Esc(x.ci_low??'—')+' / '+v33Esc(x.ci_high??'—')+'</td><td>'+v33Esc(x.prob_positive_pct??'—')+'%</td><td class="'+(x.status==='SUPPORTED'?'up':x.status==='MATURE_NO_EDGE'?'down':'amber')+'"><b>'+v33Esc(x.status)+'</b></td><td>'+v33Esc((x.regimes||[]).map(r=>r.regime+': n='+r.n).join(' · ')||'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Governance</span><b class="'+(dec.action==='CHALLENGER_REVIEW'?'amber':'up')+'">'+v33Esc(dec.action||'HOLD')+'</b><small>'+v33Esc(dec.reason||'—')+'</small></div><div class="stat"><span>Canlı işlem</span><b class="down">KAPALI</b><small>shadow only</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Politika</th><th>Durum</th><th>Settle</th><th>Seçim</th><th>PASS</th><th>WATCH</th><th>NO_TRADE</th><th>Ort. excess</th><th>Hit %</th><th>Korunan kötü</th><th>Kaçan iyi</th><th>Shadow skor</th></tr></thead><tbody>'+rows+'</tbody></table></div><h3>Paired Forward Confidence</h3><div class="tableWrap"><table class="stockTable"><thead><tr><th>Challenger</th><th>Pair n</th><th>Ort. utility Δ</th><th>%95 CI</th><th>P(Δ&gt;0)</th><th>Durum</th><th>Rejim kapsamı</th></tr></thead><tbody>'+paired+'</tbody></table></div><p class="muted">'+v33Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v33Esc(e.message)+'</div>'}
}
async function settleDecisions33(){
 const b=$('#settleDecisions33');if(!b)return;b.disabled=true;b.textContent='Güncelleniyor…';
 try{
  const r=await fetch('/api/experience/settle',{method:'POST'});if(!r.ok)throw new Error(r.status+' settle');
  const d=await r.json();b.textContent=(d.updated||0)+' sonuç güncellendi';await loadDecisionCalibration33();await loadGateCalibration33();await loadMissedOpportunity33();await loadGateUtility33();await loadGateRegime33();await loadPolicyChallengers33();
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
  $('#gateHorizon33').onchange=()=>{loadGateCalibration33();loadMissedOpportunity33();loadGateUtility33();loadGateRegime33();loadPolicyChallengers33();};
  loadDecisionCalibration33();loadGateCalibration33();loadMissedOpportunity33();loadGateUtility33();loadGateRegime33();loadPolicyChallengers33();
 }
};
