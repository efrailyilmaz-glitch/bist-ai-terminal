function v40Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadUnified40(){
 const box=document.querySelector('#unifiedDecisionBox40');if(!box)return;
 const code=state.current||'ASELS';
 box.innerHTML='<div class="loading">'+v40Esc(code)+' birleşik karar hesaplanıyor…</div>';
 try{
  const d=await getJSON('/api/unified-decision/'+encodeURIComponent(code));
  const why=(d.why||[]).map(x=>'<tr><td><b>'+v40Esc(x.module)+'</b></td><td>'+v40Esc(x.status??'—')+'</td><td>'+v40Esc(x.detail??'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats">'+
   '<div class="stat"><span>Nihai karar</span><b class="'+(d.final_decision==='RESEARCH_PASS'?'up':d.final_decision==='WATCH'?'amber':'down')+'">'+v40Esc(d.final_decision_tr||d.final_decision)+'</b><small>'+v40Esc(code)+'</small></div>'+
   '<div class="stat"><span>Güven</span><b>'+v40Esc(d.confidence_score??'—')+'/100</b><small>kalibre edilmemiş research score</small></div>'+
   '<div class="stat"><span>Hard veto</span><b class="'+((d.hard_vetoes||[]).length?'down':'up')+'">'+v40Esc((d.hard_vetoes||[]).length)+'</b><small>'+v40Esc((d.hard_vetoes||[]).join(' · ')||'yok')+'</small></div>'+
   '<div class="stat"><span>Downgrade</span><b class="'+((d.downgrades||[]).length?'amber':'up')+'">'+v40Esc((d.downgrades||[]).length)+'</b><small>'+v40Esc((d.downgrades||[]).join(' · ')||'yok')+'</small></div></div>'+
   '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Modül</th><th>Durum</th><th>Detay</th></tr></thead><tbody>'+why+'</tbody></table></div>'+
   '<h3>Destekler</h3><p>'+v40Esc((d.supports||[]).join(' · ')||'yok')+'</p><p class="muted">'+v40Esc(d.note||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v40Esc(e.message)+'</div>'}
}
const render40=render;
render=function(...args){
 render40(...args);
 if(state.view==='unifieddecision'){
  els.title.textContent='Unified Decision Engine';
  els.subtitle.textContent='Committee + Signal Guard + Trap + Smart Money + KAP + Alpha + Fundamentals tek karar zinciri';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Birleşik Nihai Karar</h2><p>Hard veto asla destek modülleriyle bypass edilmez</p></div><button id="reloadUnified40" class="toolbtn">Yenile</button></div><div id="unifiedDecisionBox40"></div></section>';
  document.querySelector('#reloadUnified40').onclick=loadUnified40;loadUnified40();
 }
};
