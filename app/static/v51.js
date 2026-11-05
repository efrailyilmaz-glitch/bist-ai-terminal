function v51Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadZoo51(){
 const box=document.querySelector('#modelZooBox51');if(!box)return;
 try{
  const d=await getJSON('/api/model-zoo-v2');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v51Esc(x.name)+'</b><br><small>'+v51Esc(x.kind)+'</small></td><td>'+v51Esc(x.source)+'</td><td>'+v51Esc(x.license)+'</td><td class="'+(x.license_gate==='PASS'?'up':'amber')+'">'+v51Esc(x.license_gate)+'</td><td>'+v51Esc(x.installed?'EVET':'HAYIR')+'</td><td>'+v51Esc(x.integration_status)+'</td><td>'+v51Esc(x.adapter)+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Aday</span><b>'+v51Esc((d.rows||[]).length)+'</b><small>'+v51Esc(d.as_of)+'</small></div><div class="stat"><span>Zorunlu gate</span><b>'+v51Esc((d.required_gates||[]).length)+'</b><small>license + PIT + OOS + cost + forward</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Model/Framework</th><th>Kaynak</th><th>Lisans</th><th>Gate</th><th>Kurulu</th><th>Durum</th><th>Adapter</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v51Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v51Esc(e.message)+'</div>'}
}
const render51=render;
render=function(...args){
 render51(...args);
 if(state.view==='modelzoo2'){
  els.title.textContent='Model Zoo Expansion';
  els.subtitle.textContent='GitHub / Hugging Face adayları · lisans ve reproducibility gate'leri';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>External Model Zoo 2.0</h2><p>Qlib, FinRL-X, PyBroker, Chronos-2, TimesFM 3 ve Moirai 2 adayları</p></div></div><div class="warningBox">Popülerlik kanıt değildir. Non-commercial ve doğrulanmamış lisanslı adaylar production yoluna giremez.</div><div id="modelZooBox51"></div></section>';loadZoo51();
 }
};