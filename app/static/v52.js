function v52Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadFeatureGov52(){
 const box=document.querySelector('#featureGovBox52'),sel=document.querySelector('#featureGovHorizon52');if(!box)return;
 const h=sel?sel.value:20;
 box.innerHTML='<div class="loading">Feature governance 3.0 yükleniyor…</div>';
 try{
  const d=await getJSON('/api/feature-governance-v3?horizon='+encodeURIComponent(h)+'&min_forward_n=30');
  const rows=(d.rows||[]).map(x=>'<tr><td><b>'+v52Esc(x.feature)+'</b></td><td class="'+(x.state==='CHALLENGER_ELIGIBLE'||x.state==='PROTECTED'?'up':x.state.includes('BLOCK')||x.state==='DECAY_REVIEW'?'down':'amber')+'"><b>'+v52Esc(x.state)+'</b></td><td>'+v52Esc(x.forward_n)+'</td><td>'+v52Esc(x.attribution_label||'—')+'</td><td>'+v52Esc(x.decay?.label||'—')+'</td><td>'+v52Esc((x.lineage_flags||[]).join(' · ')||'temiz')+'</td><td>'+v52Esc((x.redundancy||[]).map(r=>r.feature_a+' + '+r.feature_b+' '+r.jaccard_pct+'%').join(' · ')||'—')+'</td><td>'+v52Esc(x.reason||'')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Feature</span><b>'+v52Esc((d.rows||[]).length)+'</b><small>'+v52Esc(d.settled_signals)+' settled signal</small></div><div class="stat"><span>Redundancy pair</span><b>'+v52Esc((d.redundancy_pairs||[]).length)+'</b><small>Jaccard ≥ 75%</small></div><div class="stat"><span>Decay</span><b class="down">'+v52Esc((d.decay_rows||[]).filter(x=>x.label==='DECAY').length)+'</b><small>recent deterioration</small></div><div class="stat"><span>Production eligible</span><b class="down">0</b><small>research/challenger only</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Feature</th><th>State</th><th>Forward n</th><th>Attribution</th><th>Decay</th><th>Lineage</th><th>Redundancy</th><th>Neden</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v52Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v52Esc(e.message)+'</div>'}
}
const render52=render;
render=function(...args){
 render52(...args);
 if(state.view==='featuregov3'){
  els.title.textContent='Feature Governance 3.0';
  els.subtitle.textContent='Forward decay + redundancy + explicit PIT/leakage lineage';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Feature Governance 3.0</h2><p>Yeni feature production’a doğrudan giremez; registry + PIT + forward evidence gerekir</p></div><select id="featureGovHorizon52"><option value="5">5 gün</option><option value="20" selected>20 gün</option><option value="60">60 gün</option></select></div><div class="warningBox">Leakage feature isminden tahmin edilmez. Yalnız açık provenance/PIT metadata blok üretir.</div><div id="featureGovBox52"></div></section>';
  document.querySelector('#featureGovHorizon52').onchange=loadFeatureGov52;loadFeatureGov52();
 }
};