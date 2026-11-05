function v57e(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadBrokerSandbox57(){
 const box=document.querySelector('#brokerSandboxBox57');if(!box)return;
 try{
  const d=await getJSON('/api/broker-sandbox/status');
  const rows=(d.adapters||[]).map(x=>'<tr><td><b>'+v57e(x.id)+'</b></td><td class="'+(x.status==='CONNECTED'?'up':'amber')+'"><b>'+v57e(x.status)+'</b></td><td>'+v57e(x.submit_mode)+'</td><td>'+v57e(x.configured==null?'—':x.configured?'EVET':'HAYIR')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Mod</span><b>'+v57e(d.mode)+'</b></div><div class="stat"><span>Live execution</span><b class="down">KAPALI</b></div><div class="stat"><span>Kill switch</span><b class="'+(d.kill_switch?'down':'up')+'">'+(d.kill_switch?'AKTİF':'PASİF')+'</b></div><div class="stat"><span>Kontrol sayısı</span><b>'+v57e((d.controls||[]).length)+'</b></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Adapter</th><th>Durum</th><th>Submit modu</th><th>Configured</th></tr></thead><tbody>'+rows+'</tbody></table></div><div class="warningBox">Sandbox submit yalnız paper ledger’a kayıt yapar. Aynı idempotency key aynı payload ile tekrar gelirse ikinci emir oluşturulmaz; farklı payload ile aynı key kullanılırsa bloklanır.</div><p class="muted">'+v57e(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v57e(e.message)+'</div>'}
}
const render57=render;
render=function(...args){
 render57(...args);
 if(state.view==='brokersandbox'){
  els.title.textContent='Broker Integration Sandbox';
  els.subtitle.textContent='Preview + paper submit + duplicate-order koruması · live execution kapalı';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Broker Sandbox Governance</h2><p>Kill switch, risk limitleri ve idempotency zorunlu</p></div><button id="reloadBrokerSandbox57" class="toolbtn">Yenile</button></div><div id="brokerSandboxBox57"></div></section>';
  document.querySelector('#reloadBrokerSandbox57').onclick=loadBrokerSandbox57;loadBrokerSandbox57();
 }
};