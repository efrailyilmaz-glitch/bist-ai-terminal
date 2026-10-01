const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function app(href='https://terminal.example/?view=all&ticker=ASELS'){
 const tabs=[],listeners={},buttons={},nav=['overview','all','detail','forecast','cycles'].map(view=>({dataset:{view},classList:{toggle(){}}}));
 const loc=new URL(href),entries=[];let index=-1;
 const history={get state(){return entries[index]?.state},replaceState(state,_,url){entries[index<0?++index:index]={state,url:String(url)};loc.href=String(url)},pushState(state,_,url){entries.splice(index+1);entries.push({state,url:String(url)});index++;loc.href=String(url)},back(){index--;loc.href=entries[index].url;listeners.popstate()}};
 const c={URL,URLSearchParams,location:loc,history,state:{view:'overview',current:'ASELS',chartPeriod:'1y',chartInterval:'1d',universe:[{ticker:'THYAO'}]},els:{search:{value:''},title:{},content:{}},render(){},openStock(){},$:()=>null,$$:s=>s==='.nav'?nav:[],document:{createElement:()=>({}),querySelector:()=>({prepend:b=>buttons[b.id]=b})},window:{addEventListener:(n,f)=>listeners[n]=f,open:(...args)=>tabs.push(args)}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('app/static/v19.js','utf8'),c);return {c,tabs,buttons};
}
const {c,tabs,buttons}=app();
c.openStock('THYAO');assert.equal(c.state.view,'all');assert.equal(c.state.current,'ASELS');assert.equal(tabs.length,1);const opened=new URL(tabs[0][0]);assert.equal(opened.searchParams.get('ticker'),'THYAO');assert.equal(opened.searchParams.get('view'),'detail');assert.equal(tabs[0][2],'noopener');
c.els.search.value='THY';c.els.search.oninput();assert.equal(tabs.length,1,'typing must not open tabs');c.els.search.onkeydown({key:'Enter'});assert.equal(tabs.length,2);
c.state.view='cycles';c.render();buttons.backButton.onclick();assert.equal(c.state.view,'all');
const deep=app(opened.href);assert.equal(deep.c.state.current,'THYAO');assert.equal(deep.c.state.view,'detail');deep.buttons.backButton.onclick();assert.equal(deep.c.state.view,'all');
c.openStock('bad<script>');assert.equal(tabs.length,2);
console.log('new tabs, deep links, browser back, source return and Enter-only search passed');
