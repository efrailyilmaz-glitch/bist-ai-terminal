function v38Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadAdversarial38(){
 const box=document.querySelector('#adversarialBox38');if(!box)return;
 const code=state.current||'ASELS';
 box.innerHTML='<div class="loading">'+v38Esc(code)+' adversarial stres çalışıyor…</div>';
 try{
  const d=await getJSON('/api/adversarial-v3/'+encodeURIComponent(code));
  if(d.status==='ERROR')throw new Error(d.error||'stress error');
  const rows=(d.scenarios||[]).map(x=>'<tr><td><b>'+v38Esc(x.scenario)+'</b><br><small>'+v38Esc(x.description)+'</small></td><td>'+v38Esc(x.guard_status)+' / '+v38Esc(x.guard_score)+'</td><td>'+v38Esc(x.trap_status)+' / '+v38Esc(x.trap_score)+'</td><td class="'+(x.detected_any?'up':'down')+'">'+(x.detected_any?'YAKALANDI':'KAÇTI')+'</td><td>'+v38Esc((x.guard_flags||[]).slice(0,4).join(' · ')||'—')+'</td><td>'+v38Esc((x.trap_flags||[]).slice(0,4).join(' · ')||'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Hisse</span><b>'+v38Esc(d.ticker||code)+'</b><small>synthetic stress</small></div><div class="stat"><span>Any detection</span><b class="'+(d.detected_any_pct>=90?'up':'down')+'">'+v38Esc(d.detected_any_pct)+'%</b><small>'+v38Esc(d.scenario_count)+' senaryo</small></div><div class="stat"><span>Both detection</span><b>'+v38Esc(d.detected_both_pct)+'%</b><small>Guard + Trap</small></div><div class="stat"><span>Kaçan senaryo</span><b class="'+((d.missed_scenarios||[]).length?'down':'up')+'">'+v38Esc((d.missed_scenarios||[]).length)+'</b><small>'+v38Esc((d.missed_scenarios||[]).join(' · ')||'yok')+'</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Senaryo</th><th>Signal Guard</th><th>Trap Defense</th><th>Sonuç</th><th>Guard flags</th><th>Trap flags</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v38Esc(d.limits||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v38Esc(e.message)+'</div>'}
}
const render38=render;
render=function(...args){
 render38(...args);
 if(state.view==='adversarial3'){
  els.title.textContent='Adversarial Defense 3.0';
  els.subtitle.textContent='Hostile-looking OHLCV senaryolarına karşı Signal Guard + Trap Defense dayanıklılığı';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Market Trap / Adversarial Stress 3.0</h2><p>Manipülasyon niyeti iddiası değil; sentetik dayanıklılık testi</p></div><button id="rerunAdv38" class="toolbtn">Tekrar Çalıştır</button></div><div id="adversarialBox38"></div></section>';
  document.querySelector('#rerunAdv38').onclick=loadAdversarial38;loadAdversarial38();
 }
};
