function v49Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
async function loadXSRank49(){
 const box=document.querySelector('#xsRankBox49');if(!box)return;
 box.innerHTML='<div class="loading">BIST cross-sectional ranking hesaplanıyor…</div>';
 try{
  const d=await getJSON('/api/cross-sectional-ranking-v2?limit=600&min_coverage_pct=80');
  if(d.status!=='OK'){box.innerHTML='<div class="empty">'+v49Esc(d.status)+' · '+v49Esc((d.quality?.flags||[]).join(' · '))+'</div>';return}
  const rows=(d.rows||[]).slice(0,100).map(x=>'<tr data-code="'+v49Esc(x.ticker)+'"><td>'+v49Esc(x.rank)+'</td><td><b>'+v49Esc(x.ticker)+'</b></td><td>'+v49Esc(x.relative_rank_score)+'</td><td>'+v49Esc(x.universe_percentile)+'%</td><td>'+v49Esc(x.rs20_pct)+'</td><td>'+v49Esc(x.rs60_pct)+'</td><td>'+v49Esc(x.momentum_pct)+'</td><td>'+v49Esc(x.risk_quality_pct)+'</td><td>'+v49Esc(x.liquidity_pct)+'</td><td>'+v49Esc(x.signal_guard||'—')+' / '+v49Esc(x.trap_defense||'—')+'</td></tr>').join('');
  box.innerHTML='<div class="stats"><div class="stat"><span>Ranked</span><b>'+v49Esc(d.ranked)+'</b><small>'+v49Esc(d.received)+' / '+v49Esc(d.requested)+'</small></div><div class="stat"><span>Coverage</span><b>'+v49Esc(d.quality?.details?.coverage_pct??'—')+'%</b><small>'+v49Esc(d.quality?.status||'—')+'</small></div></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>#</th><th>Hisse</th><th>Relative</th><th>Percentile</th><th>RS20</th><th>RS60</th><th>Momentum</th><th>Risk Q</th><th>Likidite</th><th>Guard / Trap</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">'+v49Esc(d.policy||'')+'</p>';
  box.querySelectorAll('tr[data-code]').forEach(tr=>tr.onclick=()=>{state.current=tr.dataset.code;render();});
 }catch(e){box.innerHTML='<div class="empty">'+v49Esc(e.message)+'</div>'}
}
const render49=render;
render=function(...args){
 render49(...args);
 if(state.view==='xsrank2'){
  els.title.textContent='Cross-Sectional Ranking 2.0';
  els.subtitle.textContent='Aynı BIST snapshot içindeki relatif üstünlüğe göre sıralama';
  els.content.innerHTML='<section class="panel"><div class="panelHead"><div><h2>BIST Relative Ranking</h2><p>Absolute skor yerine evren percentile üstünlüğü</p></div><button id="reloadRank49" class="toolbtn">Yenile</button></div><div id="xsRankBox49"></div></section>';
  document.querySelector('#reloadRank49').onclick=loadXSRank49;loadXSRank49();
 }
};