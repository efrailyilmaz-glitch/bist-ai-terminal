const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const els={content:$('#content'),title:$('#pageTitle'),subtitle:$('#subtitle'),tickerbar:$('#tickerbar'),search:$('#globalSearch'),scanBtn:$('#scanBtn'),scanStatus:$('#scanStatus'),systemMode:$('#systemMode')};
const state={view:'overview',universe:[],meta:new Map(),scan:new Map(),market:{},scanning:false,scanned:0,total:0,current:'ASELS',chart:null,chartPeriod:'1y',chartInterval:'1d',factorRows:[],researchCache:new Map(),watchlist:new Set(JSON.parse(localStorage.getItem('bist-ai-watchlist')||'[]')),indicators:{ema:true,bb:true,rsi:true,stoch:true,macd:true,supertrend:true,ichimoku:false,levels:true}};
const SCAN_CACHE_KEY='bist-ai-scan-v6';
function restoreScanCache(){
  try{
    const cached=JSON.parse(localStorage.getItem(SCAN_CACHE_KEY)||'null');
    if(!cached||!cached.ts||Date.now()-cached.ts>15*60*1000||!Array.isArray(cached.rows))return false;
    cached.rows.forEach(x=>state.scan.set(x.ticker,x));
    state.scanned=Math.min(state.total,cached.scanned||cached.rows.length);
    return state.scan.size>0;
  }catch(e){return false}
}
function persistScanCache(){
  try{
    const rows=[...state.scan.values()];
    localStorage.setItem(SCAN_CACHE_KEY,JSON.stringify({ts:Date.now(),scanned:state.scanned,rows:rows}));
  }catch(e){}
}

