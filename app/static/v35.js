function v35Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadDecisionErrorCost35(){
 const box=document.querySelector('#decisionErrorCostBox35'),sel=document.querySelector('#gateHorizon33');if(!box)return;
 const h=sel?sel.value:20;
 try{
  const d=await getJSON('/api/decision-error-cost?horizon='+encodeURIComponent(h)+'&good_excess_pct=3&bad_excess_pct=-3');
  const m=d.matrix||{},c=d.costs||{};
  box.innerHTML='<div class="stats">'+
   '<div class="stat"><span>Decisive accuracy</span><b>'+v35Esc(d.accuracy_pct??0)+'%</b><small>'+v35Esc(d.decisive_signals??0)+' karar</small></div>'+
   '<div class="stat"><span>False positive cost</span><b class="down">'+v35Esc(c.false_positive_downside_sum_pct??0)+'%</b><small>'+v35Esc(m.FP?.n??0)+' hata</small></div>'+
   '<div class="stat"><span>False negative cost</span><b class="amber">'+v35Esc(c.false_negative_missed_upside_sum_pct??0)+'%</b><small>'+v35Esc(m.FN?.n??0)+' kaçırma</small></div>'+
   '<div class="stat"><span>Dominant error</span><b>'+v35Esc(c.dominant_error||'—')+'</b><small>benchmark excess maliyeti</small></div></div>'+
   '<div class="tableWrap"><table class="stockTable"><thead><tr><th></th><th>Actual good ≥ +3%</th><th>Actual bad ≤ -3%</th><th>Neutral</th></tr></thead><tbody>'+
   '<tr><td><b>SELECTED</b></td><td class="up">TP '+v35Esc(m.TP?.n??0)+'</td><td class="down">FP '+v35Esc(m.FP?.n??0)+'</td><td>'+v35Esc(m.NEUTRAL_SELECTED?.n??0)+'</td></tr>'+
   '<tr><td><b>NO_TRADE</b></td><td class="amber">FN '+v35Esc(m.FN?.n??0)+'</td><td class="up">TN '+v35Esc(m.TN?.n??0)+'</td><td>'+v35Esc(m.NEUTRAL_REJECTED?.n??0)+'</td></tr>'+
   '</tbody></table></div><p class="muted">'+v35Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v35Esc(e.message)+'</div>'}
}
const render35=render;
render=function(...args){
 render35(...args);
 if(state.view==='decisionlearning'){
  const root=els.content;
  if(root&&!document.querySelector('#decisionErrorCostBox35')){
   root.insertAdjacentHTML('beforeend','<section class="panel"><div class="panelHead"><div><h2>False Positive / False Negative Cost Matrix</h2><p>Yanlış seçim downside maliyeti ile gereksiz NO_TRADE fırsat maliyetini ayrı ölçer</p></div></div><div id="decisionErrorCostBox35"><div class="loading">Hata maliyet matrisi yükleniyor…</div></div></section>');
   loadDecisionErrorCost35();
   const sel=document.querySelector('#gateHorizon33');if(sel){const old=sel.onchange;sel.onchange=()=>{if(old)old();loadDecisionErrorCost35();};}
  }
 }
};
