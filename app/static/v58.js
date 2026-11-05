function v58e(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadLiveReadiness58(){
 const box=document.querySelector('#liveReadinessBox58');if(!box)return;
 try{
  const d=await getJSON('/api/controlled-live-readiness');
  const rows=(d.gates||[]).map(x=>'<tr><td><b>'+v58e(x.name)+'</b></td><td class="'+(x.pass?'up':'down')+'"><b>'+(x.pass?'PASS':'BLOCK')+'</b></td><td>'+v58e(x.category)+'</td><td><small>'+v58e(JSON.stringify(x.detail||{}))+'</small></td></tr>').join('');
  const ready=d.status==='READY_FOR_MANUAL_INTEGRATION_REVIEW';
  box.innerHTML='<div class="stats"><div class="stat"><span>Readiness</span><b class="'+(ready?'up':'down')+'">'+v58e(d.status)+'</b></div><div class="stat"><span>Toplam blocker</span><b>'+v58e((d.blockers||[]).length)+'</b></div><div class="stat"><span>İç / evidence</span><b>'+v58e((d.internal_blockers||[]).length)+'</b></div><div class="stat"><span>Dış bağımlılık</span><b>'+v58e((d.external_blockers||[]).length)+'</b></div><div class="stat"><span>Direct live</span><b class="down">KAPALI</b></div><div class="stat"><span>Auto enable</span><b class="down">YOK</b></div></div>'+
  '<div class="warningBox">Bu ekran canlı işlem açmaz. Tüm gate’ler geçse bile yalnız manuel broker/provider entegrasyon ve güvenlik incelemesine geçilebilir.</div>'+
  '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Gate</th><th>Durum</th><th>Kategori</th><th>Detay</th></tr></thead><tbody>'+rows+'</tbody></table></div>'+
  '<p class="muted"><b>Sonraki adım:</b> '+v58e(d.next_step||'—')+'</p><p class="muted">'+v58e(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v58e(e.message)+'</div>'}
}
const render58=render;
render=function(...args){
 render58(...args);
 if(state.view==='livereadiness'){
  els.title.textContent='Controlled Live Readiness';
  els.subtitle.textContent='Canlı işlem yetkisi vermeden entegrasyon hazırlığını hard gate’lerle ölçer';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Live Readiness Gate</h2><p>Forward evidence + integrity + realtime feed + broker contract</p></div><button id="reloadLiveReadiness58" class="toolbtn">Yenile</button></div><div id="liveReadinessBox58"></div></section>';
  document.querySelector('#reloadLiveReadiness58').onclick=loadLiveReadiness58;loadLiveReadiness58();
 }
};