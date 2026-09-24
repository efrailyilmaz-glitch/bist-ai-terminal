const compact4=n=>n==null?'—':new Intl.NumberFormat('tr-TR',{notation:'compact',maximumFractionDigits:1}).format(n);
const val4=(x,d=2)=>x==null?'—':fmt(x,d);

function saveWatchlist(){localStorage.setItem('bist-ai-watchlist',JSON.stringify([...state.watchlist]));}
function toggleWatchlist(t){
  if(state.watchlist.has(t))state.watchlist.delete(t);else state.watchlist.add(t);
  saveWatchlist();render();
}
window.toggleWatchlist=toggleWatchlist;

function watchlistView(){
  const rows=[...state.watchlist].map(t=>state.meta.get(t)||{ticker:t,name:t});
  return '<div class="panel"><div class="panelHead"><div><h2>Watchlist</h2><p>Tarayıcıda yerel olarak saklanır; hesap verisi değildir.</p></div><span class="pill">'+rows.length+' HİSSE</span></div>'+
    (rows.length?'<div class="tableWrap"><table class="stockTable"><thead><tr><th>Kod</th><th>Şirket</th><th>Kısa</th><th>Uzun</th><th>Alpha</th><th>Değişim</th></tr></thead><tbody>'+
      rows.map(m=>{const r=state.scan.get(m.ticker)||{};return '<tr onclick="openStock(\''+m.ticker+'\')"><td><strong>'+m.ticker+'</strong></td><td>'+(m.name||'')+'</td><td>'+(r.short_score??'—')+'</td><td>'+(r.long_score??'—')+'</td><td>'+(r.alpha_score??'—')+'</td><td class="'+cls(r.change||0)+'">'+(r.change!=null?pct(r.change):'—')+'</td></tr>';}).join('')+
      '</tbody></table></div>':'<div class="empty">Watchlist boş. Hisse detayındaki ★ ile ekleyebilirsin.</div>')+'</div>';
}

