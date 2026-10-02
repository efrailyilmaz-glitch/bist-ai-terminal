const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const E=require('../app/static/paper-engine.js'),D=require('../app/static/chart-drawings.js');
let seq=0;
const order=(a,side,quantity,price,extra={})=>E.trade(a,{ticker:'TEST',side,quantity,price,id:String(++seq),...extra});
let a=E.fresh();a=order(a,'BUY',100,10);assert.equal(a.cash,998999);a=order(a,'SELL',100,12);assert.equal(a.cash,1000197.8);assert.equal(a.realized,197.8);assert(!a.positions.TEST);
a=E.fresh();a=order(a,'SHORT',100,10);assert.equal(a.cash,998999);assert.equal(a.positions.TEST.quantity,-100);a=order(a,'COVER',40,8);assert.equal(a.positions.TEST.quantity,-60);a=order(a,'COVER',60,12);assert.equal(a.cash,999957.96);assert.equal(a.realized,-42.04);assert(!a.positions.TEST);
a=order(E.fresh(),'SHORT',100,10);assert.throws(()=>order(a,'BUY',1,10));assert.throws(()=>order(a,'SELL',1,10));assert.throws(()=>order(a,'COVER',101,10));
for(const qty of [0,-1,1.5,NaN,Infinity])assert.throws(()=>order(E.fresh(),'BUY',qty,10));
for(const price of [0,-1,NaN,Infinity])assert.throws(()=>order(E.fresh(),'BUY',1,price));
assert.throws(()=>order(E.fresh(),'BUY',12001,10));assert.throws(()=>order({...E.fresh(),cash:1},'BUY',1,10));
a=order(E.fresh(),'BUY',1,10,{id:'same'});assert.throws(()=>order(a,'BUY',1,10,{id:'same'}));
assert.throws(()=>E.levels('100;1\n100;2'));assert.throws(()=>E.levels('100;1.5'));assert.throws(()=>E.levels(''));
let book=E.levels('102;20\n100;30\n101;50'),filled=0,cost=0;while(filled<65){const s=E.slice(book,65-filled,20,101);assert(!s.stop);book[s.index].quantity-=s.quantity;filled+=s.quantity;cost+=s.quantity*s.price;}assert.equal(filled,65);assert.equal(cost,6535);assert.equal(book[1].quantity,15);
assert.equal(E.slice([{price:102,quantity:1}],1,1,101).stop,'ÜST FİYAT SINIRINA ULAŞILDI');assert(E.slice([{price:100,quantity:0}],1,1,101).stop);
assert.equal(D.distance({x:5,y:3},{x:0,y:0},{x:10,y:0}),3);assert.deepEqual(D.channel({x:0,y:10},{x:10,y:20},{x:5,y:25}),[{x:0,y:20},{x:10,y:30}]);assert.equal(D.channel({x:0,y:0},{x:0,y:10},{x:5,y:5}),null);
// Native pane anchoring, ruler drawing and reversible storage.
const mem=new Map();global.localStorage={getItem:k=>mem.get(k),setItem:(k,v)=>mem.set(k,v)};global.crypto={randomUUID:()=>String(++seq)};global.document={addEventListener(){},removeEventListener(){}};
const hint={textContent:''},color={value:'#fff'},buttons={};const rail={closest:()=>({querySelector:()=>hint}),querySelector:s=>s==='[type=color]'?color:(buttons[s]??={}),querySelectorAll:()=>[]};let draw;const scale={timeToCoordinate:t=>Number(t)*10,coordinateToLogical:x=>x/10};const chart={timeScale:()=>scale,paneSize:()=>({width:100,height:100}),subscribeClick(){},subscribeCrosshairMove(){},unsubscribeClick(){},unsubscribeCrosshairMove(){},applyOptions(){}};const series={coordinateToPrice:y=>100-y,priceToCoordinate:p=>100-p,attachPrimitive:p=>{draw=p;p.attached({requestUpdate(){}})}};
const tool=new D.Drawings(chart,series,[0,1,2,3,4].map(time=>({time})),'TEST','1d',rail);
tool.setTool('line');tool.onClick({point:{x:10,y:10},paneIndex:1});assert.equal(tool.pending.length,0);tool.onClick({point:{x:10,y:10},paneIndex:0});tool.onClick({point:{x:30,y:30},paneIndex:0});assert.equal(tool.items.length,1);assert.equal(tool.items[0].points[0].price,90);tool.undo();assert.equal(tool.items.length,0);tool.redo();assert.equal(tool.items.length,1);assert(mem.get('bist-drawings-v1:TEST:1d'));
tool.setTool('parallel');for(const [x,y] of [[10,10],[30,30],[20,50]])tool.onClick({point:{x,y},paneIndex:0});assert.equal(tool.items.length,2);tool.detached();
// Controller cancellation must stop a queued lock callback before storage writes.
const source=fs.readFileSync('app/static/v21.js','utf8');let lockCallback,writes=0;
const context={v19Esc:s=>s,detailShell:()=>'',render(){},window:{addEventListener(){}},navigator:{locks:{request:(_,fn)=>{lockCallback=fn;return new Promise(()=>{});}}},document:{hidden:false},localStorage:{getItem:()=>null,setItem:()=>writes++},BistPaperEngine:E,crypto:global.crypto};vm.createContext(context);vm.runInContext(source+'\nthis.Q=QuickDesk;',context);const q=Object.create(context.Q.prototype);q.ticker='TEST';q.dead=false;q.run={id:'run'};q.commit({side:'BUY',quantity:1,price:10},'run');q.run=null;assert.throws(()=>lockCallback(),/iptal/);assert.equal(writes,0);
console.log('paper cash/short/fees, risk bounds, ladder caps/partial fills, chart anchors/undo and queued cancellation passed');
