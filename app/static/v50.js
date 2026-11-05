function v50Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadNeutral50(){
 const box=document.querySelector('#neutralBox50');if(!box)return;
 box.innerHTML='<div class="loading">Sector/factor neutralization çalışıyor…</div>';
 try{
  const d=await getJSON('/api/sector-factor-neutral-v2?limit=150');
  const rows=(d.rows||[]).slice(0,80).map(x=>'<tr><td>'+v50Esc(x.neutral_rank)+'</td><td><b>'+v50Esc(x.ticker)+'</b></td><td>'+v50Esc(x.sector||'—')+'</td><td>'+v50Esc(x.raw_score)+'</td><td>'+v50Esc(x.neutral_score_z)+'</td><td class="'+(x.rank_change>0?'up':x.rank_change<0?'down':'')+'">'+(x.rank_change>0?'+':'')+v50Esc(x.rank_change)+'</td></tr>').join('');
  const g=d.diagnostics||{};
  box.innerHTML='<div class="stats"><div class="stat"><span>Neutralization</span><b class="'+(d.status==='PASS'?'up':'amber')+'">'+v50Esc(d.status)+'</b><small>'+v50Esc((d.flags||[]).join(' · ')||'temiz')+'</small></div><div class="stat"><span>Raw factor R²</span><b>'+v50Esc(g.raw_factor_r2??'—')+'</b><small>factor concentration</small></div><div class="stat"><span>Residual corr</span><b>'+v50Esc(g.max_neutral_abs_factor_corr??'—')+'</b><small>after neutralization</small></div><div class="stat"><span>Sector coverage</span><b>'+v50Esc(g.sector_coverage_pct??'—')+'%</b><small>'+v50Esc(g.sector_dummies_used??0)+' dummy</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>#</th><th>Hisse</th><th>Sektör</th><th>Raw</th><th>Neutral z</th><th>Rank Δ</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v50Esc(d.policy||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v50Esc(e.message)+'</div>'}
}
const render50=render;
render=function(...args){
 render50(...args);
 if(state.view==='neutral2'){
  els.title.textContent='Sector & Factor Neutralization 2.0';
  els.subtitle.textContent='Relative ranking içindeki sektör / momentum / volatilite / trend betasını ayırır';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>Neutralized Ranking</h2><p>Raw üstünlük ile faktörlerden arındırılmış üstünlüğü karşılaştırır</p></div><button id="reloadNeutral50" class="toolbtn">Yenile</button></div><div id="neutralBox50"></div></section>';
  document.querySelector('#reloadNeutral50').onclick=loadNeutral50;loadNeutral50();
 }
};