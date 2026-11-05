function v36Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadConfidenceCalibration36(){
 const box=document.querySelector('#confidenceCalibrationBox36'),sel=document.querySelector('#gateHorizon33');if(!box)return;
 const h=sel?sel.value:20;
 try{
  const d=await getJSON('/api/confidence-calibration?horizon='+encodeURIComponent(h)+'&success_excess_pct=0&min_bin=5');
  const rows=(d.bins||[]).map(x=>'<tr><td><b>'+v36Esc(x.range)+'%</b></td><td>'+v36Esc(x.n)+'</td><td>'+v36Esc(x.avg_confidence_pct)+'%</td><td>'+v36Esc(x.realized_success_pct)+'%</td><td>'+v36Esc(x.calibration_gap_pct)+'%</td><td class="'+(x.label==='CALIBRATED'?'up':x.label==='INSUFFICIENT'?'amber':'down')+'"><b>'+v36Esc(x.label)+'</b></td></tr>').join('');
  box.innerHTML='<div class="stats">'+
   '<div class="stat"><span>Calibration</span><b class="'+(d.status==='CALIBRATED'?'up':d.status==='INSUFFICIENT'?'amber':'down')+'">'+v36Esc(d.status)+'</b><small>'+v36Esc(d.settled_selected)+' settled selected</small></div>'+
   '<div class="stat"><span>Nominal güven</span><b>'+v36Esc(d.overall_confidence_pct??'—')+'%</b><small>committee score</small></div>'+
   '<div class="stat"><span>Gerçek başarı</span><b>'+v36Esc(d.overall_success_pct??'—')+'%</b><small>excess &gt; 0</small></div>'+
   '<div class="stat"><span>ECE / Brier</span><b>'+v36Esc(d.expected_calibration_error)+' / '+v36Esc(d.brier_score??'—')+'</b><small>reliability</small></div></div>'+
   '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Güven bandı</th><th>n</th><th>Ort. güven</th><th>Gerçek başarı</th><th>Gap</th><th>Durum</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v36Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v36Esc(e.message)+'</div>'}
}
const render36=render;
render=function(...args){
 render36(...args);
 if(state.view==='decisionlearning'){
  const root=els.content;
  if(root&&!document.querySelector('#confidenceCalibrationBox36')){
   root.insertAdjacentHTML('beforeend','<section class="panel"><div class="panelHead"><div><h2>Confidence Calibration</h2><p>Committee güven skorları ile gerçekleşen forward başarı oranının reliability analizi</p></div></div><div class="warningBox">Committee score gerçek olasılık varsayılmaz; yalnız forward evidence ile kalibrasyon tanısı yapılır.</div><div id="confidenceCalibrationBox36"><div class="loading">Güven kalibrasyonu yükleniyor…</div></div></section>');
   loadConfidenceCalibration36();
   const sel=document.querySelector('#gateHorizon33');if(sel){const old=sel.onchange;sel.onchange=()=>{if(old)old();loadConfidenceCalibration36();};}
  }
 }
};
