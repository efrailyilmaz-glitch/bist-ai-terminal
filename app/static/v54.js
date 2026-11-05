function v54Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadMaster54(){
 const box=document.querySelector('#masterIntegrityBox54');if(!box)return;
 try{
  const d=await getJSON('/api/research-integrity-master');
  const rows=(d.panels||[]).map(x=>'<tr><td><b>'+v54Esc(x.name)+'</b></td><td class="'+(['PASS','TRUSTED'].includes(x.status)?'up':['BLOCK','FAIL','DATA_BLOCK','ERROR'].includes(x.status)?'down':'amber')+'"><b>'+v54Esc(x.status)+'</b></td><td>'+v54Esc(x.critical?'KRİTİK':'İZLEME')+'</td><td><small>'+v54Esc(JSON.stringify(x.detail||{}))+'</small></td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Sistem güveni</span><b class="'+(d.status==='PASS'?'up':d.status==='BLOCK'?'down':'amber')+'">'+v54Esc(d.system_trust_score)+'/100</b><small>'+v54Esc(d.status)+'</small></div><div class="stat"><span>Araştırma kararı</span><b class="'+(d.research_decision_allowed?'up':'down')+'">'+(d.research_decision_allowed?'AÇIK':'BLOKE')+'</b><small>'+v54Esc((d.blockers||[]).join(' · ')||'kritik blok yok')+'</small></div><div class="stat"><span>Uyarı</span><b>'+v54Esc((d.warnings||[]).length)+'</b><small>'+v54Esc((d.warnings||[]).join(' · ')||'yok')+'</small></div><div class="stat"><span>Canlı işlem</span><b class="down">KAPALI</b><small>governance only</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Panel</th><th>Durum</th><th>Önem</th><th>Detay</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v54Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v54Esc(e.message)+'</div>'}
}
const render54=render;
render=function(...args){
 render54(...args);
 if(state.view==='integritymaster'){
  els.title.textContent='Research Integrity Master Dashboard';
  els.subtitle.textContent='Sistem şu anda güvenilir mi? · veri + ledger + feature + confidence + policy + factory';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Integrity Master</h2><p>Kritik blok varsa yeni araştırma kararı durur</p></div><button id="reloadMaster54" class="toolbtn">Yenile</button></div><div id="masterIntegrityBox54"></div></section>';
  document.querySelector('#reloadMaster54').onclick=loadMaster54;loadMaster54();
 }
};