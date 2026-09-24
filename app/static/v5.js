
function v5PctCount(rows, fn){ return rows.length ? Math.round(1000 * rows.filter(fn).length / rows.length) / 10 : 0; }

function v5LocalInternals(){
  const rows=[...state.scan.values()];
  const sorted=[...rows].sort((a,b)=>(b.change||0)-(a.change||0));
  const liquid=[...rows].sort((a,b)=>(b.avg_value_turnover_20||0)-(a.avg_value_turnover_20||0)).slice(0,10);
  return {
    n:rows.length,
    advance:v5PctCount(rows,x=>(x.change||0)>0),
    above20:v5PctCount(rows,x=>x.above_ema20),
    above50:v5PctCount(rows,x=>x.above_ema50),
    above200:v5PctCount(rows,x=>x.above_ema200),
    nearHigh:v5PctCount(rows,x=>x.near_52w_high),
    breakout:v5PctCount(rows,x=>x.breakout20),
    bullST:v5PctCount(rows,x=>x.supertrend==='BULLISH'),
    bullIchi:v5PctCount(rows,x=>x.ichimoku==='BULLISH'),
    strongShort:v5PctCount(rows,x=>(x.short_score||0)>=70),
    strongLong:v5PctCount(rows,x=>(x.long_score||0)>=70),
    gainers:sorted.slice(0,8),
    losers:sorted.slice(-8).reverse(),
    liquid:liquid
  };
}

function v5MiniRows(rows,key){
  key=key||'change';
  return rows.map(function(x){
    const m=state.meta.get(x.ticker)||{};
    const value=key==='change'?pct(x.change||0):compact4(x[key]);
    return '<div class="miniMarketRow" onclick="openStock(\''+x.ticker+'\')"><strong>'+x.ticker+'</strong><span>'+(m.name||x.name||'')+'</span><b class="'+(key==='change'?cls(x.change||0):'')+'">'+value+'</b></div>';
  }).join('');
}

function v5InternalsView(){
  const x=v5LocalInternals();
  const metrics=[['Yükselen',x.advance],['EMA20 üstü',x.above20],['EMA50 üstü',x.above50],['EMA200 üstü',x.above200],['52H yakını',x.nearHigh],['Breakout',x.breakout],['Bull Supertrend',x.bullST],['Bull Ichimoku',x.bullIchi],['Kısa güçlü',x.strongShort],['Uzun güçlü',x.strongLong]];
  return '<div class="panel"><div class="panelHead"><div><h2>Market Internals</h2><p>Taranan '+x.n+' hisseden piyasa katılımı ve trend genişliği</p></div><span class="pill">'+(state.scanning?'SCANNING':'LIVE SET')+'</span></div>'+
    '<div class="breadthGrid">'+metrics.map(function(a){return '<div class="breadthCard"><span>'+a[0]+'</span><b>%'+a[1]+'</b><div class="breadthBar"><i style="width:'+a[1]+'%"></i></div></div>';}).join('')+'</div>'+
    '<div class="grid3 internalsLists"><div><h4>Günün Güçlüleri</h4>'+v5MiniRows(x.gainers,'change')+'</div><div><h4>Günün Zayıfları</h4>'+v5MiniRows(x.losers,'change')+'</div><div><h4>20G Ort. İşlem Değeri</h4>'+v5MiniRows(x.liquid,'avg_value_turnover_20')+'</div></div></div>';
}

