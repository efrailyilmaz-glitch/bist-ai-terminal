
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
