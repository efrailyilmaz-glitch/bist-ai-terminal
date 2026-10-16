/* Local notification journal. Percent thresholds are descriptive, not trade advice. */
(function(root){
'use strict';
const sources={opportunity:'Fırsatlar',background:'Sistem uyarıları',pro:'Özel alarmlar',technical:'Teknik sinyaller',model:'Model Portföy',paper:'Sanal Portföy',legacy:'Execution simülasyonu',orders:'Sanal işlemler'};
const defaults={daily:5,volume:3,position:10};
const finite=x=>typeof x==='number'&&Number.isFinite(x);
function fresh(){return {version:1,items:[],seen:{},settings:{...defaults}};}
function settings(s){return {daily:finite(s?.daily)&&s.daily>=1&&s.daily<=30?s.daily:5,volume:finite(s?.volume)&&s.volume>=1.5&&s.volume<=20?s.volume:3,position:finite(s?.position)&&s.position>=1&&s.position<=100?s.position:10};}
function ingest(state,events,now=Date.now()){
 const out={...state,settings:settings(state.settings),items:[...(state.items||[])],seen:{...state.seen}};
 for(const e of events){if(!e||!e.id||!sources[e.source]||typeof e.title!=='string'||!finite(e.time))continue;if(Object.hasOwn(out.seen,e.id))continue;out.seen[e.id]=now;out.items.push({...e,read:false});}
 out.items.sort((a,b)=>b.time-a.time||a.id.localeCompare(b.id));out.items=out.items.slice(0,1000);
 // Keep a longer receipt journal so retained server history cannot reappear after UI pruning.
 const keep=Object.entries(out.seen).sort((a,b)=>b[1]-a[1]).slice(0,20000);out.seen=Object.fromEntries(keep);return out;
}
function normalise(source,r,now=Date.now()){
 if(!r||!r.id)return null;const code=/^[A-Z0-9]{2,12}$/.test(r.ticker||'')?r.ticker:null;
 const epoch=Number(r.id),time=epoch>1e12&&epoch<=now+60000?epoch:now;
 return {id:JSON.stringify([source,String(r.id),code,r.rule_id||r.type||'']),source,ticker:code,time,sourceTime:String(r.created_at||r.at||''),title:(r.name||r.type||r.label||r.grade||sources[source])+(code?' · '+code:''),body:r.message||((r.score!=null?'Skor '+r.score+' · ':'')+(r.quantity!=null?String(r.side)+' '+r.quantity+' lot · ₺'+r.price:Object.entries(r.values||{}).map(([k,v])=>k+': '+v).join(' · ')))};
}
function currentQuote(q,now){if(!q||!finite(q.price)||q.price<=0||!/^\d{4}-\d{2}-\d{2}$/.test(q.as_of||''))return false;const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Istanbul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(now));if(q.as_of>today)return false;const age=now-Date.parse(q.as_of+'T00:00:00Z');return finite(age)&&age>=-10800000&&age<=7*86400000;}
function movements(holdings,quotes,config,now=Date.now()){
 const s=settings(config),out=[];
 for(const h of holdings){const q=quotes[h.ticker];if(!sources[h.source]||!currentQuote(q,now))continue;
  const add=(kind,value,step,label)=>{if(!finite(value)||Math.abs(value)<step)return;const bucket=Math.floor(Math.abs(value)/step),sign=value>=0?1:-1;out.push({id:JSON.stringify([h.source,h.ticker,q.as_of,kind,sign,bucket,kind==='position'?h.cycle||'':'']),source:h.source,ticker:h.ticker,time:now,sourceTime:q.as_of,title:h.ticker+' · '+label,body:(value>=0?'+':'')+value.toFixed(2)+(kind==='volume'?'×':'%')+' · '+sources[h.source]+' · veri tarihi '+q.as_of+' · gecikmeli referans'});};
  add('daily',q.change,s.daily,'Büyük günlük fiyat hareketi');
  if(finite(q.volume_ratio)&&q.volume_ratio>=s.volume)add('volume',q.volume_ratio,s.volume,'Yüksek göreli hacim');
  if((!h.afterDate||q.as_of>=h.afterDate)&&finite(h.quantity)&&h.quantity!==0&&finite(h.avg)&&h.avg>0){const cost=Math.abs(h.quantity)*h.avg+(h.entryFees||0),pnl=(q.price-h.avg)*h.quantity-(h.entryFees||0);add('position',pnl/cost*100,s.position,'Pozisyon maliyetine göre büyük değişim');}
 }
 return out;
}
const api={sources,defaults,fresh,settings,ingest,normalise,movements,currentQuote};if(typeof module!=='undefined')module.exports=api;else root.BistNotifications=api;
})(typeof globalThis!=='undefined'?globalThis:this);
