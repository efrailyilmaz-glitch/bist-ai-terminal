const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const rank=require('../app/static/ranking-engine.js'),now=Date.now();
function row(ticker,raw,risk=40){return {ticker,short_score:67,raw_short_score:raw,long_score:67,alpha_score:67,as_of:'2026-10-21',fetched_at:now/1000,signal_guard:{status:'WAIT',flags:[]},risk};}
const a=row('AHGAZ',75),b=row('ZZTEST',95),c=row('TEST',90);
assert.deepEqual(rank.rows([a,b,c],'short_score',now).map(r=>r.ticker),['ZZTEST','TEST','AHGAZ']);
assert.deepEqual(rank.rows([c,b,a],'short_score',now).map(r=>r.ticker),['ZZTEST','TEST','AHGAZ']);
assert.deepEqual(rank.position([b,c,a],a,'short_score'),{rank:1,ties:3});
assert.deepEqual(rank.rows([{...a,short_score:0}],'short_score',now).map(r=>r.short_score),[0]);
for(const invalid of [{...a,fetched_at:now/1000-1201},{...a,fetched_at:undefined},{...a,short_score:NaN},{...a,short_score:null},{...a,signal_guard:{status:'BLOCK'}},{...a,signal_guard:undefined}])assert.equal(rank.rows([invalid],'short_score',now).length,0);
// Execute the real scanner: unavailable refresh results must evict old leaders.
const src=fs.readFileSync('app/static/app.js','utf8');
const scan=src.slice(src.indexOf('async function scanAll('),src.indexOf('function rankedRows('));
async function check(fail){
 const state={universe:[{ticker:'AHGAZ'},{ticker:'TEST'}],scan:new Map([['AHGAZ',a]]),total:2,scanned:2,view:'detail',scanning:false};
 const ctx={state,els:{scanBtn:{},scanStatus:{}},getJSON:async()=>{if(fail)throw Error('timeout');return {requested:2,missing:['AHGAZ'],rows:[c]};},Date,localStorage:{removeItem(){}},renderTickerbar(){},render(){},updateRegime(){},persistScanCache(){}};
 vm.createContext(ctx);vm.runInContext(scan,ctx);await ctx.scanAll(false);assert(!state.scan.has('AHGAZ'));assert.equal(state.scan.size,fail?0:1);assert(!state.scanning);
}
(async()=>{await check(false);await check(true);const ctx={state:{scan:new Map()},RankingEngine:rank,getJSON:async()=>({rows:[a]}),encodeURIComponent};vm.createContext(ctx);vm.runInContext(src.slice(src.indexOf('async function ensureTickerScan('),src.indexOf('function refreshDetailMetrics(')),ctx);await ctx.ensureTickerScan('AHGAZ');assert(ctx.state.scan.has('AHGAZ'));console.log('ranking ties, insertion independence, stale rows, zero scores and failed refresh eviction passed');})();
