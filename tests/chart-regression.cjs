const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync('app/static/app.js', 'utf8');
const code = source.slice(source.indexOf('let chartRequestId=0;'), source.indexOf('function bindChartTools()'));
function setup() {
  const host = {innerHTML:''};
  const charts=[];
  const context={
    state:{current:'ASELS',view:'detail',chartPeriod:'1y',chartInterval:'1d',indicators:{rsi:true,stoch:true,macd:true}},
    ensureTickerScan:async()=>{},refreshDetailMetrics:()=>{},addGuide:()=>{},structureHtml:()=>'',
    $:s=>s==='#tvChart'?host:null,
    getJSON:async()=>({candles:[{time:'2026-01-01',open:1,high:2,low:1,close:2}]}),
    LightweightCharts:{createChart:()=>{
      const panes=[];
      const chart={addSeries:(_,options,index)=>{
        panes[index]??={setStretchFactor:v=>panes[index].factor=v};
        return {setData:()=>{},priceScale:()=>({applyOptions:()=>{}})};
      },panes:()=>panes,timeScale:()=>({fitContent:()=>{}}),remove:()=>{}};
      charts.push(chart);return chart;
    }}
  };
  vm.createContext(context);vm.runInContext(code,context);
  return {context,charts,host};
}
(async()=>{
  for(const indicators of [{rsi:true,stoch:true,macd:true},{rsi:false,stoch:true,macd:true},{rsi:true,stoch:false,macd:true}]){
    const {context,charts}=setup();context.state.indicators=indicators;
    await context.loadChart();
    assert.deepEqual(charts[0].panes().map(p=>p.factor),[390,175,175]);
  }
  const {context,charts}=setup();let resolveOld;
  context.getJSON=url=>url.includes('ASELS')?new Promise(r=>resolveOld=r):Promise.resolve({candles:[{time:'2026-01-01',open:1,high:2,low:1,close:2}]});
  const old=context.loadChart();await new Promise(setImmediate);
  context.state.current='THYAO';await context.loadChart();
  resolveOld({candles:[{time:'2026-01-01',open:1,high:2,low:1,close:2}]});await old;
  assert.equal(charts.length,1,'late response must not replace the selected stock chart');
  console.log('equal pane factors, indicator toggles and out-of-order chart responses passed');
})().catch(e=>{console.error(e);process.exit(1)});
