function v34Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadGateInteractions34(){
 const box=document.querySelector('#gateInteractionBox34'),sel=document.querySelector('#gateHorizon33');if(!box)return;
 const h=sel?sel.value:20;
 try{
  const d=await getJSON('/api/gate-interactions?horizon='+encodeURIComponent(h)+'&min_samples=6');
  const rows=(d.rows||[]).slice(0,40).map(x=>'<tr><td><b>'+v34Esc(x.pair)+'</b></td><td>'+v34Esc(x.both_fail_n)+'</td><td>'+v34Esc(x.failure_jaccard_pct)+'%</td><td>'+v34Esc(x.both_fail_mean_excess_pct??'—')+'%</td><td>'+v34Esc(x.single_fail_mean_excess_pct??'—')+'%</td><td>'+v34Esc(x.interaction_delta_pct??'—')+'%</td><td class="'+(x.label==='JOINT_PROTECTIVE'?'up':x.label==='JOINT_COSTLY'||x.label==='REDUNDANCY_REVIEW'?'down':'amber')+'"><b>'+v34Esc(x.label)+'</b></td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Redundancy aday</span><b>'+v34Esc((d.redundancy_candidates||[]).length)+'</b><small>yüksek co-fail overlap</small></div><div class="stat"><span>Joint protective</span><b class="up">'+v34Esc((d.joint_protective||[]).length)+'</b><small>birlikte güçlü koruma</small></div><div class="stat"><span>Joint costly</span><b class="down">'+v34Esc((d.joint_costly||[]).length)+'</b><small>birlikte fırsat maliyeti</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Gate çifti</th><th>Both fail n</th><th>Jaccard</th><th>Both fail excess</th><th>Single fail excess</th><th>Interaction Δ</th><th>Etiket</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v34Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v34Esc(e.message)+'</div>'}
}
const render34=render;
render=function(...args){
 render34(...args);
 if(state.view==='decisionlearning'){
  const root=els.content;
  if(root&&!document.querySelector('#gateInteractionBox34')){
   root.insertAdjacentHTML('beforeend','<section class="panel"><div class="panelHead"><div><h2>Gate Interaction Analysis</h2><p>Hard gate çiftlerinin co-failure, redundancy ve joint protection analizi</p></div></div><div class="warningBox">Yüksek birlikte başarısızlık ortak sebep veya rejim etkisi olabilir; hiçbir gate otomatik kaldırılmaz.</div><div id="gateInteractionBox34"><div class="loading">Gate etkileşimleri yükleniyor…</div></div></section>');
   loadGateInteractions34();
   const sel=document.querySelector('#gateHorizon33');
   if(sel){const old=sel.onchange;sel.onchange=()=>{if(old)old();loadGateInteractions34();};}
  }
 }
};
