const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const els={content:$('#content'),title:$('#pageTitle'),subtitle:$('#subtitle'),tickerbar:$('#tickerbar'),search:$('#globalSearch'),scanBtn:$('#scanBtn'),scanStatus:$('#scanStatus'),systemMode:$('#systemMode')};
const state={view:'overview',universe:[],meta:new Map(),scan:new Map(),market:{},scanning:false,scanned:0,total:0,current:'ASELS',chart:null,chartPeriod:'1y',chartInterval:'1d'};
const fmt=(n,d=2)=>Number(n||0).toLocaleString('tr-TR',{maximumFractionDigits:d,minimumFractionDigits:0});
const pct=n=>`${n>=0?'+':''}${fmt(n,2)}%`; const cls=n=>Number(n)>=0?'up':'down';
const tagClass=s=>s==='GÜÇLÜ'?'':s==='POZİTİF'?'':s==='NÖTR'?'neutral':'weak';
async function getJSON(url){const r=await fetch(url); if(!r.ok) throw new Error(`${r.status} ${url}`); return r.json();}
async function init(){
  try{
    const [u,m]=await Promise.all([getJSON('/api/universe'),getJSON('/api/market')]);
    state.universe=u.rows||[]; state.total=u.count||state.universe.length; state.market=m||{};
    state.universe.forEach(x=>state.meta.set(x.ticker,x));
    els.systemMode.textContent=`V3 · ${u.source||'UNIVERSE'}`; els.scanStatus.textContent=`${state.total} şirket bulundu`;
    renderTickerbar(); render(); setTimeout(()=>scanAll(false),250);
  }catch(e){els.content.innerHTML=`<div class="empty">Başlatma hatası: ${e.message}</div>`;}
}
function renderTickerbar(){
  const m=state.market; const arr=[
    ['BIST 100',m.xu100?fmt(m.xu100):'N/A',m.xu100_change||0],['USD/TRY',m.usdtry?fmt(m.usdtry,4):'N/A',m.usdtry_change||0],['S&P 500',m.sp500?fmt(m.sp500):'N/A',m.sp500_change||0],
    ['BIST Evreni',state.total||'—',null],['Taranan',`${state.scanned}/${state.total||'—'}`,null],['Veri Modu',m.mode||'YAHOO',null]
  ];
  els.tickerbar.innerHTML=arr.map(x=>`<div class="metric"><span>${x[0]}</span><b>${x[1]}</b>${x[2]===null?'':`<small class="${cls(x[2])}">${pct(x[2])}</small>`}</div>`).join('');
}
async function scanAll(force=true){
  if(state.scanning) return; state.scanning=true; if(force){state.scan.clear();state.scanned=0;}
  els.scanBtn.textContent='Taranıyor…'; const batch=60;
  for(let offset=0;offset<state.total;offset+=batch){
    try{
      const r=await getJSON(`/api/scan?offset=${offset}&limit=${batch}`);
      (r.rows||[]).forEach(x=>state.scan.set(x.ticker,x)); state.scanned=Math.min(state.total,offset+(r.requested||batch));
      updateRegime(); els.scanStatus.textContent=`Evren taranıyor ${state.scanned}/${state.total} · fiyat bulunan ${state.scan.size}`; renderTickerbar();
      if(['overview','all','short','long'].includes(state.view)) render(false);
    }catch(e){els.scanStatus.textContent=`Tarama ${offset}-${offset+batch} atlandı`;}
  }
  updateRegime(); state.scanning=false; els.scanBtn.textContent='Tüm Evreni Tara'; els.scanStatus.textContent=`Tarama tamamlandı · ${state.scan.size}/${state.total} fiyat verisi`;
  renderTickerbar(); render(false);
}
function topBy(key,n=10){return [...state.scan.values()].sort((a,b)=>(b[key]||0)-(a[key]||0)).slice(0,n)}
function updateRegime(){
  const a=[...state.scan.values()]; if(a.length<10)return;
  const adv=a.filter(x=>x.change>0).length, dec=a.filter(x=>x.change<0).length;
  const breadth=Math.round(adv/a.length*100), avg=Math.round(a.reduce((s,x)=>s+(x.short_score||50),0)/a.length);
  state.market.advancers=adv; state.market.decliners=dec; state.market.breadth=breadth;
  state.market.regime=(breadth>=58&&avg>=60)?'RISK-ON / BULL':(breadth<=42&&avg<=45)?'RISK-OFF / BEAR':'NÖTR / TRANSITION';
}
function candidateList(rows,key){return rows.map((r,i)=>{const meta=state.meta.get(r.ticker)||{};const sig=key==='short_score'?r.short_signal:r.long_signal;const reasons=(key==='short_score'?r.reasons_short:r.reasons_long)||[];return `<div class="candidate" onclick="openStock('${r.ticker}')"><span class="rank">${String(i+1).padStart(2,'0')}</span><strong>${r.ticker}</strong><div><div>${meta.name||r.name||''}</div><div class="reason">${reasons.join(' · ')||r.trend||'veri hesaplandı'}</div></div><span class="score">${r[key]||0}</span><span class="${cls(r.change)}">${pct(r.change)}</span><span class="tag ${tagClass(sig)}">${sig}</span></div>`}).join('')||'<div class="empty">Tarama sonuçları yükleniyor…</div>'}
function overview(){
  const sh=topBy('short_score',8), lg=topBy('long_score',8); const progress=state.total?Math.round(state.scanned/state.total*100):0;
  return `<div class="grid2"><div class="panel"><div class="panelHead"><div><h2>Kısa Vade Alpha Radar</h2><p>Momentum · hacim · breakout · MA20/50 · RSI</p></div><span class="pill">SHORT HORIZON</span></div>${candidateList(sh,'short_score')}</div>
  <div class="panel"><div class="panelHead"><div><h2>Evren Motoru</h2><p>KAP şirket evreni + Yahoo fiyat katmanı</p></div></div><div class="hero"><small>Tarama kapsamı</small><b>${state.scanned}/${state.total}</b><div class="progress"><i style="width:${progress}%"></i></div><small>${state.scan.size} sembolde fiyat/teknik veri üretildi</small></div><div class="stats"><div class="stat"><span>Güçlü kısa</span><b>${[...state.scan.values()].filter(x=>x.short_score>=80).length}</b></div><div class="stat"><span>Güçlü uzun</span><b>${[...state.scan.values()].filter(x=>x.long_score>=80).length}</b></div><div class="stat"><span>Breakout</span><b>${[...state.scan.values()].filter(x=>x.breakout20).length}</b></div><div class="stat"><span>Yukarı trend</span><b>${[...state.scan.values()].filter(x=>x.trend==='YUKARI').length}</b></div><div class="stat"><span>Hacim >1.5x</span><b>${[...state.scan.values()].filter(x=>x.volume_ratio>1.5).length}</b></div><div class="stat"><span>Veri yok</span><b>${Math.max(0,state.total-state.scan.size)}</b></div></div></div>
  <div class="panel"><div class="panelHead"><div><h2>Uzun Vade Alpha Radar</h2><p>MA50/200 · 3/6 ay momentum · volatilite filtresi</p></div><span class="pill">LONG HORIZON</span></div>${candidateList(lg,'long_score')}</div>
  <div class="panel"><div class="panelHead"><div><h2>Global Risk & Piyasa Rejimi</h2><p>BIST · ABD · DXY · faiz · kur birleşik risk skoru</p></div></div><div class="hero"><small>Aktif durum</small><b>${state.market.regime||'NÖTR'}</b><small>Global skor ${state.market.global_score??50}/100 · ${state.market.mode||'LIVE / YAHOO'}</small></div><div class="stats"><div class="stat"><span>Nasdaq</span><b class="${cls(state.market.nasdaq_change||0)}">${pct(state.market.nasdaq_change||0)}</b></div><div class="stat"><span>DXY</span><b class="${cls(-(state.market.dxy_change||0))}">${pct(state.market.dxy_change||0)}</b></div><div class="stat"><span>US10Y</span><b>${state.market.us10y?fmt(state.market.us10y):'—'}</b></div><div class="stat"><span>Altın</span><b class="${cls(state.market.gold_change||0)}">${pct(state.market.gold_change||0)}</b></div><div class="stat"><span>Petrol</span><b class="${cls(state.market.oil_change||0)}">${pct(state.market.oil_change||0)}</b></div><div class="stat"><span>Breadth</span><b>%${state.market.breadth||0}</b></div></div></div></div>`;
}
function allStocks(){
  const q=(els.search.value||'').trim().toUpperCase(); let rows=state.universe.filter(x=>!q||x.ticker.includes(q)||(x.name||'').toUpperCase().includes(q));
  return `<div class="panel"><div class="panelHead"><div><h2>Tüm BIST Şirketleri</h2><p>${rows.length} / ${state.total} şirket · fiyatlar tarama geldikçe doldurulur</p></div><span class="pill">KAP UNIVERSE</span></div><div class="tableTools"><input id="tableSearch" value="${q}" placeholder="Kod / unvan filtrele"><select id="tableSort"><option value="ticker">Koda göre</option><option value="short">Kısa skor</option><option value="long">Uzun skor</option><option value="change">Günlük değişim</option></select></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Kod</th><th>Şirket</th><th>Fiyat</th><th>Değişim</th><th>Kısa</th><th>Uzun</th><th>RSI</th><th>Hacim</th><th>Trend</th></tr></thead><tbody id="allBody">${stockRows(rows)}</tbody></table></div></div>`;
}
function stockRows(rows,sort='ticker'){
  rows=[...rows]; if(sort==='short') rows.sort((a,b)=>(state.scan.get(b.ticker)?.short_score||-1)-(state.scan.get(a.ticker)?.short_score||-1));
  if(sort==='long') rows.sort((a,b)=>(state.scan.get(b.ticker)?.long_score||-1)-(state.scan.get(a.ticker)?.long_score||-1));
  if(sort==='change') rows.sort((a,b)=>(state.scan.get(b.ticker)?.change||-999)-(state.scan.get(a.ticker)?.change||-999));
  return rows.map(m=>{const r=state.scan.get(m.ticker);return `<tr onclick="openStock('${m.ticker}')"><td><strong>${m.ticker}</strong></td><td>${m.name||''}</td>${r?`<td>₺${fmt(r.price)}</td><td class="${cls(r.change)}">${pct(r.change)}</td><td>${r.short_score}</td><td>${r.long_score}</td><td>${r.rsi}</td><td>${r.volume_ratio}x</td><td>${r.trend}</td>`:`<td colspan="7" class="pending">Tarama bekleniyor</td>`}</tr>`}).join('');
}
function horizonView(kind){const key=kind==='short'?'short_score':'long_score';const rows=[...state.scan.values()].sort((a,b)=>b[key]-a[key]);return `<div class="panel"><div class="panelHead"><div><h2>${kind==='short'?'Kısa Vade':'Uzun Vade'} Araştırma Adayları</h2><p>${kind==='short'?'Günler–haftalar: momentum, breakout, hacim ve kısa trend':'Aylar: MA200, 3/6 ay momentum ve volatilite dengesi'}</p></div><span class="pill">${state.scan.size} ANALYZED</span></div>${candidateList(rows.slice(0,100),key)}</div>`}
function anomalyView(){
  const rows=[...state.scan.values()].sort((a,b)=>(b.anomaly_score||0)-(a.anomaly_score||0)).slice(0,100);
  return `<div class="panel"><div class="panelHead"><div><h2>Anomali Radar</h2><p>Hacim sıçraması · sert günlük hareket · volatilite sapması. Bu ekran manipülasyon suçu iddiası değildir.</p></div><span class="pill">RISK MONITOR</span></div>${rows.map((r,i)=>{const m=state.meta.get(r.ticker)||{};return `<div class="candidate" onclick="openStock('${r.ticker}')"><span class="rank">${String(i+1).padStart(2,'0')}</span><strong>${r.ticker}</strong><div><div>${m.name||''}</div><div class="reason">Hacim ${r.volume_ratio}x · Vol %${r.volatility} · Gün ${pct(r.change)}</div></div><span class="score">${r.anomaly_score||0}</span><span class="${cls(r.change)}">${pct(r.change)}</span><span class="tag ${(r.anomaly_score||0)>65?'weak':'neutral'}">${(r.anomaly_score||0)>65?'YÜKSEK':'İZLE'}</span></div>`}).join('')||'<div class="empty">Tarama sonuçları bekleniyor…</div>'}</div>`;
}
function portfolioView(){
  const rows=[...state.scan.values()].filter(x=>(x.alpha_score||0)>=55).sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0)).slice(0,10);
  const raw=rows.map(x=>Math.max(1,(x.alpha_score||50)*(100-Math.min(90,x.risk||50))));
  const sum=raw.reduce((a,b)=>a+b,0)||1;
  return `<div class="panel"><div class="panelHead"><div><h2>Model Portföy</h2><p>Alpha skoru + risk azaltımı ile oluşturulan örnek nicel araştırma sepeti; kişiye özel yatırım tavsiyesi değildir.</p></div><span class="pill">QUANT BASKET</span></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Kod</th><th>Şirket</th><th>Model ağırlık</th><th>Alpha</th><th>Kısa</th><th>Uzun</th><th>Risk</th><th>Smart Money</th></tr></thead><tbody>${rows.map((r,i)=>{const m=state.meta.get(r.ticker)||{};const w=raw[i]/sum*100;return `<tr onclick="openStock('${r.ticker}')"><td><strong>${r.ticker}</strong></td><td>${m.name||''}</td><td>%${fmt(w,1)}</td><td>${r.alpha_score||0}</td><td>${r.short_score}</td><td>${r.long_score}</td><td>${r.risk}</td><td>${r.smart_money_score||0}</td></tr>`}).join('')}</tbody></table></div></div>`;
}
async function openStock(t){state.current=t;state.view='detail';$$('.nav').forEach(x=>x.classList.toggle('active',x.dataset.view==='detail'));render();}
function detailShell(){const r=state.scan.get(state.current)||{};const m=state.meta.get(state.current)||{};return `<div class="panel"><div class="chartTop"><div class="chartTitle"><h2>${state.current} · ${m.name||''}</h2><p>${r.price?`₺${fmt(r.price)} · ${pct(r.change)} · RSI ${r.rsi} · Hacim ${r.volume_ratio}x`:'Fiyat verisi yükleniyor'}</p></div><div class="chartTools"><button data-period="1mo">1A</button><button data-period="3mo">3A</button><button data-period="6mo">6A</button><button data-period="1y" class="active">1Y</button><button data-period="2y">2Y</button><button data-period="5y">5Y</button><button data-interval="60m">1S</button><button data-interval="1d" class="active">1G</button><button data-interval="1wk">1H</button></div></div><div id="tvChart" class="chartbox"></div>${detailStats(r)}<div class="grid2"><div class="recommendBox"><h3>Kısa Vade Modeli · ${r.short_score??'—'}/100</h3><div class="chips">${(r.reasons_short||['Tarama verisi bekleniyor']).map(x=>`<span class="chip">${x}</span>`).join('')}</div>${r.target_short?`<p>ATR bölgesi: hedef <b class="up">₺${fmt(r.target_short)}</b> · risk stop <b class="down">₺${fmt(r.stop_short)}</b></p>`:''}</div><div class="recommendBox"><h3>Uzun Vade Modeli · ${r.long_score??'—'}/100</h3><div class="chips">${(r.reasons_long||['Tarama verisi bekleniyor']).map(x=>`<span class="chip">${x}</span>`).join('')}</div><p class="muted">Bu skor şirket değerlemesi değil; trend/momentum/volatilite tabanlı nicel araştırma puanıdır.</p></div></div></div>`}
function detailStats(r){const a=[['Kısa skor',r.short_score],['Uzun skor',r.long_score],['20G momentum',r.momentum_20!=null?pct(r.momentum_20):'—'],['3A momentum',r.momentum_60!=null?pct(r.momentum_60):'—'],['Volatilite',r.volatility!=null?`${r.volatility}%`:'—'],['Risk',r.risk!=null?`${r.risk}/100`:'—']];return `<div class="stats">${a.map(x=>`<div class="stat"><span>${x[0]}</span><b>${x[1]??'—'}</b></div>`).join('')}</div>`}
async function ensureTickerScan(t){if(state.scan.has(t))return;try{const r=await getJSON(`/api/scan?codes=${encodeURIComponent(t)}`);(r.rows||[]).forEach(x=>state.scan.set(x.ticker,x));}catch(e){}}
async function loadChart(){
  await ensureTickerScan(state.current); if(state.view!=='detail')return; const el=$('#tvChart'); if(!el)return;
  try{
    const d=await getJSON(`/api/chart/${state.current}?period=${state.chartPeriod}&interval=${state.chartInterval}`);
    if(!d.candles?.length){el.innerHTML='<div class="empty">Grafik verisi bulunamadı</div>';return;}
    if(state.chart){try{state.chart.remove()}catch(e){} state.chart=null;}
    const chart=LightweightCharts.createChart(el,{autoSize:true,layout:{background:{type:'solid',color:'#07121a'},textColor:'#8198a9'},grid:{vertLines:{color:'#102431'},horzLines:{color:'#102431'}},rightPriceScale:{borderColor:'#1a3344'},timeScale:{borderColor:'#1a3344',timeVisible:state.chartInterval!=='1d'&&state.chartInterval!=='1wk'}});
    state.chart=chart; const candle=chart.addSeries(LightweightCharts.CandlestickSeries,{upColor:'#28d17c',downColor:'#ff5e72',borderVisible:false,wickUpColor:'#28d17c',wickDownColor:'#ff5e72'}); candle.setData(d.candles);
    const vol=chart.addSeries(LightweightCharts.HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:''}); vol.priceScale().applyOptions({scaleMargins:{top:.82,bottom:0}}); vol.setData(d.candles.map(x=>({time:x.time,value:x.volume,color:x.close>=x.open?'rgba(40,209,124,.35)':'rgba(255,94,114,.35)'})));
    const ma20=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#49d7ff',priceLineVisible:false,lastValueVisible:false});ma20.setData(d.ma20||[]);
    const ma50=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#f6b94a',priceLineVisible:false,lastValueVisible:false});ma50.setData(d.ma50||[]);
    const ma200=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#a77cff',priceLineVisible:false,lastValueVisible:false});ma200.setData(d.ma200||[]); chart.timeScale().fitContent();
  }catch(e){el.innerHTML=`<div class="empty">Grafik yüklenemedi: ${e.message}</div>`;}
}
async function backtestView(){return `<div class="panel"><div class="panelHead"><div><h2>Backtest Lab · ${state.current}</h2><p>MA20/MA50 trend stratejisi · gerçek tarihsel fiyat serisi</p></div><button class="toolbtn" id="runBacktest">Çalıştır</button></div><div id="btResult" class="empty">Backtest çalıştırılmayı bekliyor.</div></div>`}
async function runBacktest(){const box=$('#btResult');if(!box)return;box.innerHTML='<div class="loading">Backtest hesaplanıyor…</div>';try{const b=await getJSON(`/api/backtest/${state.current}?fast=20&slow=50&period=2y`);if(b.error)throw new Error(b.error);box.innerHTML=`<div class="btgrid">${[['Strateji',pct(b.return_pct)],['Buy & Hold',pct(b.buy_hold_pct)],['Alpha',pct(b.alpha_pct)],['Sharpe',b.sharpe],['Max DD',pct(b.max_drawdown)],['İşlem',b.trades]].map(x=>`<div class="stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('')}</div><p class="muted">Geçmiş performans gelecekteki sonucu garanti etmez. İşlem maliyeti/slippage katmanı sonraki motor sürümünde parametreleştirilecek.</p>`;}catch(e){box.innerHTML=`<div class="empty">Backtest hatası: ${e.message}</div>`}}
function kapView(){return `<div class="kapcard"><h2>KAP Radar</h2><p>Şirket evreni KAP'ın BIST şirketleri listesinden dinamik alınıyor. Bildirim NLP katmanı ayrı servis olarak hazırlanıyor.</p><p><b>Neden şimdilik sahte akış yok?</b> Resmî gerçek zamanlı KAP veri yayını lisans/abonelik gerektirebildiği için, terminal gerçek veri bağlantısı kurulmadan yapay “canlı bildirim” göstermiyor.</p><a href="https://www.kap.org.tr/tr/bildirim-sorgu" target="_blank" rel="noopener">KAP bildirim sorgu ↗</a></div>`}
function render(){
  if(state.view==='overview'){els.title.textContent='Piyasa Komuta Merkezi';els.content.innerHTML=overview();}
  if(state.view==='all'){els.title.textContent='Tüm BIST Şirketleri';els.content.innerHTML=allStocks();bindTable();}
  if(state.view==='short'){els.title.textContent='Kısa Vade Alpha Radar';els.content.innerHTML=horizonView('short');}
  if(state.view==='long'){els.title.textContent='Uzun Vade Alpha Radar';els.content.innerHTML=horizonView('long');}
  if(state.view==='anomaly'){els.title.textContent='Anomali Radar';els.content.innerHTML=anomalyView();}
  if(state.view==='portfolio'){els.title.textContent='Model Portföy';els.content.innerHTML=portfolioView();}
  if(state.view==='detail'){els.title.textContent=`${state.current} Hisse Analizi`;els.content.innerHTML=detailShell();bindChartTools();setTimeout(loadChart,0);}
  if(state.view==='backtest'){els.title.textContent='Backtest Lab';backtestView().then(h=>{els.content.innerHTML=h;$('#runBacktest').onclick=runBacktest});}
  if(state.view==='kap'){els.title.textContent='KAP Radar';els.content.innerHTML=kapView();}
}
function bindTable(){const s=$('#tableSearch'),sort=$('#tableSort'); if(s)s.oninput=e=>{els.search.value=e.target.value;render()};if(sort)sort.onchange=e=>{const q=(els.search.value||'').trim().toUpperCase();const rows=state.universe.filter(x=>!q||x.ticker.includes(q)||(x.name||'').toUpperCase().includes(q));$('#allBody').innerHTML=stockRows(rows,e.target.value)}}
function bindChartTools(){$$('.chartTools button').forEach(b=>b.onclick=()=>{if(b.dataset.period){state.chartPeriod=b.dataset.period;$$('[data-period]').forEach(x=>x.classList.toggle('active',x.dataset.period===state.chartPeriod))}if(b.dataset.interval){state.chartInterval=b.dataset.interval;$$('[data-interval]').forEach(x=>x.classList.toggle('active',x.dataset.interval===state.chartInterval))}loadChart()})}
$$('.nav').forEach(b=>b.onclick=()=>{$$('.nav').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.view=b.dataset.view;render()});
els.scanBtn.onclick=()=>scanAll(true);
els.search.oninput=e=>{if(state.view==='all'){render();return;}const q=e.target.value.trim().toUpperCase();if(q.length>=2){const m=state.universe.find(x=>x.ticker===q)||state.universe.find(x=>x.ticker.startsWith(q));if(m)openStock(m.ticker)}};
window.openStock=openStock; init();
