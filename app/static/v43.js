function v43Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function stressShell43(){
 const defaults=[...state.watchlist].slice(0,8);if(!defaults.length)defaults.push('ASELS','THYAO','TUPRS','KCHOL');
 return '<section class="panel"><div class="panelHead"><div><h2>Portfolio Stress & Crash Scenarios</h2><p>BIST, korelasyon, likidite, sektör, faiz ve FX proxy stresleri</p></div></div><div class="formRow"><input id="stressCodes43" value="'+v43Esc(defaults.join(','))+'" placeholder="ASELS,THYAO,TUPRS"><select id="stressMethod43"><option value="equal">Equal</option><option value="inverse_vol">Inverse Vol</option><option value="risk_parity">Risk Parity</option></select><button id="runStress43" class="toolbtn">Stres Testi</button></div><div id="stressBox43"></div></section>';
}
async function loadStress43(){
 const box=document.querySelector('#stressBox43');if(!box)return;
 const codes=document.querySelector('#stressCodes43').value.trim(),method=document.querySelector('#stressMethod43').value;
 box.innerHTML='<div class="loading">Portföy stres senaryoları hesaplanıyor…</div>';
 try{
  const d=await getJSON('/api/portfolio-crash-stress?codes='+encodeURIComponent(codes)+'&method='+encodeURIComponent(method));
  const rows=(d.scenarios||[]).map(x=>'<tr><td><b>'+v43Esc(x.scenario)+'</b></td><td class="'+(x.loss_pct>=18?'down':x.loss_pct>=12?'amber':'')+'">'+v43Esc(x.loss_pct)+'%</td><td>'+v43Esc(x.quality)+'</td><td>'+v43Esc(x.detail)+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Risk durumu</span><b class="'+(d.risk_status==='CLEAR'?'up':d.risk_status==='BLOCK'?'down':'amber')+'">'+v43Esc(d.risk_status)+'</b><small>'+v43Esc((d.portfolio_flags||[]).join(' · ')||'temiz')+'</small></div><div class="stat"><span>Worst case</span><b class="down">'+v43Esc(d.worst_scenario?.loss_pct??'—')+'%</b><small>'+v43Esc(d.worst_scenario?.scenario||'—')+'</small></div><div class="stat"><span>Beta / Corr</span><b>'+v43Esc(d.metrics?.portfolio_beta??'—')+' / '+v43Esc(d.metrics?.avg_correlation??'—')+'</b><small>portföy</small></div><div class="stat"><span>Max sektör</span><b>'+v43Esc(d.metrics?.max_sector_weight_pct??'—')+'%</b><small>sector sleeve</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Senaryo</th><th>Kayıp</th><th>Kalite</th><th>Açıklama</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v43Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v43Esc(e.message)+'</div>'}
}
const render43=render;
render=function(...args){
 render43(...args);
 if(state.view==='portfoliostress'){
  els.title.textContent='Portfolio Stress & Crash Scenarios';
  els.subtitle.textContent='BIST crash, correlation spike, liquidity dry-up ve macro proxy şokları';
  els.content.innerHTML=stressShell43();document.querySelector('#runStress43').onclick=loadStress43;loadStress43();
 }
};
