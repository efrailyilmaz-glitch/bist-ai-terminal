function v46Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadDataTrust46(){
 const box=document.querySelector('#dataTrustBox46');if(!box)return;
 try{
  const d=await getJSON('/api/data-trust-v2');
  const rows=(d.providers||[]).map(x=>'<tr><td><b>'+v46Esc(x.provider)+'</b></td><td class="'+(x.status==='PASS'?'up':x.status==='BLOCK'?'down':'amber')+'"><b>'+v46Esc(x.status)+'</b></td><td>'+v46Esc(x.critical?'KRİTİK':'İKİNCİL')+'</td><td>'+v46Esc(x.trust_score)+'</td><td>'+v46Esc(JSON.stringify(x.detail||{}))+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Data trust</span><b class="'+(d.status==='TRUSTED'?'up':d.status==='DATA_BLOCK'?'down':'amber')+'">'+v46Esc(d.status)+'</b><small>score '+v46Esc(d.trust_score)+'</small></div><div class="stat"><span>Karar izni</span><b class="'+(d.decision_allowed?'up':'down')+'">'+(d.decision_allowed?'AÇIK':'BLOKE')+'</b><small>'+v46Esc((d.critical_blocks||[]).join(' · ')||'kritik blok yok')+'</small></div><div class="stat"><span>Coverage</span><b>'+v46Esc(d.received_symbols)+' / '+v46Esc(d.requested_symbols)+'</b><small>current scan</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Kaynak</th><th>Durum</th><th>Önem</th><th>Trust</th><th>Detay</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v46Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v46Esc(e.message)+'</div>'}
}
const render46=render;
render=function(...args){
 render46(...args);
 if(state.view==='datatrust2'){
  els.title.textContent='Data Quality & Provider Trust 2.0';
  els.subtitle.textContent='Kaynak çalışıyor mu değil, karar vermeye yeterince güvenilir mi?';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Provider Trust 2.0</h2><p>Kritik market/universe bozulması DATA_BLOCK üretir</p></div><button id="reloadTrust46" class="toolbtn">Yenile</button></div><div id="dataTrustBox46"></div></section>';
  document.querySelector('#reloadTrust46').onclick=loadDataTrust46;loadDataTrust46();
 }
};