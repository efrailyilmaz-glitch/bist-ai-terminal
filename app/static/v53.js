function v53Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadFactory53(){
 const box=document.querySelector('#researchFactoryBox53');if(!box)return;
 try{
  const d=await getJSON('/api/research-factory/status?limit=30');
  const rows=(d.runs||[]).map(x=>'<tr><td>'+v53Esc(x.id)+'</td><td>'+v53Esc(new Date((x.created_epoch||0)*1000).toLocaleString('tr-TR'))+'</td><td><b>'+v53Esc(x.stage)+'</b></td><td>'+v53Esc(x.status)+'</td><td><small>'+v53Esc((x.run_hash||'').slice(0,12))+'</small></td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Factory run</span><b>'+v53Esc((d.runs||[]).length)+'</b><small>inspectable ledger</small></div><div class="stat"><span>Canlı yetki</span><b class="down">YOK</b><small>research/paper only</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>ID</th><th>Zaman</th><th>Stage</th><th>Status</th><th>Hash</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v53Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v53Esc(e.message)+'</div>'}
}
async function runFactory53(){
 const b=document.querySelector('#runFactory53');b.disabled=true;b.textContent='Çalışıyor…';
 try{
  const r=await fetch('/api/research-factory/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:120,train_days:252,test_days:63,purge_days:5,embargo_days:5,one_way_cost_bps:20,rebalance_every:5,portfolio_value:1000000,adv_limit_pct:1,auto_create_paper:true})});
  const d=await r.json();document.querySelector('#factoryLast53').innerHTML='<b>'+v53Esc(d.status)+'</b> · '+v53Esc((d.blockers||[]).join(' · ')||d.stage||'');
  await loadFactory53();
 }catch(e){document.querySelector('#factoryLast53').textContent=e.message}
 finally{b.disabled=false;b.textContent='Factory Run';}
}
const render53=render;
render=function(...args){
 render53(...args);
 if(state.view==='researchfactory'){
  els.title.textContent='Continuous Research Factory';
  els.subtitle.textContent='Data/PIT/feature integrity preflight → validation → paper incubation';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Research Factory 2.0</h2><p>Integrity blocker varsa validation veya paper creation başlamaz</p></div><button id="runFactory53" class="toolbtn">Factory Run</button></div><div id="factoryLast53" class="warningBox">Henüz bu ekrandan run başlatılmadı.</div><div id="researchFactoryBox53"></div></section>';
  document.querySelector('#runFactory53').onclick=runFactory53;loadFactory53();
 }
};