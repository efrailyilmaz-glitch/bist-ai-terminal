function v44Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadExecutionReality44(){
 const box=document.querySelector('#executionRealityBox44');if(!box)return;
 const code=document.querySelector('#execTicker44').value.trim().toUpperCase(),notional=document.querySelector('#execNotional44').value,side=document.querySelector('#execSide44').value;
 box.innerHTML='<div class="loading">Execution Reality 2.0 hesaplanıyor…</div>';
 try{
  const d=await getJSON('/api/execution-reality-v2/'+encodeURIComponent(code)+'?notional='+encodeURIComponent(notional)+'&side='+encodeURIComponent(side));
  const e=d.execution||{},m=d.microstructure||{},b=d.bist_market_rules||{};
  box.innerHTML='<div class="stats"><div class="stat"><span>Execution status</span><b class="'+(d.status==='CLEAR'?'up':d.status==='BLOCK'?'down':'amber')+'">'+v44Esc(d.status)+'</b><small>quality '+v44Esc(d.quality_score)+'/100</small></div><div class="stat"><span>Slippage</span><b>'+v44Esc(d.estimated_slippage_bps??'—')+' bp</b><small>fill '+v44Esc(d.expected_fill_ratio_pct??'—')+'%</small></div><div class="stat"><span>Horizon</span><b>'+v44Esc(d.execution_horizon_bars??'—')+' bar</b><small>participation '+v44Esc(e.participation_rate_pct??'—')+'%</small></div><div class="stat"><span>Microstructure</span><b>'+v44Esc(m.status||'UNKNOWN')+'</b><small>'+v44Esc((m.flags||[]).join(' · ')||'—')+'</small></div></div><div class="tableWrap"><table class="stockTable"><tbody><tr><th>BIST guard</th><td>'+v44Esc(b.status||'—')+'</td><td>'+v44Esc((b.flags||[]).join(' · ')||'—')+'</td></tr><tr><th>Execution flags</th><td colspan="2">'+v44Esc((e.flags||[]).join(' · ')||'—')+'</td></tr><tr><th>Combined flags</th><td colspan="2">'+v44Esc((d.flags||[]).join(' · ')||'—')+'</td></tr></tbody></table></div><p class="muted">'+v44Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v44Esc(e.message)+'</div>'}
}
const render44=render;
render=function(...args){
 render44(...args);
 if(state.view==='executionreality2'){
  els.title.textContent='Execution Reality 2.0';
  els.subtitle.textContent='Slippage + participation + BIST limit + optional Level-2 + Trade Reality birleşik execution gate';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Execution Reality 2.0</h2><p>Eksik veya olumsuz execution kanıtı fill kalitesini yalnız kötüleştirebilir</p></div></div><div class="formRow"><input id="execTicker44" value="'+v44Esc(state.current||'ASELS')+'"><input id="execNotional44" type="number" value="100000" min="0" step="10000"><select id="execSide44"><option>BUY</option><option>SHORT</option></select><button id="runExec44" class="toolbtn">Analiz Et</button></div><div id="executionRealityBox44"></div></section>';
  document.querySelector('#runExec44').onclick=loadExecutionReality44;loadExecutionReality44();
 }
};
