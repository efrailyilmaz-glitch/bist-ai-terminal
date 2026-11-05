function v47Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadKapIntel47(){
 const box=document.querySelector('#kapIntelBox47');if(!box)return;
 const code=state.current||'ASELS';
 try{
  const d=await getJSON('/api/kap-intelligence-v2/'+encodeURIComponent(code)+'?limit=30');
  const cats=(d.categories||[]).map(x=>'<tr><td><b>'+v47Esc(x.category)+'</b></td><td>'+v47Esc(x.n)+'</td><td>'+v47Esc(x.mean_excess_1d??'—')+'% / '+v47Esc(x.hit_rate_1d??'—')+'%</td><td>'+v47Esc(x.mean_excess_5d??'—')+'% / '+v47Esc(x.hit_rate_5d??'—')+'%</td><td>'+v47Esc(x.mean_excess_20d??'—')+'% / '+v47Esc(x.hit_rate_20d??'—')+'%</td><td>'+v47Esc(x.avg_materiality??'—')+'</td></tr>').join('');
  const recent=(d.recent||[]).slice(0,15).map(x=>'<tr><td>'+v47Esc(x.date||'—')+'</td><td><b>'+v47Esc(x.event||'OTHER')+'</b></td><td>'+v47Esc(x.title||'—')+'</td><td>'+v47Esc(x.materiality??'—')+'</td><td>'+v47Esc(x.sentiment_score??'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>KAP PIT</span><b class="'+(d.point_in_time?.status==='PASS'?'up':d.point_in_time?.status==='BLOCK'?'down':'amber')+'">'+v47Esc(d.point_in_time?.status||'—')+'</b><small>'+v47Esc((d.point_in_time?.flags||[]).join(' · ')||'tarih temiz')+'</small></div><div class="stat"><span>Event study</span><b>'+v47Esc(d.event_count)+'</b><small>dated event</small></div></div><h3>Olay Sınıfı Performansı</h3><div class="tableWrap"><table class="stockTable"><thead><tr><th>Kategori</th><th>n</th><th>1g mean/hit</th><th>5g mean/hit</th><th>20g mean/hit</th><th>Materiality</th></tr></thead><tbody>'+cats+'</tbody></table></div><h3>Son KAP Olayları</h3><div class="tableWrap"><table class="stockTable"><thead><tr><th>Tarih</th><th>Tür</th><th>Başlık</th><th>Önem</th><th>Sentiment</th></tr></thead><tbody>'+recent+'</tbody></table></div><p class="muted">'+v47Esc(d.limits||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v47Esc(e.message)+'</div>'}
}
const render47=render;
render=function(...args){
 render47(...args);
 if(state.view==='kapintel2'){
  els.title.textContent='KAP Intelligence 2.0';
  els.subtitle.textContent='KAP olay sınıfları ve 1/5/20 günlük tarihsel stock-vs-XU100 davranışı';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>KAP Intelligence 2.0</h2><p>Sözleşme, yatırım, sermaye, dava, pay satışı, borç ve yönetim değişimi olayları</p></div><button id="reloadKap47" class="toolbtn">Yenile</button></div><div id="kapIntelBox47"></div></section>';
  document.querySelector('#reloadKap47').onclick=loadKapIntel47;loadKapIntel47();
 }
};