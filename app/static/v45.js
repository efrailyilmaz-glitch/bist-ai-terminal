function v45Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadCapacity45(){
 const box=document.querySelector('#capacityBox45');if(!box)return;
 const code=document.querySelector('#capacityTicker45').value.trim().toUpperCase();
 try{
  const d=await getJSON('/api/capacity-scale/'+encodeURIComponent(code)+'?adv_limit_pct=1');
  const rows=(d.rows||[]).map(x=>'<tr><td>₺'+Number(x.notional).toLocaleString('tr-TR')+'</td><td class="'+(x.status==='CLEAR'?'up':x.status==='BLOCK'?'down':'amber')+'"><b>'+v45Esc(x.status)+'</b></td><td>'+v45Esc(x.participation_pct??'—')+'%</td><td>'+v45Esc(x.effective_impact_bps??'—')+' bp</td><td>'+v45Esc(x.execution_horizon_days??'—')+'</td><td>'+v45Esc((x.flags||[]).join(' · ')||'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>ADV</span><b>₺'+Number(d.adv_value||0).toLocaleString('tr-TR')+'</b><small>'+v45Esc(code)+'</small></div><div class="stat"><span>Max CLEAR</span><b>₺'+Number(d.max_clear_notional||0).toLocaleString('tr-TR')+'</b><small>1% ADV policy</small></div><div class="stat"><span>Max non-block</span><b>₺'+Number(d.max_non_block_notional||0).toLocaleString('tr-TR')+'</b><small>clear + caution</small></div><div class="stat"><span>İlk BLOCK</span><b class="down">'+(d.first_block_notional==null?'—':'₺'+Number(d.first_block_notional).toLocaleString('tr-TR'))+'</b><small>scale limit</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Notional</th><th>Durum</th><th>ADV %</th><th>Impact</th><th>Gün</th><th>Flags</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v45Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v45Esc(e.message)+'</div>'}
}
const render45=render;
render=function(...args){
 render45(...args);
 if(state.view==='capacityscale'){
  els.title.textContent='Capacity & Market Impact';
  els.subtitle.textContent='Aynı hisse için sermaye büyüdükçe ADV katılımı, impact ve execution horizon';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Capacity Scale Analysis</h2><p>100 bin TL’den 10 milyon TL’ye aynı adayın execution kapasitesi</p></div></div><div class="formRow"><input id="capacityTicker45" value="'+v45Esc(state.current||'ASELS')+'"><button id="runCapacity45" class="toolbtn">Analiz Et</button></div><div id="capacityBox45"></div></section>';
  document.querySelector('#runCapacity45').onclick=loadCapacity45;loadCapacity45();
 }
};
