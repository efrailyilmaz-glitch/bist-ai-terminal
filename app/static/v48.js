function v48Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadFundFusion48(){
 const box=document.querySelector('#fundFusionBox48');if(!box)return;
 const code=state.current||'ASELS';
 try{
  const d=await getJSON('/api/fundamental-price-fusion/'+encodeURIComponent(code));
  box.innerHTML='<div class="stats"><div class="stat"><span>Fusion state</span><b class="'+(d.state==='QUALITY_AND_TIMING_ALIGNED'?'up':d.hard_fundamental_risk?'down':'amber')+'">'+v48Esc(d.state)+'</b><small>'+v48Esc(d.research_action)+'</small></div><div class="stat"><span>Fundamental kalite</span><b>'+v48Esc(d.fundamental_quality_score)+'</b><small>health '+v48Esc(d.health_score)+'</small></div><div class="stat"><span>Price action timing</span><b>'+v48Esc(d.price_action_timing_score)+'</b><small>alignment '+v48Esc(d.technical_alignment??'—')+'</small></div><div class="stat"><span>Fair value</span><b>'+v48Esc(d.fair_value_upside_pct)+'%</b><small>Piotroski '+v48Esc(d.piotroski??'—')+'</small></div></div><div class="tableWrap"><table class="stockTable"><tbody><tr><th>Altman</th><td>'+v48Esc(d.altman||'—')+'</td></tr><tr><th>Beneish</th><td>'+v48Esc(d.beneish||'—')+'</td></tr><tr><th>Supertrend</th><td>'+v48Esc(d.supertrend||'—')+'</td></tr><tr><th>Ichimoku</th><td>'+v48Esc(d.ichimoku||'—')+'</td></tr><tr><th>EMA200</th><td>'+v48Esc(d.above_ema200)+'</td></tr></tbody></table></div><p class="muted">'+v48Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v48Esc(e.message)+'</div>'}
}
const render48=render;
render=function(...args){
 render48(...args);
 if(state.view==='fundpricefusion'){
  els.title.textContent='Fundamental + Price Action Fusion';
  els.subtitle.textContent='İyi şirket ile iyi giriş zamanını birbirinden ayırır';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Fundamental + Price Action Fusion</h2><p>Güçlü grafik kötü bilanço riskini; iyi bilanço da kötü giriş zamanını gizlemez</p></div><button id="reloadFund48" class="toolbtn">Yenile</button></div><div id="fundFusionBox48"></div></section>';
  document.querySelector('#reloadFund48').onclick=loadFundFusion48;loadFundFusion48();
 }
};