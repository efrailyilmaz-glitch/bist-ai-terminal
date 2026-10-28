/* Local, hypothetical fills only. No network or broker integration. */
(function(root){
 'use strict';
 const amount=x=>{const n=Number(x);if(!Number.isFinite(n)||n<=0)throw Error('Pozitif ve sonlu bir sayı girin.');return n;};
 const lots=x=>{const n=amount(x);if(!Number.isSafeInteger(n)||n>1000000)throw Error('Lot, 1–1.000.000 arasında tam sayı olmalı.');return n;};
 const money=x=>Math.round(x*1000000)/1000000;
 function fresh(){return {version:1,cash:1000000,capital:1000000,realized:0,positions:{},orders:[],revision:0};}
 function trade(account,o){
  if(!/^[A-Z0-9]{2,12}$/.test(o.ticker||''))throw Error('Geçersiz hisse.');
  if(!['BUY','SELL','SHORT','COVER'].includes(o.side))throw Error('Geçersiz yön.');
  if(typeof o.id!=='string'||!o.id)throw Error('İşlem kimliği gerekli.');
  const at=o.at||new Date().toISOString(),stamp=Date.parse(at);
  if(!Number.isFinite(stamp)||stamp>Date.now()+60000)throw Error('Geçerli, gelecekte olmayan işlem tarihi girin.');
  const latest=account.orders.find(x=>x.ticker===o.ticker);
  if(latest&&stamp<Date.parse(latest.at))throw Error('Bu hissenin son işleminden eski tarih girilemez.');
  const qty=lots(o.quantity),price=amount(o.price),feeBps=Number(o.feeBps??10);
  if(!Number.isFinite(feeBps)||feeBps<0||feeBps>100)throw Error('Komisyon 0–100 baz puan olmalı.');
  if(account.orders.some(x=>x.id===o.id))throw Error('Bu işlem zaten kaydedildi.');
  const a=JSON.parse(JSON.stringify(account)),p=a.positions[o.ticker]||{quantity:0,avg:0,entryFees:0};
  const notional=qty*price,fee=notional*feeBps/10000,opening=['BUY','SHORT'].includes(o.side);
  if(!Number.isFinite(notional)||notional>250000)throw Error('Simülasyonda emir başına üst sınır 250.000 TL.');
  if(opening && (Math.abs(p.quantity)+qty)*price>a.capital*.12)throw Error('Simülasyonda hisse başına üst sınır başlangıç sermayesinin %12’si.');
  if(opening && a.cash<notional+fee)throw Error('Simülasyon nakdi/teminatı yetersiz.');
  let pnl=null;
  if(o.side==='BUY'||o.side==='SHORT'){
   if((o.side==='BUY'&&p.quantity<0)||(o.side==='SHORT'&&p.quantity>0))throw Error('Önce karşı yöndeki pozisyonu kapatın.');
   const old=Math.abs(p.quantity);p.avg=(old*p.avg+notional)/(old+qty);p.entryFees+=fee;
   p.quantity+=(o.side==='BUY'?qty:-qty);a.cash-=notional+fee;
  }else{
   if((o.side==='SELL'&&p.quantity<=0)||(o.side==='COVER'&&p.quantity>=0)||qty>Math.abs(p.quantity))throw Error('Kapatılacak yeterli pozisyon yok.');
   const allocated=p.entryFees*qty/Math.abs(p.quantity);
   pnl=(o.side==='SELL'?price-p.avg:p.avg-price)*qty-fee-allocated;
   a.cash+=o.side==='SELL'?notional-fee:p.avg*qty+(p.avg-price)*qty-fee;
   p.entryFees-=allocated;p.quantity+=(o.side==='SELL'?-qty:qty);a.realized+=pnl;
  }
  if(p.quantity)a.positions[o.ticker]=p;else delete a.positions[o.ticker];
  a.cash=money(a.cash);a.realized=money(a.realized);a.revision++;
  a.orders.unshift({id:o.id,ticker:o.ticker,side:o.side,quantity:qty,price,fee:money(fee),pnl:pnl===null?null:money(pnl),at:new Date(stamp).toISOString(),recordedAt:new Date().toISOString(),source:o.source||'USER_SIMULATION',runId:o.runId||null});
  return a;
 }
 function levels(text){
  const rows=String(text).trim().split(/\n/).filter(x=>x.trim());
  if(!rows.length||rows.length>100)throw Error('1–100 deneme kademesi girin: fiyat;lot');
  const out=rows.map(row=>{const fields=row.trim().split(';');if(fields.length!==2)throw Error('Her satır fiyat;lot biçiminde olmalı.');return {price:amount(fields[0].replace(',','.')),quantity:lots(fields[1])};}).sort((a,b)=>a.price-b.price);
  if(new Set(out.map(x=>x.price)).size!==out.length)throw Error('Aynı fiyatı tek satırda birleştirin.');
  return out;
 }
 function slice(book,remaining,child,maxPrice){
  lots(remaining);lots(child);amount(maxPrice);
  const index=book.findIndex(x=>x.quantity>0);
  if(index<0)return {stop:'DENEME DERİNLİĞİ TÜKENDİ'};
  const level=book[index];if(level.price>maxPrice)return {stop:'ÜST FİYAT SINIRINA ULAŞILDI'};
  return {index,price:level.price,quantity:Math.min(remaining,child,level.quantity)};
 }
 function excursion(p,candles){
  const xs=(candles||[]).filter(x=>x&&Number.isFinite(Number(x.high))&&Number.isFinite(Number(x.low)));
  if(!xs.length||!p||!Number.isFinite(Number(p.avg))||p.avg<=0||!p.quantity)return {mfePct:null,maePct:null};
  const hi=Math.max(...xs.map(x=>Number(x.high))),lo=Math.min(...xs.map(x=>Number(x.low))),avg=Number(p.avg);
  return p.quantity>0
   ? {mfePct:money((hi/avg-1)*100),maePct:money((lo/avg-1)*100)}
   : {mfePct:money((avg-lo)/avg*100),maePct:money((avg-hi)/avg*100)};
 }
 function valuation(a,quotes){
  let known=0,unreal=0,missing=0;
  const rows=Object.entries(a.positions).map(([ticker,p])=>{const q=quotes[ticker],price=q?.price,ok=typeof price==='number'&&Number.isFinite(price)&&price>0;
   const orders=a.orders.filter(o=>o.ticker===ticker);
   // Determine the start of the current position by replaying quantities backwards, including partial closes.
   let balance=p.quantity,start=null;for(const o of orders){start=o.at;balance-=o.side==='BUY'||o.side==='COVER'?o.quantity:-o.quantity;if(balance===0)break;}
   const pnl=ok?(price-p.avg)*p.quantity-p.entryFees:null,cost=Math.abs(p.quantity)*p.avg+p.entryFees;
   if(ok){unreal+=pnl;known+=p.quantity>0?p.quantity*price:Math.abs(p.quantity)*(2*p.avg-price);}else missing++;
   return {ticker,...p,price:ok?price:null,asOf:q?.as_of||null,pnl,returnPct:ok?pnl/cost*100:null,openedAt:balance===0?start:null,lastAt:orders[0]?.at||null,mfePct:q?.mfePct??null,maePct:q?.maePct??null};
  });
  return {rows,missing,unrealized:missing?null:money(unreal),knownUnrealized:money(unreal),equity:missing?null:money(a.cash+known),totalPnl:missing?null:money(a.realized+unreal),realized:a.realized,cash:a.cash};
 }
 const api={fresh,trade,levels,slice,lots,amount,valuation,excursion};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BistPaperEngine=api;
})(typeof window!=='undefined'?window:this);