function exportScanCsv(){
  const head=['ticker','name','price','change','short_score','long_score','alpha_score','rsi','macd_hist','adx','mfi','relative_strength_20','risk'];
  const lines=[head.join(',')];
  [...state.scan.values()].forEach(r=>{
    const m=state.meta.get(r.ticker)||{};
    const row={...r,name:m.name||r.name||''};
    lines.push(head.map(k=>'"'+String(row[k]??'').replaceAll('"','""')+'"').join(','));
  });
  const blob=new Blob([lines.join('\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='bist-ai-scan.csv';a.click();URL.revokeObjectURL(a.href);
}
window.exportScanCsv=exportScanCsv;

function factorTable(rows){
  return '<div class="tableWrap"><table class="stockTable"><thead><tr><th>Kod</th><th>Şirket</th><th>Sektör</th><th>Fund.</th><th>Value</th><th>Quality</th><th>Growth</th><th>Balance</th><th>F/K</th><th>PD/DD</th><th>ROE</th><th>Gelir Büy.</th><th>Sektör %ile</th><th>Kapsam</th></tr></thead><tbody>'+
    rows.map(r=>'<tr onclick="openStock(\''+r.ticker+'\')"><td><strong>'+r.ticker+'</strong></td><td>'+(r.name||'')+'</td><td>'+(r.sector||'—')+'</td><td><b>'+(r.fundamental_score??'—')+'</b></td><td>'+(r.value_score??'—')+'</td><td>'+(r.quality_score??'—')+'</td><td>'+(r.growth_score??'—')+'</td><td>'+(r.balance_score??'—')+'</td><td>'+val4(r.trailing_pe,1)+'</td><td>'+val4(r.price_to_book,1)+'</td><td>'+(r.roe_pct!=null?pct(r.roe_pct):'—')+'</td><td>'+(r.revenue_growth_pct!=null?pct(r.revenue_growth_pct):'—')+'</td><td>'+(r.sector_percentile??'—')+'</td><td>%'+(r.coverage_pct??0)+'</td></tr>').join('')+
    '</tbody></table></div>';
}

function sectorSummary(rows){
  const g={};
  rows.forEach(r=>{const s=r.sector||'Unknown';if(!g[s])g[s]=[];g[s].push(r);});
  const data=Object.entries(g).map(([sector,arr])=>{
    const avg=k=>{const v=arr.map(x=>x[k]).filter(x=>x!=null);return v.length?Math.round(v.reduce((a,b)=>a+b,0)/v.length):null;};
    return {sector,count:arr.length,fund:avg('fundamental_score'),value:avg('value_score'),quality:avg('quality_score'),growth:avg('growth_score')};
  }).sort((a,b)=>(b.fund||-1)-(a.fund||-1));
  return '<div class="sectorSummary"><h4>Sektör Faktör Özeti <span class="muted">(yalnız yüklenen örneklem)</span></h4><div class="tableWrap"><table class="stockTable"><thead><tr><th>Sektör</th><th>Şirket</th><th>Fund.</th><th>Value</th><th>Quality</th><th>Growth</th></tr></thead><tbody>'+data.map(x=>'<tr><td>'+x.sector+'</td><td>'+x.count+'</td><td>'+(x.fund??'—')+'</td><td>'+(x.value??'—')+'</td><td>'+(x.quality??'—')+'</td><td>'+(x.growth??'—')+'</td></tr>').join('')+'</tbody></table></div></div>';
}
function factorView(){
  return '<div class="panel"><div class="panelHead"><div><h2>Factor Lab</h2><p>Value · Quality · Growth · Balance Sheet · Shareholder Return</p></div><button class="toolbtn" id="runFactors">Top Adayları Zenginleştir</button></div>'+
    '<div class="factorNote">Temel veriler talep üzerine yüklenir. Sektör yüzdeliği yalnız yüklenen örneklem içindeki karşılaştırmadır; tüm piyasa konsensüsü değildir.</div>'+
    '<div id="factorResult">'+(state.factorRows.length?sectorSummary(state.factorRows)+factorTable(state.factorRows):'<div class="empty">Teknik tarama ilerledikçe en güçlü adayları temel verilerle zenginleştirebilirsin.</div>')+'</div></div>';
}

async function loadFactors(){
  const box=$('#factorResult');if(!box)return;
  let candidates=[...state.scan.values()].sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0)).slice(0,18).map(x=>x.ticker);
  if(!candidates.length)candidates=state.universe.slice(0,12).map(x=>x.ticker);
  box.innerHTML='<div class="loading">Temel veriler ve faktörler yükleniyor…</div>';
  try{
    const d=await getJSON('/api/factor-screen?codes='+encodeURIComponent(candidates.join(',')));
    state.factorRows=d.rows||[];box.innerHTML=sectorSummary(state.factorRows)+factorTable(state.factorRows);
  }catch(e){box.innerHTML='<div class="empty">Factor Lab hatası: '+e.message+'</div>';}
}

function factorScoreCards(f){
  const arr=[['Fundamental',f.fundamental_score],['Value',f.value_score],['Quality',f.quality_score],['Growth',f.growth_score],['Balance',f.balance_score],['Shareholder',f.shareholder_score]];
  return '<div class="factorCards">'+arr.map(x=>'<div class="factorCard"><span>'+x[0]+'</span><b>'+(x[1]??'—')+'</b></div>').join('')+'</div>';
}

function fundamentalHtml(f){
  if(!f||f.status==='NO_DATA')return '<div class="empty">Temel veri bulunamadı.</div>';
  const metrics=[
    ['Piyasa Değeri',compact4(f.market_cap)],['F/K',val4(f.trailing_pe,1)],['İleri F/K',val4(f.forward_pe,1)],['PD/DD',val4(f.price_to_book,1)],
    ['FD/FAVÖK',val4(f.ev_to_ebitda,1)],['F/S',val4(f.price_to_sales,1)],['ROE',f.roe_pct!=null?pct(f.roe_pct):'—'],['ROA',f.roa_pct!=null?pct(f.roa_pct):'—'],
    ['Faaliyet Marjı',f.operating_margin_pct!=null?pct(f.operating_margin_pct):'—'],['Net Marj',f.profit_margin_pct!=null?pct(f.profit_margin_pct):'—'],
    ['Gelir Büyümesi',f.revenue_growth_pct!=null?pct(f.revenue_growth_pct):'—'],['Kâr Büyümesi',f.earnings_growth_pct!=null?pct(f.earnings_growth_pct):'—'],
    ['Borç/Özsermaye',val4(f.debt_to_equity,2)],['Cari Oran',val4(f.current_ratio,2)],['FCF Yield',f.fcf_yield!=null?pct(f.fcf_yield):'—'],['Temettü Verimi',f.dividend_yield_pct!=null?pct(f.dividend_yield_pct):'—'],
    ['Net Borç',compact4(f.net_debt)],['TTM FCF',compact4(f.ttm_free_cash_flow)],['FCF/Kâr Dönüşüm',f.fcf_conversion_pct!=null?pct(f.fcf_conversion_pct):'—'],['OCF/Kâr Dönüşüm',f.cash_conversion_pct!=null?pct(f.cash_conversion_pct):'—'],
    ['Analist Hedef Ort.',f.target_mean_price!=null?'₺'+val4(f.target_mean_price,2):'—'],['Analist Sayısı',f.analyst_count??'—'],['Faktör Modeli',f.factor_model||'—'],['Beta',val4(f.beta,2)]
  ];
  const q=f.quarterly||[];
  return factorScoreCards(f)+
    '<div class="fundamentalMeta"><span>'+((f.sector||'Sektör N/A')+' / '+(f.industry||'Endüstri N/A'))+'</span><span>Veri kapsamı %'+(f.coverage_pct??0)+' · '+(f.source||'')+'</span></div>'+
    '<div class="fundMetrics">'+metrics.map(x=>'<div><span>'+x[0]+'</span><b>'+x[1]+'</b></div>').join('')+'</div>'+
    (q.length?'<div class="quarterly"><h4>Çeyreklik Finansal Özet</h4><div class="tableWrap"><table class="stockTable"><thead><tr><th>Dönem</th><th>Gelir</th><th>Net Kâr</th><th>Faaliyet Kârı</th><th>FCF</th><th>Borç</th></tr></thead><tbody>'+
      q.map(x=>'<tr><td>'+x.period+'</td><td>'+compact4(x.revenue)+'</td><td>'+compact4(x.net_income)+'</td><td>'+compact4(x.operating_income)+'</td><td>'+compact4(x.free_cash_flow)+'</td><td>'+compact4(x.total_debt)+'</td></tr>').join('')+
      '</tbody></table></div></div>':'');
}

function researchHtml(d){
  const comp=d.components||{},strengths=d.strengths||[],flags=d.flags||[];
  const comps=[['Teknik Kısa',comp.technical_short],['Teknik Uzun',comp.technical_long],['Fundamental',comp.fundamental],['KAP',comp.kap],['Haber',comp.news],['Makro',comp.macro],['Risk',comp.risk],['Anomali',comp.anomaly]];
  return '<div class="researchHero"><div><span>Kısa Vade Araştırma</span><b>'+d.short_research_score+'/100</b><small>'+d.short_stance+'</small></div><div><span>Uzun Vade Araştırma</span><b>'+d.long_research_score+'/100</b><small>'+d.long_stance+'</small></div><div><span>Güven / Veri Kapsamı</span><b>'+d.confidence+'/100</b><small>Eksik veri güveni düşürür</small></div></div>'+
    '<div class="componentGrid">'+comps.map(x=>'<div><span>'+x[0]+'</span><b>'+(x[1]??'—')+'</b></div>').join('')+'</div>'+
    '<div class="researchLists"><div><h4>Güçlü Taraflar</h4>'+(strengths.length?strengths.map(x=>'<span class="goodFlag">'+x+'</span>').join(''):'<span class="pending">Belirgin güçlü faktör yok</span>')+'</div><div><h4>Risk / Kırmızı Bayrak</h4>'+(flags.length?flags.map(x=>'<span class="badFlag">'+x+'</span>').join(''):'<span class="pending">Belirgin kırmızı bayrak yok</span>')+'</div></div>';
}

function kapNewsHtml(d){
  const p=d.kap_profile||{},k=d.kap||{},n=d.news||{};
  const cal=p.calendar||[],ki=k.items||[],ni=n.items||[];
  return '<div class="dataColumns"><div><h4>KAP Profil / Takvim</h4><p class="muted">'+((p.sectors||[]).join(' · ')||'Sektör N/A')+' · '+(p.market||'Pazar N/A')+'</p>'+
    (cal.length?cal.map(x=>'<div class="feedItem"><b>'+x.subject+'</b><span>'+x.period+' '+x.year+'</span><small>'+x.start+' → '+x.end+'</small></div>').join(''):'<div class="pending">Takvim verisi yok</div>')+
    '</div><div><h4>KAP Olay Akışı</h4>'+
    (ki.length?ki.map(x=>'<a class="feedItem" href="'+x.url+'" target="_blank" rel="noopener"><b>'+x.title+'</b><span class="'+cls(x.sentiment_score)+'">Etki '+x.sentiment_score+' · Önem '+x.materiality+'</span><small>'+x.event+'</small></a>').join(''):'<div class="pending">Eşleşen güncel KAP kaydı bulunamadı.</div>')+
    '</div><div><h4>Haber Başlık Duyarlılığı</h4><p class="muted">Başlık bazlı sinyal · ortalama '+(n.headline_sentiment??'—')+'</p>'+
    (ni.length?ni.slice(0,8).map(x=>'<a class="feedItem" href="'+x.url+'" target="_blank" rel="noopener"><b>'+x.title+'</b><span>'+x.source+'</span><small class="'+cls(x.sentiment_score)+'">Sentiment '+x.sentiment_score+'</small></a>').join(''):'<div class="pending">Haber verisi yok</div>')+
    '</div></div>';
}

async function loadResearch(){
  const ticker=state.current;
  let d=state.researchCache.get(ticker);
  try{
    if(!d){d=await getJSON('/api/research/'+ticker);state.researchCache.set(ticker,d);}
    const a=$('#researchPanel');if(a)a.innerHTML=researchHtml(d);
    const b=$('#fundamentalPanel');if(b)b.innerHTML=fundamentalHtml(d.fundamentals);
    const k=$('#kapNewsPanel');if(k)k.innerHTML=kapNewsHtml(d);
  }catch(e){
    ['researchPanel','fundamentalPanel','kapNewsPanel'].forEach(id=>{const x=$('#'+id);if(x)x.innerHTML='<div class="empty">Araştırma verisi yüklenemedi: '+e.message+'</div>';});
  }
}

function fundamentalView(){
  return '<div class="panel"><div class="panelHead"><div><h2>Temel Analiz · '+state.current+'</h2><p>Değerleme · kalite · büyüme · bilanço · nakit akışı</p></div><button class="toolbtn" onclick="openStock(\''+state.current+'\')">Teknik Grafiğe Git</button></div><div id="fundamentalPanel"><div class="loading">Temel veri yükleniyor…</div></div></div>';
}
function kapResearchView(){
  return '<div class="panel"><div class="panelHead"><div><h2>KAP & Haber · '+state.current+'</h2><p>KAP profil/takvim · olay sınıflandırma · haber başlık sinyali</p></div></div><div id="kapNewsPanel"><div class="loading">KAP ve haber verisi yükleniyor…</div></div></div>';
}

const _detailShellV4=detailShell;
detailShell=function(){
  let html=_detailShellV4();
  const cached=state.researchCache.has(state.current);
  const extra='<div class="panelSub"><div class="subTitle"><b>V5 Deep Research</b><span>teknik + temel + KAP + haber + makro</span></div><div id="researchPanel">'+(cached?'<div class="loading">Önbellekteki araştırma açılıyor…</div>':'<div class="lazyResearch"><p>Grafik ve teknik analiz öncelikli yüklendi. Temel/KAP/haber analizi isteğe bağlıdır.</p><button class="toolbtn" id="loadDeepResearch">Derin Araştırmayı Yükle</button></div>')+'</div></div>'+
    '<div class="panelSub"><div class="subTitle"><b>Temel Analiz</b><span>lazy-load · Yahoo fundamentals</span></div><div id="fundamentalPanel"><div class="pending">'+(cached?'Önbellek okunuyor…':'Derin araştırma yüklenince açılır.')+'</div></div></div>'+
    '<div class="panelSub"><div class="subTitle"><b>KAP & Haber</b><span>lazy-load · KAP + headline sentiment</span></div><div id="kapNewsPanel"><div class="pending">'+(cached?'Önbellek okunuyor…':'Derin araştırma yüklenince açılır.')+'</div></div></div>';
  html=html.replace('<div class="grid2">',extra+'<div class="grid2">');
  html=html.replace(/<h2>([^<]+)<\/h2>/,'<h2>$1 <button class="starBtn '+(state.watchlist.has(state.current)?'on':'')+'" onclick="toggleWatchlist(\''+state.current+'\')">★</button></h2>');
  return html;
};

kapView=kapResearchView;

const _renderV4=render;
render=function(){
  _renderV4();
  if(state.view==='factors'){
    els.title.textContent='Factor Lab';els.content.innerHTML=factorView();
    setTimeout(()=>{const b=$('#runFactors');if(b)b.onclick=loadFactors;},0);
  }
  if(state.view==='fundamental'){
    els.title.textContent='Temel Analiz';els.content.innerHTML=fundamentalView();setTimeout(loadResearch,0);
  }
  if(state.view==='watchlist'){
    els.title.textContent='Watchlist';els.content.innerHTML=watchlistView();
  }
  if(state.view==='detail')setTimeout(()=>{
    if(state.researchCache.has(state.current)){loadResearch();return;}
    const b=$('#loadDeepResearch');
    if(b)b.onclick=()=>{
      b.disabled=true;b.textContent='Yükleniyor…';
      loadResearch();
    };
  },0);
  if(state.view==='kap'){els.title.textContent='KAP & Haber';els.content.innerHTML=kapResearchView();setTimeout(loadResearch,0);}
  if(state.view==='all'){
    const head=$('.panelHead');
    if(head&&!$('#exportScanBtn')){const b=document.createElement('button');b.id='exportScanBtn';b.className='toolbtn';b.textContent='CSV Dışa Aktar';b.onclick=exportScanCsv;head.appendChild(b);}
  }
};

function portfolioRiskHtml(d){
  if(!d||d.status!=='OK')return '<div class="empty">Portföy risk verisi bulunamadı.</div>';
  const cards=[['Yıllık Getiri',pct(d.annual_return_pct)],['Yıllık Vol.',pct(d.annual_volatility_pct)],['Sharpe Proxy',d.sharpe_proxy],['Max Drawdown',pct(d.max_drawdown_pct)],['Ort. Korelasyon',d.avg_correlation],['Çeşitlendirme',d.diversification_score+'/100']];
  const risk='<div class="tableWrap"><table class="stockTable"><thead><tr><th>Kod</th><th>Ağırlık</th><th>Volatilite</th><th>XU100 Beta</th><th>Risk Katkısı</th></tr></thead><tbody>'+d.risk_rows.map(x=>'<tr onclick="openStock(\''+x.ticker+'\')"><td><strong>'+x.ticker+'</strong></td><td>%'+x.weight_pct+'</td><td>%'+x.volatility_pct+'</td><td>'+(x.beta_xu100??'—')+'</td><td>%'+x.risk_contribution_pct+'</td></tr>').join('')+'</tbody></table></div>';
  const names=d.tickers||[];
  const corr='<div class="corrWrap"><table class="corrTable"><thead><tr><th></th>'+names.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+d.correlation.map(row=>'<tr><th>'+row.ticker+'</th>'+names.map(x=>'<td class="'+((row[x]||0)>=.7?'corrHigh':(row[x]||0)<=.2?'corrLow':'')+'">'+val4(row[x],2)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
  return '<div class="btgrid">'+cards.map(x=>'<div class="stat"><span>'+x[0]+'</span><b>'+x[1]+'</b></div>').join('')+'</div><h4>Risk Katkısı</h4>'+risk+'<h4>Korelasyon Matrisi</h4>'+corr+'<p class="muted">'+d.note+'</p>';
}
async function loadPortfolioRisk(){
  const box=$('#portfolioRisk');if(!box)return;
  const codes=[...state.scan.values()].filter(x=>(x.alpha_score||0)>=55).sort((a,b)=>(b.alpha_score||0)-(a.alpha_score||0)).slice(0,8).map(x=>x.ticker);
  if(!codes.length){box.innerHTML='<div class="empty">Risk analizi için yeterli aday yok.</div>';return;}
  try{const d=await getJSON('/api/portfolio-risk?codes='+encodeURIComponent(codes.join(',')));box.innerHTML=portfolioRiskHtml(d);}
  catch(e){box.innerHTML='<div class="empty">Portföy risk analizi yüklenemedi: '+e.message+'</div>';}
}
const _portfolioViewV4=portfolioView;
portfolioView=function(){
  return _portfolioViewV4()+'<div class="panel portfolioRiskPanel"><div class="panelHead"><div><h2>Portföy Risk Laboratuvarı</h2><p>Korelasyon · beta · volatilite · drawdown · risk katkısı</p></div><span class="pill">EQUAL-WEIGHT PROXY</span></div><div id="portfolioRisk"><div class="loading">Risk analizi hesaplanıyor…</div></div></div>';
};
const _renderPortfolioV4=render;
render=function(){
  _renderPortfolioV4();
  if(state.view==='portfolio')setTimeout(loadPortfolioRisk,0);
};
