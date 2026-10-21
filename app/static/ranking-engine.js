// Pure ranking policy shared by the overview and horizon lists.
const RankingEngine=(()=>{
 const numeric=v=>typeof v==='number'&&Number.isFinite(v);
 function eligible(r,key,now=Date.now()){
  const age=now-r.fetched_at*1000;
  return numeric(r[key])&&numeric(r.fetched_at)&&age>=-60000&&age<=20*60*1000&&
   ['CLEAR','WAIT'].includes(r.signal_guard?.status)&&/^\d{4}-\d{2}-\d{2}$/.test(r.as_of||'')&&
   !(r.signal_guard.flags||[]).some(f=>['STALE_DATA','INVALID_BARS','MISSING_DATA'].includes(f.code));
 }
 function compare(key){return (a,b)=>b[key]-a[key]||
  (b['raw_'+key]??b[key])-(a['raw_'+key]??a[key])||
  (a.risk??100)-(b.risk??100)||(b.avg_value_turnover_20??0)-(a.avg_value_turnover_20??0)||
  a.ticker.localeCompare(b.ticker);}
 function rows(all,key,now=Date.now()){return [...all].filter(r=>eligible(r,key,now)).sort(compare(key));}
 function position(all,row,key){return {rank:all.findIndex(r=>r[key]===row[key])+1,ties:all.filter(r=>r[key]===row[key]).length};}
 return {eligible,compare,rows,position};
})();
if(typeof module!=='undefined')module.exports=RankingEngine;
