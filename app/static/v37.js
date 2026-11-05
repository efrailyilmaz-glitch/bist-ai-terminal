function v37Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadRegimeAdaptive37(){
 const box=document.querySelector('#regimeAdaptiveBox37'),sel=document.querySelector('#gateHorizon33');if(!box)return;
 const h=sel?sel.value:20;
 try{
  const d=await getJSON('/api/regime-adaptive-policy?horizon='+encodeURIComponent(h)+'&min_regime_samples=10&min_selected=4');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v37Esc(x.regime)+'</b></td><td>'+v37Esc(x.leader_name||'—')+'</td><td>'+v37Esc(x.margin_vs_incumbent??'—')+'</td><td class="'+(x.recommendation==='SHADOW_REGIME_CHALLENGER'?'amber':x.recommendation==='HOLD_INCUMBENT'?'up':'')+'"><b>'+v37Esc(x.recommendation)+'</b></td><td>'+v37Esc((x.policies||[]).map(p=>p.name+': '+(p.mean_utility??'—')).join(' · '))+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Shadow rejim önerisi</span><b>'+v37Esc((d.shadow_recommendations||[]).length)+'</b><small>otomatik switch yok</small></div><div class="stat"><span>Canlı policy switch</span><b class="down">KAPALI</b><small>research only</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Rejim</th><th>Lider policy</th><th>Incumbent farkı</th><th>Öneri</th><th>Policy utility</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v37Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v37Esc(e.message)+'</div>'}
}
const render37=render;
render=function(...args){
 render37(...args);
 if(state.view==='decisionlearning'){
  const root=els.content;
  if(root&&!document.querySelector('#regimeAdaptiveBox37')){
   root.insertAdjacentHTML('beforeend','<section class="panel"><div class="panelHead"><div><h2>Regime-Adaptive Decision Layer</h2><p>BULL / BEAR / SIDEWAYS rejimlerinde hangi shadow policy daha iyi davranıyor?</p></div></div><div class="warningBox">Rejim lideri yalnız araştırma gözlemidir; otomatik policy switch kapalıdır.</div><div id="regimeAdaptiveBox37"><div class="loading">Rejim policy analizi yükleniyor…</div></div></section>');
   loadRegimeAdaptive37();
   const sel=document.querySelector('#gateHorizon33');if(sel){const old=sel.onchange;sel.onchange=()=>{if(old)old();loadRegimeAdaptive37();};}
  }
 }
};
