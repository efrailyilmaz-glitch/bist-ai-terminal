function v39Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadSmartFusion39(){
 const box=document.querySelector('#smartFusionBox39');if(!box)return;
 const code=state.current||'ASELS';
 try{
  const [cur,rad]=await Promise.all([getJSON('/api/smart-money-trap/'+encodeURIComponent(code)),getJSON('/api/smart-money-trap-radar?limit=20')]);
  const rows=(rad.rows||[]).map(x=>'<tr data-code="'+v39Esc(x.ticker)+'"><td><b>'+v39Esc(x.ticker)+'</b></td><td class="'+(x.state==='CLEAN_ACCUMULATION_WATCH'?'up':x.state.includes('TRAP_RISK')?'down':'amber')+'"><b>'+v39Esc(x.state)+'</b></td><td>'+v39Esc(x.fusion_score)+'</td><td>'+v39Esc(x.risk_score)+'</td><td>'+v39Esc(x.smart_money?.accumulation_probability??'—')+'</td><td>'+v39Esc(x.smart_money?.markup_probability??'—')+'</td><td>'+v39Esc(x.smart_money?.distribution_risk??'—')+'</td><td>'+v39Esc(x.trap_defense?.status??'—')+' / '+v39Esc(x.trap_defense?.score??'—')+'</td><td>'+v39Esc(x.research_action)+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Seçili hisse</span><b>'+v39Esc(code)+'</b><small>'+v39Esc(cur.state||cur.status)+'</small></div><div class="stat"><span>Fusion</span><b>'+v39Esc(cur.fusion_score??'—')+'</b><small>yüksek = temiz birikim</small></div><div class="stat"><span>Risk</span><b class="'+((cur.risk_score||0)>=65?'down':'')+'">'+v39Esc(cur.risk_score??'—')+'</b><small>distribution + trap</small></div><div class="stat"><span>Temiz aday</span><b class="up">'+v39Esc(rad.clean_count??0)+'</b><small>conflict '+v39Esc(rad.conflict_count??0)+'</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Hisse</th><th>Fusion state</th><th>Fusion</th><th>Risk</th><th>Accum.</th><th>Markup</th><th>Distrib.</th><th>Trap</th><th>Aksiyon</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v39Esc(cur.warning||rad.note||'')+'</p>';
  box.querySelectorAll('tr[data-code]').forEach(tr=>tr.onclick=()=>{state.current=tr.dataset.code;loadSmartFusion39();});
 }catch(e){box.innerHTML='<div class="empty">'+v39Esc(e.message)+'</div>'}
}
const render39=render;
render=function(...args){
 render39(...args);
 if(state.view==='smartfusion'){
  els.title.textContent='Smart Money + Trap Fusion';
  els.subtitle.textContent='Birikim / markup sinyalini dağıtım ve tuzak riskiyle birlikte değerlendirir';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Smart Money + Trap Defense Fusion</h2><p>Temiz birikim adaylarını bullish görünen ama tuzak riski taşıyanlardan ayırır</p></div><button id="reloadFusion39" class="toolbtn">Yenile</button></div><div id="smartFusionBox39"><div class="loading">Fusion radar yükleniyor…</div></div></section>';
  document.querySelector('#reloadFusion39').onclick=loadSmartFusion39;loadSmartFusion39();
 }
};