function v5Signals(){
  const signals=[];
  [...state.scan.values()].forEach(function(r){
    function add(type,tone,priority,detail){signals.push({ticker:r.ticker,type:type,tone:tone,priority:priority,detail:detail,score:r.alpha_score||0,change:r.change||0});}
    if(r.cross_event==='GOLDEN_CROSS')add('Golden Cross','up',95,'EMA50 / EMA200 kesişimi');
    if(r.rsi_divergence==='BULLISH'||r.macd_divergence==='BULLISH')add('Bullish Divergence','up',92,'RSI/MACD pozitif uyumsuzluk');
    if(r.breakout20&&(r.volume_ratio||0)>=1.3)add('Breakout + Hacim','up',90,'20G kırılım · hacim '+r.volume_ratio+'x');
    if(r.bollinger_squeeze&&(r.short_score||0)>=60)add('Bollinger Squeeze','amber',82,'Daralan volatilite · skor '+r.short_score);
    if((r.short_score||0)>=80)add('Kısa Vade Güçlü','up',80,'Short score '+r.short_score);
    if((r.long_score||0)>=80)add('Uzun Vade Güçlü','up',78,'Long score '+r.long_score);
    if(r.near_52w_high&&(r.relative_strength_20||0)>3)add('52H + Relative Strength','up',76,'RS20 '+pct(r.relative_strength_20));
    if((r.anomaly_score||0)>=70)add('Yüksek Anomali','down',94,'Anomali '+r.anomaly_score+' · hacim '+r.volume_ratio+'x');
    if(r.rsi_divergence==='BEARISH'||r.macd_divergence==='BEARISH')add('Bearish Divergence','down',91,'RSI/MACD negatif uyumsuzluk');
    if(r.cross_event==='DEATH_CROSS')add('Death Cross','down',93,'EMA50 / EMA200 negatif kesişim');
  });
  return signals.sort((a,b)=>b.priority-a.priority||b.score-a.score);
}

function v5AlertsView(){
  const s=v5Signals();
  return '<div class="panel"><div class="panelHead"><div><h2>Signal Inbox</h2><p>Teknik setup ve risk sinyalleri</p></div><span class="pill">'+s.length+' SIGNAL</span></div>'+
    (s.length?'<div class="signalList">'+s.slice(0,150).map(function(x){return '<div class="signalItem" onclick="openStock(\''+x.ticker+'\')"><span class="signalType '+x.tone+'">'+x.type+'</span><strong>'+x.ticker+'</strong><span>'+x.detail+'</span><b class="'+cls(x.change)+'">'+pct(x.change)+'</b><em>Alpha '+x.score+'</em></div>';}).join('')+'</div>':'<div class="empty">Henüz sinyal yok.</div>')+'</div>';
}

function v5StrategyLabView(){
  return '<div class="panel"><div class="panelHead"><div><h2>Strategy Lab · '+state.current+'</h2><p>İşlem maliyeti + slippage · walk-forward · Monte Carlo</p></div><span class="pill">OOS READY</span></div>'+
    '<div class="strategyControls"><label>Strateji<select id="v5Strategy"><option value="ma_trend">EMA Trend</option><option value="momentum">Momentum</option><option value="breakout">Breakout</option><option value="rsi_reversion">RSI Reversion</option><option value="supertrend">Supertrend</option></select></label><label>Komisyon bps<input id="v5Cost" type="number" value="10" min="0" max="100"></label><label>Slippage bps<input id="v5Slip" type="number" value="5" min="0" max="100"></label><button class="toolbtn" id="v5RunStrategy">Tam Doğrulama</button></div><div id="strategyResult"><div class="empty">Tam Doğrulama ile strateji paketini çalıştır.</div></div></div>';
}

function v5MetricCards(arr){
  return '<div class="btgrid">'+arr.map(function(x){return '<div class="stat"><span>'+x[0]+'</span><b>'+x[1]+'</b></div>';}).join('')+'</div>';
}

