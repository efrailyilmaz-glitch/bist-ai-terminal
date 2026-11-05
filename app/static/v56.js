function v56e(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadLiveAdapters56(){
 const box=document.querySelector('#liveAdaptersBox56');if(!box)return;
 try{
  const d=await getJSON('/api/live-data-adapters');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v56e(x.name)+'</b><br><small>'+v56e(x.id)+'</small></td><td class="'+(x.status==='CONNECTED'?'up':x.status==='AVAILABLE_DELAYED'?'amber':'down')+'"><b>'+v56e(x.status)+'</b></td><td>'+v56e(x.realtime?'EVET':'HAYIR')+'</td><td>'+v56e(x.depth?'EVET':'HAYIR')+'</td><td>'+v56e(x.requires_license?'EVET':'HAYIR')+'</td><td>'+v56e(x.note||'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Realtime bağlı</span><b>'+v56e(d.connected_realtime||0)+'</b></div><div class="stat"><span>Toplam kullanılabilir</span><b>'+v56e(d.connected_any||0)+'</b></div><div class="stat"><span>Varsayılan</span><b>'+v56e(d.default_provider||'—')+'</b></div><div class="stat"><span>Depth sentezi</span><b class="up">YOK</b><small>yalnız gerçek lisanslı feed</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Sağlayıcı</th><th>Durum</th><th>Realtime</th><th>Depth</th><th>Lisans</th><th>Not</th></tr></thead><tbody>'+rows+'</tbody></table></div><div class="warningBox">Yahoo gecikmeli/public fallback olarak etiketlenir. Matriks / İş Yatırım / Info slotları gerçek sağlayıcı protokolü ve kimlik doğrulaması bağlanmadan veri üretmez. Level-2/derinlik hiçbir zaman tahmin edilmez veya sahte üretilmez.</div><p class="muted">'+v56e(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v56e(e.message)+'</div>'}
}
const render56=render;
render=function(...args){
 render56(...args);
 if(state.view==='liveadapters'){
  els.title.textContent='Live Data Adapters';
  els.subtitle.textContent='Gecikmeli fallback ve lisanslı gerçek zamanlı veri sağlayıcılarının açık durum kaydı';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Market Data Provider Registry</h2><p>Realtime ve Level-2 yalnız gerçek bağlantı varsa kullanılabilir</p></div><button id="reloadAdapters56" class="toolbtn">Yenile</button></div><div id="liveAdaptersBox56"></div></section>';
  document.querySelector('#reloadAdapters56').onclick=loadLiveAdapters56;loadLiveAdapters56();
 }
};