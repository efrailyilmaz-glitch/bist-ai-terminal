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
  a.orders.unshift({id:o.id,ticker:o.ticker,side:o.side,quantity:qty,price,fee:money(fee),pnl:pnl===null?null:money(pnl),at:o.at||new Date().toISOString(),source:o.source||'USER_SIMULATION',runId:o.runId||null});
  a.orders=a.orders.slice(0,500);return a;
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
 const api={fresh,trade,levels,slice,lots,amount};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BistPaperEngine=api;
})(typeof window!=='undefined'?window:this);