async function v5RunStrategyLab(){
  const box=$('#strategyResult'); if(!box)return;
  const st=$('#v5Strategy').value, cost=Number($('#v5Cost').value||10), slip=Number($('#v5Slip').value||5);
  box.innerHTML='<div class="loading">Backtest + walk-forward + Monte Carlo hesaplanıyor…</div>';
  try{
    const qs='?period=5y&cost_bps='+cost+'&slippage_bps='+slip;
    const data=await Promise.all([
      getJSON('/api/backtest/'+state.current+qs+'&strategy='+st),
      getJSON('/api/strategy-compare/'+state.current+qs),
      getJSON('/api/walk-forward/'+state.current+qs+'&strategy='+st),
      getJSON('/api/monte-carlo/'+state.current+qs+'&strategy='+st)
    ]);
    const base=data[0], cmp=data[1], wf=data[2], mc=data[3];
    const baseCards=v5MetricCards([['Getiri',pct(base.return_pct)],['CAGR',pct(base.cagr_pct)],['Sharpe',base.sharpe],['Sortino',base.sortino],['Max DD',pct(base.max_drawdown)],['Calmar',base.calmar],['Profit Factor',base.profit_factor],['Exposure',pct(base.exposure_pct)],['VaR95/Gün',pct(base.var95_daily_pct)],['CVaR95/Gün',pct(base.cvar95_daily_pct)]]);
    const compare='<div class="tableWrap"><table class="stockTable"><thead><tr><th>Strateji</th><th>Getiri</th><th>CAGR</th><th>Sharpe</th><th>Sortino</th><th>Max DD</th><th>PF</th><th>İşlem</th></tr></thead><tbody>'+(cmp.rows||[]).map(function(x){return '<tr><td>'+x.strategy+'</td><td>'+pct(x.return_pct)+'</td><td>'+pct(x.cagr_pct)+'</td><td>'+x.sharpe+'</td><td>'+x.sortino+'</td><td>'+pct(x.max_drawdown)+'</td><td>'+x.profit_factor+'</td><td>'+x.trades+'</td></tr>';}).join('')+'</tbody></table></div>';
    const wfHtml=wf.error?'<div class="warningBox">'+wf.error+'</div>':v5MetricCards([['OOS Getiri',pct(wf.oos_return_pct)],['OOS Sharpe',wf.oos_sharpe],['OOS Max DD',pct(wf.oos_max_drawdown_pct)],['Segment',wf.segments.length]]);
    const mcHtml=mc.error?'<div class="warningBox">'+mc.error+'</div>':v5MetricCards([['MC P10',pct(mc.return_p10)],['MC Median',pct(mc.return_median)],['MC P90',pct(mc.return_p90)],['Pozitif Dağılım',pct(mc.prob_positive_pct)],['Medyan Max DD',pct(mc.maxdd_median)],['Kötü %10 DD',pct(mc.maxdd_p10)]]);
    box.innerHTML='<h4>Seçili Strateji</h4>'+baseCards+'<h4>Strateji Karşılaştırma</h4>'+compare+'<h4>Walk-Forward / Out-of-Sample</h4>'+wfHtml+'<h4>Monte Carlo</h4>'+mcHtml+'<p class="muted">Monte Carlo tarihsel strateji getirilerinin block-bootstrap dağılımıdır; gelecek tahmini değildir.</p>';
  }catch(e){box.innerHTML='<div class="empty">Strategy Lab hatası: '+e.message+'</div>';}
}

function v5HealthView(){
  return '<div class="panel"><div class="panelHead"><div><h2>Data Health</h2><p>Veri erişimi ve premium connector readiness</p></div><button class="toolbtn" id="refreshHealth">Yenile</button></div><div id="healthResult"><div class="loading">Kaynaklar kontrol ediliyor…</div></div></div>';
}

async function v5LoadHealth(){
  const box=$('#healthResult'); if(!box)return;
  try{
    const d=await getJSON('/api/data-health');
    const providers=Object.entries(d.providers||{}).map(function(kv){const k=kv[0],v=kv[1];return '<div class="providerCard"><span>'+k.toUpperCase()+'</span><b>'+v.active+'</b><small>'+(v.licensed_ready?'Premium connector ENV hazır':'Premium connector bağlı değil')+'</small></div>';}).join('');
    const checks=(d.checks||[]).map(function(x){return '<div class="healthRow"><i class="'+(x.status==='OK'?'ok':'bad')+'"></i><strong>'+x.name+'</strong><span>'+x.status+'</span><b>'+x.latency_ms+' ms</b><small>'+(x.error||JSON.stringify(x.detail||{}))+'</small></div>';}).join('');
    box.innerHTML='<div class="healthHero '+(d.status==='HEALTHY'?'ok':'warn')+'"><b>'+d.status+'</b><span>'+d.ok+'/'+d.total+' kaynak · '+d.timestamp+'</span></div><div class="providerGrid">'+providers+'</div><div class="healthList">'+checks+'</div>';
  }catch(e){box.innerHTML='<div class="empty">Data Health hatası: '+e.message+'</div>';}
}

