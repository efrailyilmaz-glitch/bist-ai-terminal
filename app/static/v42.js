function v42Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function sizingShell42(){
 const defaults=[...state.watchlist].slice(0,8);
 return '<section class="panel"><div class="panelHead"><div><h2>Dynamic Position Sizing</h2><p>Committee baz pozisyonunu yalnız azaltan çoklu risk çarpanları</p></div></div><div class="formRow"><input id="sizeTicker42" value="'+v42Esc(state.current||'ASELS')+'" placeholder="Hisse"><input id="sizePortfolio42" type="number" value="1000000" min="0" step="10000"><input id="sizeCodes42" value="'+v42Esc(defaults.join(','))+'" placeholder="Opsiyonel portföy kodları"><button id="runSizing42" class="toolbtn">Hesapla</button></div><div id="sizingBox42"></div></section>';
}
async function loadSizing42(){
 const box=document.querySelector('#sizingBox42');if(!box)return;
 const code=document.querySelector('#sizeTicker42').value.trim().toUpperCase(),pv=document.querySelector('#sizePortfolio42').value,codes=document.querySelector('#sizeCodes42').value.trim();
 box.innerHTML='<div class="loading">Dinamik pozisyon hesaplanıyor…</div>';
 try{
  const d=await getJSON('/api/dynamic-position-sizing/'+encodeURIComponent(code)+'?portfolio_value='+encodeURIComponent(pv)+(codes?'&codes='+encodeURIComponent(codes):''));
  const mult=Object.entries(d.multipliers||{}).map(([k,v])=>'<tr><td><b>'+v42Esc(k)+'</b></td><td>'+v42Esc(v)+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Committee baz</span><b>₺'+Number(d.base_committee_amount||0).toLocaleString('tr-TR')+'</b><small>'+v42Esc(d.base_committee_pct)+'%</small></div><div class="stat"><span>Dinamik pozisyon</span><b class="'+((d.dynamic_research_amount||0)>0?'up':'down')+'">₺'+Number(d.dynamic_research_amount||0).toLocaleString('tr-TR')+'</b><small>'+v42Esc(d.dynamic_research_pct)+'%</small></div><div class="stat"><span>Combined</span><b>'+v42Esc(d.combined_multiplier)+'</b><small>'+v42Esc(d.regime)+' · '+v42Esc(d.unified_decision)+'</small></div><div class="stat"><span>Güven</span><b>'+v42Esc(d.confidence_score)+'/100</b><small>exposure artırmaz</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Çarpan</th><th>Değer</th></tr></thead><tbody>'+mult+'</tbody></table></div><p class="muted">'+v42Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v42Esc(e.message)+'</div>'}
}
const render42=render;
render=function(...args){
 render42(...args);
 if(state.view==='positionsizing'){
  els.title.textContent='Dynamic Position Sizing';
  els.subtitle.textContent='Confidence + rejim + trap/distribution + portfolio risk ile yalnız aşağı yönlü sizing';
  els.content.innerHTML=sizingShell42();document.querySelector('#runSizing42').onclick=loadSizing42;loadSizing42();
 }
};