const fmt=(n,d=2)=>Number(n||0).toLocaleString('tr-TR',{maximumFractionDigits:d,minimumFractionDigits:0});
const pct=n=>`${n>=0?'+':''}${fmt(n,2)}%`; const cls=n=>Number(n)>=0?'up':'down';
const tagClass=s=>s==='GÜÇLÜ'?'':s==='POZİTİF'?'':s==='NÖTR'?'neutral':'weak';
async function getJSON(url){const r=await fetch(url); if(!r.ok) throw new Error(`${r.status} ${url}`); return r.json();}
async function init(){
  try{
    const [u,m]=await Promise.all([getJSON('/api/universe'),getJSON('/api/market')]);
    state.universe=u.rows||[]; state.total=u.count||state.universe.length; state.market=m||{};
    state.universe.forEach(x=>state.meta.set(x.ticker,x));
    const restored=restoreScanCache();
    els.systemMode.textContent=`V6 · ${u.source||'UNIVERSE'}`;
    els.scanStatus.textContent=restored?`Önbellekten ${state.scan.size} hisse · arka planda yenileniyor`:`${state.total} şirket bulundu`;
    if(restored)updateRegime();
    renderTickerbar(); render(); setTimeout(()=>scanAll(false),restored?900:150);
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
  if(state.scanning)return;
  state.scanning=true;
  if(force){state.scan.clear();state.scanned=0;try{localStorage.removeItem(SCAN_CACHE_KEY)}catch(e){}}
  els.scanBtn.textContent='Taranıyor…';
  const batch=100, offsets=[];
  for(let offset=0;offset<state.total;offset+=batch)offsets.push(offset);
  let cursor=0,completed=0,lastPaint=0,lastPersist=0;
  async function worker(){
    while(true){
      const idx=cursor++;
      if(idx>=offsets.length)return;
      const offset=offsets[idx];
      try{
        const r=await getJSON(`/api/scan?offset=${offset}&limit=${batch}`);
        (r.rows||[]).forEach(x=>state.scan.set(x.ticker,x));
        completed+=r.requested||Math.min(batch,state.total-offset);
        state.scanned=Math.min(state.total,Math.max(state.scanned,completed));
        updateRegime();
        const now=Date.now();
        els.scanStatus.textContent=`Evren taranıyor · ${state.scan.size} fiyat verisi · ${Math.min(state.total,completed)}/${state.total} yenilendi`;
        renderTickerbar();
        if(now-lastPaint>900&&['overview','short','long','setups','anomaly'].includes(state.view)){render(false);lastPaint=now}
        if(now-lastPersist>2500){persistScanCache();lastPersist=now}
      }catch(e){
        completed+=Math.min(batch,state.total-offset);
        els.scanStatus.textContent=`Bazı tarama paketleri atlandı · ${state.scan.size} veri mevcut`;
      }
    }
  }
  await Promise.all([worker(),worker()]);
  state.scanned=state.total;
  updateRegime();persistScanCache();
  state.scanning=false;els.scanBtn.textContent='Tüm Evreni Tara';
  els.scanStatus.textContent=`Tarama tamamlandı · ${state.scan.size}/${state.total} fiyat verisi`;
  renderTickerbar();render(false);
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
  return `<div class="panel"><div class="panelHead"><div><h2>Tüm BIST Şirketleri</h2><p>${rows.length} / ${state.total} şirket · fiyatlar tarama geldikçe doldurulur</p></div><span class="pill">KAP UNIVERSE</span></div><div class="tableTools"><input id="tableSearch" value="${q}" placeholder="Kod / unvan filtrele"><select id="tableSort"><option value="ticker">Koda göre</option><option value="short">Kısa skor</option><option value="long">Uzun skor</option><option value="change">Günlük değişim</option><option value="adx">ADX</option><option value="rs">RS vs XU100</option></select></div><div class="tableWrap"><table class="stockTable"><thead><tr><th>Kod</th><th>Şirket</th><th>Fiyat</th><th>Değişim</th><th>Kısa</th><th>Uzun</th><th>RSI</th><th>Stoch</th><th>MACD H</th><th>ADX</th><th>MFI</th><th>RS20</th><th>Hacim</th><th>Trend</th></tr></thead><tbody id="allBody">${stockRows(rows)}</tbody></table></div></div>`;
}
function stockRows(rows,sort='ticker'){
  rows=[...rows];
  if(sort==='short') rows.sort((a,b)=>(state.scan.get(b.ticker)?.short_score||-1)-(state.scan.get(a.ticker)?.short_score||-1));
  if(sort==='long') rows.sort((a,b)=>(state.scan.get(b.ticker)?.long_score||-1)-(state.scan.get(a.ticker)?.long_score||-1));
  if(sort==='change') rows.sort((a,b)=>(state.scan.get(b.ticker)?.change||-999)-(state.scan.get(a.ticker)?.change||-999));
  if(sort==='adx') rows.sort((a,b)=>(state.scan.get(b.ticker)?.adx||-1)-(state.scan.get(a.ticker)?.adx||-1));
  if(sort==='rs') rows.sort((a,b)=>(state.scan.get(b.ticker)?.relative_strength_20||-999)-(state.scan.get(a.ticker)?.relative_strength_20||-999));
  return rows.map(m=>{const r=state.scan.get(m.ticker);return `<tr onclick="openStock('${m.ticker}')"><td><strong>${m.ticker}</strong></td><td>${m.name||''}</td>${r?`<td>₺${fmt(r.price)}</td><td class="${cls(r.change)}">${pct(r.change)}</td><td>${r.short_score}</td><td>${r.long_score}</td><td>${fmt(r.rsi,1)}</td><td>${fmt(r.stoch_rsi_k,1)}</td><td class="${cls(r.macd_hist)}">${fmt(r.macd_hist,4)}</td><td>${fmt(r.adx,1)}</td><td>${fmt(r.mfi,1)}</td><td class="${cls(r.relative_strength_20)}">${pct(r.relative_strength_20)}</td><td>${r.volume_ratio}x</td><td>${r.trend}</td>`:`<td colspan="12" class="pending">Tarama bekleniyor</td>`}</tr>`}).join('');
}
function horizonView(kind){const key=kind==='short'?'short_score':'long_score';const rows=[...state.scan.values()].sort((a,b)=>b[key]-a[key]);return `<div class="panel"><div class="panelHead"><div><h2>${kind==='short'?'Kısa Vade':'Uzun Vade'} Araştırma Adayları</h2><p>${kind==='short'?'Günler–haftalar: momentum, breakout, hacim ve kısa trend':'Aylar: MA200, 3/6 ay momentum ve volatilite dengesi'}</p></div><span class="pill">${state.scan.size} ANALYZED</span></div>${candidateList(rows.slice(0,100),key)}</div>`}
function setupRows(rows,label){
  return rows.slice(0,30).map(function(r,i){
    const m=state.meta.get(r.ticker)||{};
    return '<div class="candidate" onclick="openStock(\''+r.ticker+'\')"><span class="rank">'+String(i+1).padStart(2,'0')+'</span><strong>'+r.ticker+'</strong><div><div>'+((m.name||r.name)||'')+'</div><div class="reason">'+label+' · RSI '+fmt(r.rsi,1)+' · ADX '+fmt(r.adx,1)+' · RS20 '+pct(r.relative_strength_20||0)+'</div></div><span class="score">'+(r.alpha_score||0)+'</span><span class="'+cls(r.change)+'">'+pct(r.change)+'</span><span class="tag">'+label+'</span></div>';
  }).join('')||'<div class="empty">Henüz eşleşme yok</div>';
}
function setupView(){
  const all=[...state.scan.values()];
  const golden=all.filter(x=>x.cross_event==='GOLDEN_CROSS').sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0));
  const squeeze=all.filter(x=>x.bollinger_squeeze).sort((a,b)=>(b.short_score||0)-(a.short_score||0));
  const bullDiv=all.filter(x=>x.rsi_divergence==='BULLISH'||x.macd_divergence==='BULLISH').sort((a,b)=>(b.short_score||0)-(a.short_score||0));
  const trend=all.filter(x=>x.supertrend==='BULLISH'&&x.ichimoku==='BULLISH').sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0));
  return '<div class="setupGrid">'+
    '<div class="panel"><div class="panelHead"><div><h2>Golden Cross</h2><p>EMA50 son dönemde EMA200 üzerine geçti</p></div><span class="pill">'+golden.length+'</span></div>'+setupRows(golden,'GOLDEN')+'</div>'+
    '<div class="panel"><div class="panelHead"><div><h2>Bollinger Squeeze</h2><p>Volatilite daralması · olası kırılım hazırlığı</p></div><span class="pill">'+squeeze.length+'</span></div>'+setupRows(squeeze,'SQUEEZE')+'</div>'+
    '<div class="panel"><div class="panelHead"><div><h2>Bullish Divergence</h2><p>Fiyat ile RSI/MACD arasında pozitif uyumsuzluk</p></div><span class="pill">'+bullDiv.length+'</span></div>'+setupRows(bullDiv,'DIVERGENCE')+'</div>'+
    '<div class="panel"><div class="panelHead"><div><h2>Trend Alignment</h2><p>Supertrend + Ichimoku aynı yönde pozitif</p></div><span class="pill">'+trend.length+'</span></div>'+setupRows(trend,'TREND')+'</div>'+
  '</div>';
}
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
function indicatorTone(label,value){
  if(value==null)return '';
  if(label==='RSI') return value>=70?'amber':value<=30?'down':'up';
  if(label==='Stoch RSI') return value>=80?'amber':value<=20?'down':'up';
  if(label==='ADX') return value>=25?'up':'';
  if(label==='MFI') return value>=80?'amber':value<=20?'down':'up';
  if(label==='MACD Hist') return value>=0?'up':'down';
  if(label==='RS vs XU100') return value>=0?'up':'down';
  return '';
}
function indicatorDashboard(r){
  const items=[
    ['RSI',r.rsi,r.rsi!=null?fmt(r.rsi,1):'—'],
    ['Stoch RSI',r.stoch_rsi_k,r.stoch_rsi_k!=null?`${fmt(r.stoch_rsi_k,1)} / ${fmt(r.stoch_rsi_d,1)}`:'—'],
    ['MACD Hist',r.macd_hist,r.macd_hist!=null?fmt(r.macd_hist,4):'—'],
    ['ADX',r.adx,r.adx!=null?fmt(r.adx,1):'—'],
    ['MFI',r.mfi,r.mfi!=null?fmt(r.mfi,1):'—'],
    ['ATR %',null,r.atr_pct!=null?`%${fmt(r.atr_pct,2)}`:'—'],
    ['Bollinger %B',null,r.bb_pct!=null?`${fmt(r.bb_pct,1)}`:'—'],
    ['OBV Trend',r.obv_trend,r.obv_trend!=null?fmt(r.obv_trend,3):'—'],
    ['RS vs XU100',r.relative_strength_20,r.relative_strength_20!=null?pct(r.relative_strength_20):'—'],
    ['Smart Money',null,r.smart_money_score!=null?`${r.smart_money_score}/100`:'—']
  ];
  return `<div class="indicatorGrid">${items.map(x=>`<div class="indicatorCard"><span>${x[0]}</span><b class="${indicatorTone(x[0],x[1])}">${x[2]}</b></div>`).join('')}</div>`;
}
function detailShell(){
  const r=state.scan.get(state.current)||{}, m=state.meta.get(state.current)||{};
  const p=state.chartPeriod, iv=state.chartInterval;
  return `<div class="panel">
    <div class="chartTop">
      <div class="chartTitle"><h2>${state.current} · ${m.name||''}</h2><p>${r.price?`₺${fmt(r.price)} · ${pct(r.change)} · Alpha ${r.alpha_score??'—'} · Risk ${r.risk??'—'}`:'Fiyat verisi yükleniyor'}</p></div>
      <div class="chartTools">
        ${[['1mo','1A'],['3mo','3A'],['6mo','6A'],['1y','1Y'],['2y','2Y'],['5y','5Y']].map(x=>`<button data-period="${x[0]}" class="${p===x[0]?'active':''}">${x[1]}</button>`).join('')}
        ${[['60m','1S'],['1d','1G'],['1wk','1H']].map(x=>`<button data-interval="${x[0]}" class="${iv===x[0]?'active':''}">${x[1]}</button>`).join('')}
      </div>
    </div>
    <div class="indicatorToolbar">
      <span>Göstergeler</span>
      ${[['ema','EMA 20/50/200'],['bb','Bollinger'],['supertrend','Supertrend'],['ichimoku','Ichimoku'],['levels','Destek/Direnç'],['rsi','RSI'],['stoch','Stoch RSI'],['macd','MACD']].map(x=>`<button data-indicator="${x[0]}" class="${state.indicators[x[0]]?'active':''}">${x[1]}</button>`).join('')}
    </div>
    <div id="tvChart" class="chartbox"></div>
    ${detailStats(r)}
    ${indicatorDashboard(r)}
    <div class="panelSub"><div class="subTitle"><b>Multi-Timeframe Konsensüs</b><span>15dk · 1sa · 4sa · 1g · 1h</span></div><div id="mtfGrid" class="mtfGrid"><div class="pending">Zaman dilimleri hesaplanıyor…</div></div></div>
    <div class="panelSub"><div class="subTitle"><b>Pattern & Structure Engine</b><span>divergence · cross · squeeze · Supertrend · Ichimoku · S/R</span></div><div id="structurePanel" class="structurePanel"><div class="pending">Yapı analizi yükleniyor…</div></div></div>
    <div class="grid2">
      <div class="recommendBox"><h3>Kısa Vade Modeli · ${r.short_score??'—'}/100</h3><div class="chips">${(r.reasons_short||['Tarama verisi bekleniyor']).map(x=>`<span class="chip">${x}</span>`).join('')}</div>${r.target_short?`<p>ATR bölgesi: hedef <b class="up">₺${fmt(r.target_short)}</b> · risk stop <b class="down">₺${fmt(r.stop_short)}</b></p>`:''}</div>
      <div class="recommendBox"><h3>Uzun Vade Modeli · ${r.long_score??'—'}/100</h3><div class="chips">${(r.reasons_long||['Tarama verisi bekleniyor']).map(x=>`<span class="chip">${x}</span>`).join('')}</div><p class="muted">Trend, relative strength, momentum ve risk birlikte değerlendirilir; tek bir indikatör karar vermez.</p></div>
    </div>
  </div>`;
}
function detailStats(r){
  const a=[['Kısa skor',r.short_score],['Uzun skor',r.long_score],['Alpha',r.alpha_score],['20G momentum',r.momentum_20!=null?pct(r.momentum_20):'—'],['3A momentum',r.momentum_60!=null?pct(r.momentum_60):'—'],['Volatilite',r.volatility!=null?`${r.volatility}%`:'—'],['Risk',r.risk!=null?`${r.risk}/100`:'—'],['Hacim',r.volume_ratio!=null?`${r.volume_ratio}x`:'—']];return `<div class="stats">${a.map(x=>`<div class="stat"><span>${x[0]}</span><b>${x[1]??'—'}</b></div>`).join('')}</div>`;
}
async function ensureTickerScan(t){
  if(state.scan.has(t))return;
  try{const r=await getJSON(`/api/scan?codes=${encodeURIComponent(t)}`);(r.rows||[]).forEach(x=>state.scan.set(x.ticker,x));}catch(e){}
}
function structureHtml(s){
  if(!s)return '<div class="pending">Yapı verisi yok</div>';
  const div=s.divergence||{}, cr=s.cross||{}, sq=s.squeeze||{};
  const cards=[
    ['Supertrend',s.supertrend||'—',s.supertrend==='BULLISH'?'up':s.supertrend==='BEARISH'?'down':''],
    ['Ichimoku',s.ichimoku||'—',s.ichimoku==='BULLISH'?'up':s.ichimoku==='BEARISH'?'down':''],
    ['EMA Cross',(cr.recent_event&&cr.recent_event!=='NONE')?cr.recent_event:(cr.state||'—'),cr.state==='GOLDEN'?'up':'down'],
    ['Bollinger Squeeze',sq.active?'AKTİF':'Pasif',sq.active?'amber':''],
    ['RSI Divergence',div.rsi||'NONE',div.rsi==='BULLISH'?'up':div.rsi==='BEARISH'?'down':''],
    ['MACD Divergence',div.macd||'NONE',div.macd==='BULLISH'?'up':div.macd==='BEARISH'?'down':'']
  ];
  const sup=(s.supports||[]).map(function(x){return '<span class="level support">S ₺'+fmt(x)+'</span>';}).join('');
  const res=(s.resistances||[]).map(function(x){return '<span class="level resistance">R ₺'+fmt(x)+'</span>';}).join('');
  return '<div class="structureCards">'+cards.map(function(x){return '<div class="structureCard"><span>'+x[0]+'</span><b class="'+x[2]+'">'+x[1]+'</b></div>';}).join('')+'</div><div class="levelsRow">'+sup+(res||'<span class="pending">Direnç seviyesi bulunamadı</span>')+'</div>';
}
function mtfHtml(d){
  if(!d||!d.frames)return '<div class="pending">Zaman dilimi verisi yok</div>';
  const tone=d.consensus==='BULLISH'?'up':d.consensus==='BEARISH'?'down':'amber';
  let out='<div class="mtfConsensus">Konsensüs <b class="'+tone+'">'+d.consensus+'</b></div>';
  out+=d.frames.map(function(x){
    if(x.status!=='OK')return '<div class="mtfCard muted"><span>'+x.timeframe+'</span><b>—</b><small>'+x.status+'</small></div>';
    const t=x.supertrend==='BULLISH'?'up':x.supertrend==='BEARISH'?'down':'';
    return '<div class="mtfCard"><span>'+x.timeframe+'</span><b>'+x.score+'/100</b><small class="'+t+'">'+x.trend+' · '+x.supertrend+'</small><em>RSI '+x.rsi+' · ADX '+x.adx+'</em></div>';
  }).join('');
  return out;
}
async function loadMtf(){
  const box=$('#mtfGrid'); if(!box)return;
  try{const d=await getJSON('/api/mtf/'+state.current); if($('#mtfGrid'))$('#mtfGrid').innerHTML=mtfHtml(d);}
  catch(e){if($('#mtfGrid'))$('#mtfGrid').innerHTML='<div class="pending">MTF yüklenemedi: '+e.message+'</div>';}
}
function addGuide(series,price,color,title){
  try{series.createPriceLine({price,color,lineWidth:1,lineStyle:2,axisLabelVisible:true,title});}catch(e){}
}
async function loadChart(){
  await ensureTickerScan(state.current);
  if(state.view!=='detail')return;
  const el=$('#tvChart'); if(!el)return;
  try{
    const d=await getJSON(`/api/chart/${state.current}?period=${state.chartPeriod}&interval=${state.chartInterval}`);
    if(!d.candles?.length){el.innerHTML='<div class="empty">Grafik verisi bulunamadı</div>';return;}
    if(state.chart){try{state.chart.remove()}catch(e){} state.chart=null;}
    const chart=LightweightCharts.createChart(el,{
      autoSize:true,
      layout:{background:{type:'solid',color:'#07121a'},textColor:'#8198a9',panes:{separatorColor:'#173040',separatorHoverColor:'#28516a',enableResize:true}},
      grid:{vertLines:{color:'#102431'},horzLines:{color:'#102431'}},
      rightPriceScale:{borderColor:'#1a3344'},
      timeScale:{borderColor:'#1a3344',timeVisible:state.chartInterval!=='1d'&&state.chartInterval!=='1wk'}
    });
    state.chart=chart;

    const candle=chart.addSeries(LightweightCharts.CandlestickSeries,{upColor:'#28d17c',downColor:'#ff5e72',borderVisible:false,wickUpColor:'#28d17c',wickDownColor:'#ff5e72'},0);
    candle.setData(d.candles);
    const vol=chart.addSeries(LightweightCharts.HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:''},0);
    vol.priceScale().applyOptions({scaleMargins:{top:.83,bottom:0}});
    vol.setData(d.candles.map(x=>({time:x.time,value:x.volume,color:x.close>=x.open?'rgba(40,209,124,.26)':'rgba(255,94,114,.26)'})));

    if(state.indicators.ema){
      const e20=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#49d7ff',priceLineVisible:false,lastValueVisible:false,title:'EMA20'},0); e20.setData(d.ema20||[]);
      const e50=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#f6b94a',priceLineVisible:false,lastValueVisible:false,title:'EMA50'},0); e50.setData(d.ema50||[]);
      const e200=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#a77cff',priceLineVisible:false,lastValueVisible:false,title:'EMA200'},0); e200.setData(d.ema200||[]);
    }
    if(state.indicators.bb){
      const bu=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'rgba(95,150,255,.55)',priceLineVisible:false,lastValueVisible:false,title:'BB+'},0);bu.setData(d.bb_upper||[]);
      const bm=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'rgba(120,145,165,.55)',priceLineVisible:false,lastValueVisible:false,title:'BB20'},0);bm.setData(d.bb_mid||[]);
      const bl=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'rgba(95,150,255,.55)',priceLineVisible:false,lastValueVisible:false,title:'BB-'},0);bl.setData(d.bb_lower||[]);
    }

    if(state.indicators.supertrend){
      const su=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:2,color:'#28d17c',priceLineVisible:false,lastValueVisible:false,title:'Supertrend +'},0);su.setData(d.supertrend_up||[]);
      const sd=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:2,color:'#ff5e72',priceLineVisible:false,lastValueVisible:false,title:'Supertrend -'},0);sd.setData(d.supertrend_down||[]);
    }
    if(state.indicators.ichimoku){
      const ten=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#49d7ff',priceLineVisible:false,lastValueVisible:false,title:'Tenkan'},0);ten.setData(d.tenkan||[]);
      const kij=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#f6b94a',priceLineVisible:false,lastValueVisible:false,title:'Kijun'},0);kij.setData(d.kijun||[]);
      const ia=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'rgba(40,209,124,.55)',priceLineVisible:false,lastValueVisible:false,title:'Cloud A'},0);ia.setData(d.ichimoku_a||[]);
      const ib=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'rgba(255,94,114,.55)',priceLineVisible:false,lastValueVisible:false,title:'Cloud B'},0);ib.setData(d.ichimoku_b||[]);
    }
    if(state.indicators.levels && d.structure){
      (d.structure.supports||[]).forEach(function(x,i){addGuide(candle,x,'rgba(40,209,124,.5)','S'+(i+1));});
      (d.structure.resistances||[]).forEach(function(x,i){addGuide(candle,x,'rgba(255,94,114,.5)','R'+(i+1));});
    }
    const sp=$('#structurePanel'); if(sp)sp.innerHTML=structureHtml(d.structure);
    let pane=1;
    if(state.indicators.rsi||state.indicators.stoch){
      let guide=null;
      if(state.indicators.rsi){
        const rs=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:2,color:'#49d7ff',priceLineVisible:false,title:'RSI'},pane);rs.setData(d.rsi||[]);guide=rs;
      }
      if(state.indicators.stoch){
        const sk=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#f6b94a',priceLineVisible:false,title:'Stoch K'},pane);sk.setData(d.stoch_k||[]);
        const sd=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#a77cff',priceLineVisible:false,title:'Stoch D'},pane);sd.setData(d.stoch_d||[]);
        if(!guide)guide=sk;
      }
      if(guide){guide.priceScale().applyOptions({autoScale:false,scaleMargins:{top:.08,bottom:.08}});addGuide(guide,70,'rgba(255,185,74,.5)','70');addGuide(guide,30,'rgba(255,94,114,.45)','30');}
      pane++;
    }

    if(state.indicators.macd){
      const mh=chart.addSeries(LightweightCharts.HistogramSeries,{priceLineVisible:false,title:'MACD Hist'},pane);
      mh.setData((d.macd_hist||[]).map(x=>({time:x.time,value:x.value,color:x.value>=0?'rgba(40,209,124,.55)':'rgba(255,94,114,.55)'})));
      const ml=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#49d7ff',priceLineVisible:false,title:'MACD'},pane);ml.setData(d.macd||[]);
      const ms=chart.addSeries(LightweightCharts.LineSeries,{lineWidth:1,color:'#f6b94a',priceLineVisible:false,title:'Signal'},pane);ms.setData(d.macd_signal||[]);
    }

    try{
      const panes=chart.panes();
      if(panes[0])panes[0].setHeight(390);
      for(let i=1;i<panes.length;i++)panes[i].setHeight(145);
    }catch(e){}
    chart.timeScale().fitContent();
  }catch(e){
    el.innerHTML=`<div class="empty">Grafik yüklenemedi: ${e.message}</div>`;
  }
}
function bindChartTools(){
  $$('.chartTools button').forEach(b=>b.onclick=()=>{
    if(b.dataset.period){state.chartPeriod=b.dataset.period;$$('[data-period]').forEach(x=>x.classList.toggle('active',x.dataset.period===state.chartPeriod))}
    if(b.dataset.interval){state.chartInterval=b.dataset.interval;$$('[data-interval]').forEach(x=>x.classList.toggle('active',x.dataset.interval===state.chartInterval))}
    loadChart();
  });
  $$('.indicatorToolbar button').forEach(b=>b.onclick=()=>{
    const k=b.dataset.indicator; state.indicators[k]=!state.indicators[k]; b.classList.toggle('active',state.indicators[k]); loadChart();
  });
}
async function backtestView(){return `<div class="panel"><div class="panelHead"><div><h2>Backtest Lab · ${state.current}</h2><p>MA20/MA50 trend stratejisi · gerçek tarihsel fiyat serisi</p></div><button class="toolbtn" id="runBacktest">Çalıştır</button></div><div id="btResult" class="empty">Backtest çalıştırılmayı bekliyor.</div></div>`}
async function runBacktest(){const box=$('#btResult');if(!box)return;box.innerHTML='<div class="loading">Backtest hesaplanıyor…</div>';try{const b=await getJSON(`/api/backtest/${state.current}?fast=20&slow=50&period=2y`);if(b.error)throw new Error(b.error);box.innerHTML=`<div class="btgrid">${[['Strateji',pct(b.return_pct)],['Buy & Hold',pct(b.buy_hold_pct)],['Alpha',pct(b.alpha_pct)],['Sharpe',b.sharpe],['Max DD',pct(b.max_drawdown)],['İşlem',b.trades]].map(x=>`<div class="stat"><span>${x[0]}</span><b>${x[1]}</b></div>`).join('')}</div><p class="muted">Geçmiş performans gelecekteki sonucu garanti etmez. İşlem maliyeti/slippage katmanı sonraki motor sürümünde parametreleştirilecek.</p>`;}catch(e){box.innerHTML=`<div class="empty">Backtest hatası: ${e.message}</div>`}}
function kapView(){return `<div class="kapcard"><h2>KAP Radar</h2><p>Şirket evreni KAP'ın BIST şirketleri listesinden dinamik alınıyor. Bildirim NLP katmanı ayrı servis olarak hazırlanıyor.</p><p><b>Neden şimdilik sahte akış yok?</b> Resmî gerçek zamanlı KAP veri yayını lisans/abonelik gerektirebildiği için, terminal gerçek veri bağlantısı kurulmadan yapay “canlı bildirim” göstermiyor.</p><a href="https://www.kap.org.tr/tr/bildirim-sorgu" target="_blank" rel="noopener">KAP bildirim sorgu ↗</a></div>`}
function render(){
  if(state.view==='overview'){els.title.textContent='Piyasa Komuta Merkezi';els.content.innerHTML=overview();}
  if(state.view==='all'){els.title.textContent='Tüm BIST Şirketleri';els.content.innerHTML=allStocks();bindTable();}
  if(state.view==='short'){els.title.textContent='Kısa Vade Alpha Radar';els.content.innerHTML=horizonView('short');}
  if(state.view==='long'){els.title.textContent='Uzun Vade Alpha Radar';els.content.innerHTML=horizonView('long');}
  if(state.view==='setups'){els.title.textContent='Setup Radar';els.content.innerHTML=setupView();}
  if(state.view==='anomaly'){els.title.textContent='Anomali Radar';els.content.innerHTML=anomalyView();}
  if(state.view==='portfolio'){els.title.textContent='Model Portföy';els.content.innerHTML=portfolioView();}
  if(state.view==='detail'){els.title.textContent=`${state.current} Hisse Analizi`;els.content.innerHTML=detailShell();bindChartTools();setTimeout(function(){loadChart();loadMtf();},0);}
  if(state.view==='backtest'){els.title.textContent='Backtest Lab';backtestView().then(h=>{els.content.innerHTML=h;$('#runBacktest').onclick=runBacktest});}
  if(state.view==='kap'){els.title.textContent='KAP Radar';els.content.innerHTML=kapView();}
}
function bindTable(){const s=$('#tableSearch'),sort=$('#tableSort'); if(s)s.oninput=e=>{els.search.value=e.target.value;render()};if(sort)sort.onchange=e=>{const q=(els.search.value||'').trim().toUpperCase();const rows=state.universe.filter(x=>!q||x.ticker.includes(q)||(x.name||'').toUpperCase().includes(q));$('#allBody').innerHTML=stockRows(rows,e.target.value)}}
$$('.nav').forEach(b=>b.onclick=()=>{$$('.nav').forEach(x=>x.classList.remove('active'));b.classList.add('active');state.view=b.dataset.view;render()});
els.scanBtn.onclick=()=>scanAll(true);
els.search.oninput=e=>{if(state.view==='all'){render();return;}const q=e.target.value.trim().toUpperCase();if(q.length>=2){const m=state.universe.find(x=>x.ticker===q)||state.universe.find(x=>x.ticker.startsWith(q));if(m)openStock(m.ticker)}};
window.openStock=openStock; init();