const v5RenderBase=render;
render=function(){
  v5RenderBase();
  if(state.view==='internals'){els.title.textContent='Market Internals';els.content.innerHTML=v5InternalsView();}
  if(state.view==='alerts'){els.title.textContent='Signal Inbox';els.content.innerHTML=v5AlertsView();}
  if(state.view==='backtest'){els.title.textContent='Strategy Lab';els.content.innerHTML=v5StrategyLabView();setTimeout(function(){const b=$('#v5RunStrategy');if(b)b.onclick=v5RunStrategyLab;},0);}
  if(state.view==='health'){els.title.textContent='Data Health';els.content.innerHTML=v5HealthView();setTimeout(function(){v5LoadHealth();const b=$('#refreshHealth');if(b)b.onclick=v5LoadHealth;},0);}
};

const v5JournalKey='bist-ai-research-journal';
function v5JournalLoad(){try{return JSON.parse(localStorage.getItem(v5JournalKey)||'[]')}catch(e){return[]}}
function v5JournalStore(items){localStorage.setItem(v5JournalKey,JSON.stringify(items.slice(0,250)))}

function v5CatalystView(){
  const codes=state.watchlist.size?[...state.watchlist]:[...state.scan.values()].sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0)).slice(0,8).map(x=>x.ticker);
  return '<div class="panel"><div class="panelHead"><div><h2>Catalyst Calendar</h2><p>'+(state.watchlist.size?'Watchlist':'Top alpha adayları')+' · KAP finansal takvim ve önemli olaylar</p></div><span class="pill">'+codes.length+' HİSSE</span></div><div id="catalystResult"><div class="loading">Katalizörler yükleniyor…</div></div></div>';
}
async function v5LoadCatalysts(){
  const codes=state.watchlist.size?[...state.watchlist]:[...state.scan.values()].sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0)).slice(0,8).map(x=>x.ticker);
  const box=$('#catalystResult');if(!box)return;
  if(!codes.length){box.innerHTML='<div class="empty">Katalizör için önce tarama veya Watchlist gerekli.</div>';return;}
  try{
    const d=await getJSON('/api/catalysts?codes='+encodeURIComponent(codes.join(',')));
    const rows=d.events||[];
    box.innerHTML=rows.length?'<div class="timeline">'+rows.map(function(x){
      return '<a class="timelineItem" href="'+(x.url||'#')+'" target="_blank" rel="noopener"><span>'+(x.date||'Güncel')+'</span><strong>'+x.ticker+' · '+x.title+'</strong><p>'+((x.detail||'').slice(0,180))+'</p><small>'+x.type+' · Önem '+(x.materiality||0)+(x.sentiment_score!=null?' · Etki '+x.sentiment_score:'')+'</small></a>';
    }).join('')+'</div>':'<div class="empty">Katalizör bulunamadı.</div>';
  }catch(e){box.innerHTML='<div class="empty">Catalyst Calendar hatası: '+e.message+'</div>';}
}

function v5SaveCurrentJournal(){
  const note=($('#v5JournalNote')?.value||'').trim();
  const tech=state.scan.get(state.current)||{};
  const res=state.researchCache.get(state.current)||{};
  const items=v5JournalLoad();
  items.unshift({
    id:Date.now(),time:new Date().toLocaleString('tr-TR'),ticker:state.current,note:note,
    price:tech.price??null,short:tech.short_score??null,long:tech.long_score??null,alpha:tech.alpha_score??null,risk:tech.risk??null,
    researchShort:res.short_research_score??null,researchLong:res.long_research_score??null,
    strengths:res.strengths||[],flags:res.flags||[]
  });
  v5JournalStore(items);
  const b=$('#v5JournalSave');if(b){b.textContent='Kaydedildi ✓';setTimeout(function(){b.textContent='Research Snapshot Kaydet';},1200);}
}
function v5AttachJournalQuick(){
  const panel=$('#content .panel');if(!panel||$('#v5JournalQuick'))return;
  panel.insertAdjacentHTML('beforeend','<div id="v5JournalQuick" class="journalQuick"><textarea id="v5JournalNote" placeholder="Tez, risk, katalizör veya izlenecek seviye notu…"></textarea><button class="toolbtn" id="v5JournalSave">Research Snapshot Kaydet</button></div>');
  const b=$('#v5JournalSave');if(b)b.onclick=v5SaveCurrentJournal;
}
function v5DeleteJournal(id){v5JournalStore(v5JournalLoad().filter(x=>x.id!==id));render()}
window.v5DeleteJournal=v5DeleteJournal;

