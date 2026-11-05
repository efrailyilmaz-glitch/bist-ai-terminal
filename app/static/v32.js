function v32Esc(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function v32Tone(s){s=String(s||'').toUpperCase();if(['PASS','ARAŞTIRMA ONAYI','CLEAR'].includes(s))return 'up';if(['WATCH','İZLE / TEYİT BEKLE','WAIT'].includes(s))return 'amber';return 'down'}
function decisionGateShell32(){
 const code=v32Esc(state.current||'ASELS');
 return '<section class="panel"><div class="panelHead"><div><h2>Nihai Karar Güven Kapısı</h2><p>Committee · Signal Guard · Trap Defense · Point-in-Time · KAP bütünlüğü · rejim · expected value</p></div><div class="actions"><input id="decisionTicker32" value="'+code+'" placeholder="Hisse kodu"><button id="decisionRun32" class="toolbtn">Kararı Hesapla</button></div></div><div class="warningBox">Yüksek teknik skor tek başına geçiş sağlamaz. Hard gate başarısızsa sistem güçlü sinyali veto eder.</div><div id="decisionBox32"><div class="loading">Karar kapısı yükleniyor…</div></div></section>';
}
function gateRows32(gates){
 return (gates||[]).map(g=>'<tr><td><b>'+v32Esc(g.name)+'</b></td><td class="'+(g.pass?'up':'down')+'">'+(g.pass?'PASS':'FAIL')+'</td><td>'+v32Esc(g.hard?'HARD':'SOFT')+'</td><td>'+v32Esc(g.detail||'')+'</td></tr>').join('');
}
async function loadDecision32(){
 const box=$('#decisionBox32'),inp=$('#decisionTicker32');if(!box||!inp)return;
 const code=String(inp.value||'').trim().toUpperCase().replace('.IS','');if(!code){box.innerHTML='<div class="empty">Hisse kodu girin.</div>';return}
 box.innerHTML='<div class="loading">'+v32Esc(code)+' için karar kapısı çalışıyor…</div>';
 try{
  const d=await getJSON('/api/committee/'+encodeURIComponent(code));
  if(d.status!=='OK'){box.innerHTML='<div class="empty">'+v32Esc(d.status||'Veri yok')+'</div>';return}
  const guard=d.signal_guard||{},trap=d.trap_defense||{},pit=d.point_in_time||{},kap=d.kap_point_in_time||{};
  const veto=(d.vetoes||[]);
  box.innerHTML='<div class="stats">'+
    '<div class="stat"><span>Nihai karar</span><b class="'+v32Tone(d.decision_tr)+'">'+v32Esc(d.decision_tr)+'</b><small>'+v32Esc(d.decision||'')+'</small></div>'+
    '<div class="stat"><span>Committee skor</span><b>'+v32Esc(d.committee_score)+'/100</b><small>rejim '+v32Esc(d.regime||'—')+'</small></div>'+
    '<div class="stat"><span>Expected value</span><b class="'+(Number(d.expected_value_pct)>=0?'up':'down')+'">'+v32Esc(d.expected_value_pct)+'%</b><small>RR '+v32Esc(d.risk_reward??'—')+'</small></div>'+
    '<div class="stat"><span>Hard veto</span><b class="'+(veto.length?'down':'up')+'">'+veto.length+'</b><small>'+v32Esc(veto.join(' · ')||'yok')+'</small></div>'+
    '<div class="stat"><span>Signal Guard</span><b class="'+v32Tone(guard.status)+'">'+v32Esc(guard.status||'—')+'</b><small>'+v32Esc(guard.score??'—')+'/100</small></div>'+
    '<div class="stat"><span>Trap Defense</span><b class="'+v32Tone(trap.status)+'">'+v32Esc(trap.status||'—')+'</b><small>'+v32Esc(trap.score??'—')+'/100</small></div>'+
    '<div class="stat"><span>PIT</span><b class="'+v32Tone(pit.status)+'">'+v32Esc(pit.status||'—')+'</b><small>signal timestamp</small></div>'+
    '<div class="stat"><span>KAP PIT</span><b class="'+v32Tone(kap.status)+'">'+v32Esc(kap.status||'—')+'</b><small>disclosure chronology</small></div>'+
  '</div>'+
  '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Kapı</th><th>Sonuç</th><th>Tip</th><th>Açıklama</th></tr></thead><tbody>'+gateRows32(d.gates)+'</tbody></table></div>'+
  '<div class="grid2"><div><h3>Tezi bozan durumlar</h3><p>'+v32Esc((d.invalidation||[]).join(' · ')||'—')+'</p></div><div><h3>Araştırma pozisyon sınırı</h3><p>'+v32Esc(d.position_sizing?.research_position_pct??'—')+'% · ₺'+v32Esc(d.position_sizing?.research_position_value??'—')+'</p></div></div>'+
  '<p class="muted">'+v32Esc(d.note||'')+'</p>';
 }catch(e){box.innerHTML='<div class="empty">'+v32Esc(e.message)+'</div>'}
}
const render32=render;
render=function(...args){
 render32(...args);
 if(state.view==='decisiongate'){
  els.title.textContent='Nihai Karar Güven Kapısı';
  els.subtitle.textContent='Güçlü sinyal bile hard-gate başarısızsa veto edilir';
  els.content.innerHTML=decisionGateShell32();
  $('#decisionRun32').onclick=loadDecision32;
  $('#decisionTicker32').addEventListener('keydown',e=>{if(e.key==='Enter')loadDecision32()});
  loadDecision32();
 }
};
