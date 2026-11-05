function v41Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function portfolioIntelShell41(){
 const defaults=[...state.watchlist].slice(0,8);if(!defaults.length)defaults.push('ASELS','THYAO','TUPRS','KCHOL');
 return '<section class="panel"><div class="panelHead"><div><h2>Portfolio Decision Intelligence</h2><p>İyi hisse bile portföy yoğunlaşması nedeniyle ertelenebilir</p></div></div><div class="formRow"><input id="portfolioCodes41" value="'+v41Esc(defaults.join(','))+'" placeholder="ASELS,THYAO,TUPRS"><input id="candidate41" value="'+v41Esc(state.current||'ASELS')+'" placeholder="Aday hisse"><select id="method41"><option value="equal">Equal</option><option value="inverse_vol">Inverse Vol</option><option value="risk_parity">Risk Parity</option></select><button id="runPortfolioIntel41" class="toolbtn">Analiz Et</button></div><div id="portfolioIntelBox41"></div></section>';
}
async function loadPortfolioIntel41(){
 const box=document.querySelector('#portfolioIntelBox41');if(!box)return;
 const codes=document.querySelector('#portfolioCodes41').value.trim(),cand=document.querySelector('#candidate41').value.trim().toUpperCase(),method=document.querySelector('#method41').value;
 if(!codes){box.innerHTML='<div class="empty">En az bir portföy hissesi girin.</div>';return}
 box.innerHTML='<div class="loading">Portföy karar zekâsı hesaplanıyor…</div>';
 try{
  const d=await getJSON('/api/portfolio-decision-intelligence?codes='+encodeURIComponent(codes)+'&candidate='+encodeURIComponent(cand)+'&method='+encodeURIComponent(method));
  const sectors=(d.sectors||[]).map(x=>'<tr><td><b>'+v41Esc(x.sector)+'</b></td><td>'+v41Esc(x.weight_pct)+'%</td><td>'+v41Esc((x.tickers||[]).join(', '))+'</td></tr>').join('');
  const risks=(d.portfolio?.risk_rows||[]).map(x=>'<tr><td><b>'+v41Esc(x.ticker)+'</b></td><td>'+v41Esc(x.weight_pct)+'%</td><td>'+v41Esc(x.volatility_pct)+'%</td><td>'+v41Esc(x.beta_xu100??'—')+'</td><td>'+v41Esc(x.risk_contribution_pct)+'%</td></tr>').join('');
  const c=d.candidate||{};
  box.innerHTML='<div class="stats"><div class="stat"><span>Portföy</span><b class="'+(d.portfolio_status==='CLEAR'?'up':d.portfolio_status==='BLOCK'?'down':'amber')+'">'+v41Esc(d.portfolio_status)+'</b><small>'+v41Esc((d.flags||[]).join(' · ')||'temiz')+'</small></div><div class="stat"><span>Aday karar</span><b class="'+(c.decision==='PORTFOLIO_ACCEPTABLE_RESEARCH'?'up':c.decision==='PORTFOLIO_BLOCK'?'down':'amber')+'">'+v41Esc(c.decision||'—')+'</b><small>'+v41Esc((c.flags||[]).join(' · ')||'—')+'</small></div><div class="stat"><span>Avg corr</span><b>'+v41Esc(d.portfolio?.avg_correlation??'—')+'</b><small>diversification '+v41Esc(d.portfolio?.diversification_score??'—')+'</small></div><div class="stat"><span>Entry guard</span><b>'+v41Esc(c.entry_guard?.status??'—')+'</b><small>'+v41Esc((c.entry_guard?.flags||[]).join(' · ')||'—')+'</small></div></div><h3>Sektör Yoğunluğu</h3><div class="tableWrap"><table class="stockTable"><thead><tr><th>Sektör</th><th>Ağırlık</th><th>Hisseler</th></tr></thead><tbody>'+sectors+'</tbody></table></div><h3>Risk Katkısı</h3><div class="tableWrap"><table class="stockTable"><thead><tr><th>Hisse</th><th>Ağırlık</th><th>Vol</th><th>Beta</th><th>Risk katkısı</th></tr></thead><tbody>'+risks+'</tbody></table></div><p class="muted">'+v41Esc(d.note||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v41Esc(e.message)+'</div>'}
}
const render41=render;
render=function(...args){
 render41(...args);
 if(state.view==='portfoliointel'){
  els.title.textContent='Portfolio Decision Intelligence';
  els.subtitle.textContent='Tek-hisse fırsatlarını portföy korelasyon, sektör ve tail-risk bağlamında değerlendirir';
  els.content.innerHTML=portfolioIntelShell41();
  document.querySelector('#runPortfolioIntel41').onclick=loadPortfolioIntel41;loadPortfolioIntel41();
 }
};