function v5JournalView(){
  const items=v5JournalLoad();
  return '<div class="panel"><div class="panelHead"><div><h2>Research Journal</h2><p>Geçmiş tezleri, model snapshotlarını ve sonradan gerçekleşen fiyat hareketini karşılaştır</p></div><span class="pill">'+items.length+' SNAPSHOT</span></div>'+
    (items.length?'<div class="journalList">'+items.map(function(x){
      const now=state.scan.get(x.ticker);const perf=(now&&now.price&&x.price)?(now.price/x.price-1)*100:null;
      return '<div class="journalItem"><div class="journalHead"><strong>'+x.ticker+'</strong><span>'+x.time+'</span></div><div class="journalScores"><b>Tech '+(x.short??'—')+'/'+(x.long??'—')+'</b><b>Research '+(x.researchShort??'—')+'/'+(x.researchLong??'—')+'</b><b class="'+(perf==null?'':cls(perf))+'">'+(perf!=null?'Fiyat '+pct(perf):'Kayıt ₺'+val4(x.price,2))+'</b></div><p>'+(x.note||'Not yok')+'</p><small>'+([...(x.strengths||[]),...(x.flags||[])].join(' · ')||'')+'</small><div class="journalActions"><button class="toolbtn" onclick="openStock(\''+x.ticker+'\')">Aç</button><button class="dangerBtn" onclick="v5DeleteJournal('+x.id+')">Sil</button></div></div>';
    }).join('')+'</div>':'<div class="empty">Henüz snapshot yok. Hisse detay ekranından kaydet.</div>')+'</div>';
}

function v5AllocationCompareHtml(d){
  return '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Yöntem</th><th>Getiri</th><th>Volatilite</th><th>Sharpe</th><th>Max DD</th><th>VaR95</th><th>CVaR95</th><th>Çeşitlendirme</th></tr></thead><tbody>'+(d.rows||[]).map(function(x){
    return '<tr><td>'+x.method+'</td><td>'+pct(x.annual_return_pct)+'</td><td>'+pct(x.annual_volatility_pct)+'</td><td>'+x.sharpe_proxy+'</td><td>'+pct(x.max_drawdown_pct)+'</td><td>'+pct(x.var95_daily_pct)+'</td><td>'+pct(x.cvar95_daily_pct)+'</td><td>'+x.diversification_score+'</td></tr>';
  }).join('')+'</tbody></table></div>';
}
async function v5LoadAllocationCompare(){
  const box=$('#v5AllocationCompare');if(!box)return;
  const codes=[...state.scan.values()].filter(x=>(x.alpha_score||0)>=55).sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0)).slice(0,8).map(x=>x.ticker);
  if(!codes.length){box.innerHTML='<div class="empty">Yeterli aday yok.</div>';return;}
  try{const d=await getJSON('/api/portfolio-allocations?codes='+encodeURIComponent(codes.join(',')));box.innerHTML=v5AllocationCompareHtml(d);}
  catch(e){box.innerHTML='<div class="empty">Allocation Optimizer hatası: '+e.message+'</div>';}
}

const v5RenderBase2=render;
render=function(){
  v5RenderBase2();
  if(state.view==='catalysts'){els.title.textContent='Catalyst Calendar';els.content.innerHTML=v5CatalystView();setTimeout(v5LoadCatalysts,0);}
  if(state.view==='journal'){els.title.textContent='Research Journal';els.content.innerHTML=v5JournalView();}
  if(state.view==='detail')setTimeout(v5AttachJournalQuick,0);
  if(state.view==='portfolio'){
    els.content.insertAdjacentHTML('beforeend','<div class="panel portfolioRiskPanel"><div class="panelHead"><div><h2>Allocation Optimizer</h2><p>Equal · inverse-vol · min-variance · risk-parity</p></div><span class="pill">HISTORICAL</span></div><div id="v5AllocationCompare"><div class="loading">Tahsis yöntemleri karşılaştırılıyor…</div></div></div>');
    setTimeout(v5LoadAllocationCompare,0);
  }
};
