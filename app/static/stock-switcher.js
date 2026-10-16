// Same-tab chart symbol changes. Chart preferences stay in the existing state object.
function stockSearchKey(value){return String(value??'').trim().toLocaleUpperCase('tr-TR').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ');}
function stockResolve(value,universe){
 const raw=String(value??'').trim(),key=stockSearchKey(raw),code=stockSearchKey(raw.replace(/\.IS$/i,''));
 if(!key)return {error:'Hisse kodu veya şirket adı yazın.'};
 const exact=universe.find(r=>stockSearchKey(r.ticker)===code);if(exact)return {ticker:exact.ticker};
 const exactName=universe.filter(r=>stockSearchKey(r.name)===key);
 if(exactName.length===1)return {ticker:exactName[0].ticker};
 const matches=universe.filter(r=>stockSearchKey(r.ticker).startsWith(key)||stockSearchKey(r.name).includes(key));
 if(matches.length===1)return {ticker:matches[0].ticker};
 return {error:matches.length?'Birden fazla eşleşme var: '+matches.slice(0,6).map(r=>r.ticker).join(', ')+'. Listeden bir hisse kodu seçin.':'Eşleşen hisse bulunamadı. Kodu veya şirket adını kontrol edin.'};
}
function stockTranslateRange(view,count){
 if(!view?.range||!Number.isFinite(count)||count<2)return null;
 const {from,to}=view.range,span=to-from;
 if(!Number.isFinite(from)||!Number.isFinite(to)||span<=0||!Number.isFinite(view.count))return null;
 const width=Math.min(span,count-1),gap=view.count-1-to;
 const end=Math.max(width,Math.min(count-1+Math.max(0,-gap),count-1-gap));
 return {from:end-width,to:end};
}
let stockChartContext=null,stockPendingView=null;
function stockCaptureView(){
 try{
  if(!state.chart||stockChartContext?.chart!==state.chart||stockChartContext.ticker!==state.current)return stockPendingView;
  const chart=state.chart,range=chart.timeScale().getVisibleLogicalRange(),panes=chart.panes().map(p=>p.getHeight());
  const price=chart.priceScale('right').options();
  return {range,count:stockChartContext.count,panes,price:{mode:price.mode,invertScale:price.invertScale},period:state.chartPeriod,interval:state.chartInterval};
 }catch(e){return stockPendingView;}
}
function stockSwitchChart(ticker){
 if(state.view!=='detail'||!state.universe.some(r=>r.ticker===ticker))return false;
 if(ticker===state.current)return false;
 const view=stockCaptureView();stockPendingView=view?{...view,ticker}:null;
 // Invalidate old responses and cancel pending simulation work before changing symbols.
 if(typeof chartRequestId!=='undefined')chartRequestId++;
 if(typeof disposeChartWorkspace==='function')disposeChartWorkspace();
 state.current=ticker;render();return true;
}
function stockChartReady(chart,candles,ticker){
 stockChartContext={chart,ticker,count:candles.length};
 const saved=stockPendingView;
 if(!saved||saved.ticker!==ticker)return;
 stockPendingView=null;
 if(saved.period!==state.chartPeriod||saved.interval!==state.chartInterval)return;
 try{
  const panes=chart.panes();if(panes.length===saved.panes.length)saved.panes.forEach((h,i)=>{if(Number.isFinite(h)&&h>0)panes[i].setStretchFactor(h);});
  chart.priceScale('right').applyOptions(saved.price);
  const range=stockTranslateRange(saved,candles.length);if(range)chart.timeScale().setVisibleLogicalRange(range);
 }catch(e){/* A shorter/unsupported series still opens with its normal chart defaults. */}
}
function stockSwitcherHTML(){return `<form id="stockSwitcher" class="stockSwitcher"><label for="stockSwitcherQuery">Grafikte hisse değiştir</label><div class="stockSwitcherControls"><input id="stockSwitcherQuery" list="stockSwitcherOptions" maxlength="100" autocomplete="off" spellcheck="false" placeholder="Hisse kodu veya şirket adı — ör. THYAO" value="${v19Esc(state.current)}"><button type="submit">Aynı grafikte aç</button></div><datalist id="stockSwitcherOptions">${state.universe.map(r=>`<option value="${v19Esc(r.ticker)}" label="${v19Esc(r.name||r.ticker)}"></option>`).join('')}</datalist><small>Dönem, bar aralığı, göstergeler ve grafik yakınlaştırması korunur. Enter ile geçin.</small><p id="stockSwitcherStatus" role="status" aria-live="polite"></p></form>`;}
function stockSwitcherBind(){const form=$('#stockSwitcher'),input=$('#stockSwitcherQuery');if(!form||!input)return;input.onfocus=()=>input.select();form.onsubmit=e=>{e.preventDefault();const result=stockResolve(input.value,state.universe),status=$('#stockSwitcherStatus');if(result.error){status.textContent=result.error;return;}if(!stockSwitchChart(result.ticker))status.textContent='Bu hisse zaten grafikte açık.';};}
const stockDetailBase=detailShell;detailShell=function(...args){return stockDetailBase(...args).replace('<div class="chartTop">',stockSwitcherHTML()+'<div class="chartTop">');};
const stockRenderBase=render;render=function(...args){stockRenderBase(...args);if(state.view==='detail')stockSwitcherBind();};
