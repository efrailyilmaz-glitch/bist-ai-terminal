const COPILOT_HISTORY_KEY='bist-ai-copilot-history-v129';
let copilotHistory129=(()=>{try{return JSON.parse(localStorage.getItem(COPILOT_HISTORY_KEY)||'[]')}catch(e){return []}})();
let copilotStatus129=null;

function esc129(v){return String(v==null?'':v).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function num129(v,d=2){const n=Number(v);return Number.isFinite(n)?n.toLocaleString('tr-TR',{minimumFractionDigits:d,maximumFractionDigits:d}):'—'}
function pct129(v){const n=Number(v);return Number.isFinite(n)?(n>0?'+':'')+num129(n,2)+'%':'—'}
function cls129(v){const n=Number(v);return n>0?'up':n<0?'down':'amber'}
function scanRows129(){return [...state.scan.values()].filter(x=>Number.isFinite(Number(x.price)))}
function movers129(dir=1,n=7){return scanRows129().sort((a,b)=>dir*(Number(b.change||0)-Number(a.change||0))).slice(0,n)}
function watchedRows129(){
  const out=[];
  for(const t of state.watchlist||[]){
    const r=state.scan.get(t)||{ticker:t,price:null,change:null};
    out.push(r);
  }
  return out.slice(0,12);
}
function watchSave129(){try{localStorage.setItem('bist-ai-watchlist',JSON.stringify([...state.watchlist]))}catch(e){}}
function toggleWatch129(ticker){
  ticker=String(ticker||state.current).toUpperCase().replace(/\.IS$/,'');
  if(state.watchlist.has(ticker))state.watchlist.delete(ticker);else state.watchlist.add(ticker);
  watchSave129();render(false);
}
window.toggleWatch129=toggleWatch129;

function setTicker129(ticker){
  if(typeof setActiveTicker==='function')setActiveTicker(ticker,true);
}
window.setTicker129=setTicker129;
function go129(view,ticker){
  if(ticker&&typeof setActiveTicker==='function')setActiveTicker(ticker,false);
  state.view=view;render();
}
window.go129=go129;

function miniRow129(r,extra=''){
  const m=state.meta.get(r.ticker)||{};
  return `<div class="miniRow129" onclick="setTicker129('${esc129(r.ticker)}')"><div><b>${esc129(r.ticker)}</b><small>${esc129((m.name||'').slice(0,28))}</small></div><span>₺${num129(r.price)}</span><em class="${cls129(r.change)}">${pct129(r.change)}</em>${extra}</div>`;
}
function listBlock129(title,rows,icon){
  return `<section class="dashCard129"><div class="dashHead129"><div><span>${icon}</span><h3>${title}</h3></div><small>${rows.length}</small></div><div class="miniList129">${rows.length?rows.map(r=>miniRow129(r)).join(''):'<div class="empty129">Veri bekleniyor</div>'}</div></section>`;
}
function activeCard129(){
  const r=state.scan.get(state.current)||{};
  const m=state.meta.get(state.current)||{};
  const guard=r.signal_guard?.status||'—',trap=r.trap_defense?.status||'—';
  return `<section class="activeHero129">
    <div class="activeTop129"><div><span>AKTİF HİSSE</span><h2>${esc129(state.current)} <small>${esc129(m.name||'')}</small></h2></div><button class="star129 ${state.watchlist.has(state.current)?'on':''}" onclick="toggleWatch129('${esc129(state.current)}')">${state.watchlist.has(state.current)?'★':'☆'} Takip</button></div>
    <div class="activePrice129"><b>₺${num129(r.price)}</b><span class="${cls129(r.change)}">${pct129(r.change)}</span></div>
    <div class="activeMetrics129">
      <div><span>Kısa Skor</span><b>${r.short_score??'—'}</b></div>
      <div><span>Uzun Skor</span><b>${r.long_score??'—'}</b></div>
      <div><span>Alpha</span><b>${r.alpha_score??'—'}</b></div>
      <div><span>Signal Guard</span><b class="${guard==='CLEAR'?'up':guard==='BLOCK'?'down':'amber'}">${esc129(guard)}</b></div>
      <div><span>Trap Defense</span><b class="${trap==='CLEAR'?'up':trap==='BLOCK'?'down':'amber'}">${esc129(trap)}</b></div>
    </div>
    <div class="quickActions129">
      <button onclick="go129('detail','${esc129(state.current)}')">Hisse Analizi</button>
      <button onclick="go129('committee','${esc129(state.current)}')">Komite</button>
      <button onclick="go129('kap','${esc129(state.current)}')">KAP</button>
      <button onclick="askCopilot129('${esc129(state.current)} için mevcut terminal verisini özetle; güçlü ve zayıf tarafları açıkla.')">AI'ya Sor</button>
    </div>
  </section>`;
}
function opportunity129(){
  const rows=scanRows129().filter(x=>x.signal_guard?.status==='CLEAR').sort((a,b)=>Number(b.alpha_score||0)-Number(a.alpha_score||0)).slice(0,6);
  return `<section class="dashCard129"><div class="dashHead129"><div><span>✦</span><h3>En Güçlü Fırsatlar</h3></div><button onclick="go129('opportunity')">Tümünü Aç</button></div>
  <div class="oppList129">${rows.map((r,i)=>`<div onclick="setTicker129('${esc129(r.ticker)}')"><span>#${i+1}</span><b>${esc129(r.ticker)}</b><em>Alpha ${r.alpha_score??'—'}</em><strong class="${cls129(r.change)}">${pct129(r.change)}</strong></div>`).join('')||'<div class="empty129">Tarama verisi bekleniyor</div>'}</div></section>`;
}
function risk129(){
  const rows=scanRows129().sort((a,b)=>(Number(b.risk||0)+Number(b.anomaly_score||0))-(Number(a.risk||0)+Number(a.anomaly_score||0))).slice(0,5);
  return `<section class="dashCard129"><div class="dashHead129"><div><span>⚠</span><h3>Risk Radarı</h3></div><button onclick="go129('trapdefense')">Savunma</button></div>
  <div class="riskRows129">${rows.map(r=>`<div onclick="setTicker129('${esc129(r.ticker)}')"><b>${esc129(r.ticker)}</b><span>Risk ${r.risk??'—'}</span><span>Anomali ${r.anomaly_score??'—'}</span><em class="${r.signal_guard?.status==='BLOCK'?'down':'amber'}">${esc129(r.signal_guard?.status||'—')}</em></div>`).join('')}</div></section>`;
}
function tape129(){
  let rows=[...watchedRows129(),...movers129(1,5),...movers129(-1,5)];
  const seen=new Set();rows=rows.filter(r=>r&&r.ticker&&!seen.has(r.ticker)&&seen.add(r.ticker)).slice(0,18);
  const items=rows.map(r=>`<div class="tapeItem129" onclick="setTicker129('${esc129(r.ticker)}')"><b>${esc129(r.ticker)}</b><span>₺${num129(r.price)}</span><em class="${cls129(r.change)}">${pct129(r.change)}</em></div>`).join('');
  return `<section class="priceRail129"><div class="railTitle129"><span>CANLI FİYAT AKIŞI</span><small>Gecikmeli veri</small></div><div class="priceViewport129"><div class="priceTrack129">${items}${items}</div></div></section>`;
}
function dashboard129(){
  const gain=movers129(1,6),loss=movers129(-1,6),watch=watchedRows129();
  const progress=state.total?Math.round(state.scanned/state.total*100):0;
  const adv=state.market.advancers||0,dec=state.market.decliners||0;
  return `<div class="premiumDash129">
    <div class="dashMain129">
      <section class="marketStrip129">
        <div><span>PİYASA REJİMİ</span><b>${esc129(state.market.regime||'NÖTR / TRANSITION')}</b></div>
        <div><span>Breadth</span><b>%${state.market.breadth||0}</b><small>${adv} ↑ / ${dec} ↓</small></div>
        <div><span>Tarama</span><b>%${progress}</b><small>${state.scan.size}/${state.total}</small></div>
        <div><span>Global Skor</span><b>${state.market.global_score??50}</b><small>/100</small></div>
        <div><span>Veri Modu</span><b class="amber">${esc129(state.market.mode||'DELAYED')}</b></div>
      </section>
      ${activeCard129()}
      <div class="dashGrid129">${opportunity129()}${risk129()}</div>
      <div class="dashGrid129">${listBlock129('En Çok Kazananlar',gain,'↗')}${listBlock129('En Çok Kaybedenler',loss,'↘')}</div>
      <section class="dashCard129 watchWide129"><div class="dashHead129"><div><span>★</span><h3>Takip Ettiklerim</h3></div><button onclick="go129('watchlist')">Watchlist</button></div>
        <div class="watchGrid129">${watch.length?watch.map(r=>miniRow129(r,`<button onclick="event.stopPropagation();toggleWatch129('${esc129(r.ticker)}')">×</button>`)).join(''):`<div class="empty129">Takip listen boş. <button onclick="toggleWatch129('${esc129(state.current)}')">Aktif hisseyi ekle</button></div>`}</div>
      </section>
    </div>
    <aside class="dashRail129">${tape129()}${listBlock129('Takip Ettiklerim',watch,'★')}${listBlock129('Kazananlar',gain.slice(0,4),'↗')}${listBlock129('Kaybedenler',loss.slice(0,4),'↘')}</aside>
  </div>`;
}

function watchlist129(){
  const rows=watchedRows129();
  return `<section class="panel"><div class="panelHead"><div><h2>Takip Ettiklerim</h2><p>Yerel watchlist · seçili hisse tüm terminalde aktif olur</p></div><button class="toolbtn" onclick="toggleWatch129('${esc129(state.current)}')">${state.watchlist.has(state.current)?'Aktif hisseyi çıkar':'Aktif hisseyi ekle'}</button></div>
  <div class="watchTable129">${rows.length?rows.map(r=>miniRow129(r,`<button onclick="event.stopPropagation();toggleWatch129('${esc129(r.ticker)}')">×</button>`)).join(''):'<div class="empty">Takip listesi boş.</div>'}</div></section>`;
}

function copilotContext129(){
  return {
    watchlist:[...state.watchlist],
    gainers:movers129(1,6).map(x=>({ticker:x.ticker,price:x.price,change:x.change,alpha_score:x.alpha_score})),
    losers:movers129(-1,6).map(x=>({ticker:x.ticker,price:x.price,change:x.change,alpha_score:x.alpha_score})),
    visible_summary:state.scan.get(state.current)||{}
  };
}
function saveCopilotHistory129(){try{localStorage.setItem(COPILOT_HISTORY_KEY,JSON.stringify(copilotHistory129.slice(-20)))}catch(e){}}
function renderCopilotMessages129(){
  const box=document.querySelector('#copilotMessages129');if(!box)return;
  box.innerHTML=copilotHistory129.length?copilotHistory129.map(x=>`<div class="chatMsg129 ${x.role}"><span>${x.role==='assistant'?'AI':'Sen'}</span><p>${esc129(x.content).replace(/\n/g,'<br>')}</p></div>`).join(''):'<div class="copilotWelcome129"><b>BIST AI Copilot</b><p>Aktif hisseyi, açık ekranı ve terminal verisini bağlam olarak kullanırım.</p><div><button data-prompt="Bu hisseyi özetle">Bu hisseyi özetle</button><button data-prompt="Riskleri açıkla">Riskleri açıkla</button><button data-prompt="Neden bu skorları aldı?">Skorları açıkla</button></div></div>';
  box.scrollTop=box.scrollHeight;
  box.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>askCopilot129(b.dataset.prompt));
}
async function refreshCopilotStatus129(){
  try{copilotStatus129=await getJSON('/api/copilot/status',{force:true})}catch(e){copilotStatus129={status:'ERROR',configured:false}}
  const s=document.querySelector('#copilotStatus129');if(s)s.textContent=copilotStatus129.configured?`${copilotStatus129.model} · bağlı`:'AI anahtarı gerekli';
}
function ensureCopilot129(){
  if(document.querySelector('#copilotFab129'))return;
  document.body.insertAdjacentHTML('beforeend',`<button id="copilotFab129" class="copilotFab129" aria-label="BIST AI Copilot"><span>AI</span><i></i></button>
  <section id="copilotPanel129" class="copilotPanel129" aria-hidden="true">
    <header><div><b>BIST AI Copilot</b><small id="copilotStatus129">Kontrol ediliyor…</small></div><div><button id="copilotSettingsBtn129">⚙</button><button id="copilotClose129">×</button></div></header>
    <div class="copilotTicker129">Aktif hisse <b id="copilotTicker129">${esc129(state.current)}</b> · <span id="copilotView129">${esc129(state.view)}</span></div>
    <div id="copilotConfig129" class="copilotConfig129"><label>OpenAI API anahtarı<input id="copilotKey129" type="password" autocomplete="off" placeholder="sk-..."></label><label>Model<input id="copilotModel129" value="gpt-6-luna"></label><button id="copilotSave129">Yerel cihazda kaydet</button><small>Anahtar yalnız Python backend'de tutulur; web sayfasına geri verilmez.</small></div>
    <div id="copilotMessages129" class="copilotMessages129"></div>
    <div class="copilotComposer129"><textarea id="copilotInput129" rows="2" placeholder="Örn: THYAO neden güçlü görünüyor?"></textarea><button id="copilotSend129">Gönder</button></div>
  </section>`);
  const fab=document.querySelector('#copilotFab129'),panel=document.querySelector('#copilotPanel129');
  fab.onclick=()=>{panel.classList.add('open');panel.setAttribute('aria-hidden','false');document.querySelector('#copilotTicker129').textContent=state.current;document.querySelector('#copilotView129').textContent=state.view;renderCopilotMessages129();refreshCopilotStatus129();setTimeout(()=>document.querySelector('#copilotInput129')?.focus(),100)};
  document.querySelector('#copilotClose129').onclick=()=>{panel.classList.remove('open');panel.setAttribute('aria-hidden','true')};
  document.querySelector('#copilotSettingsBtn129').onclick=()=>document.querySelector('#copilotConfig129').classList.toggle('open');
  document.querySelector('#copilotSave129').onclick=saveCopilotConfig129;
  document.querySelector('#copilotSend129').onclick=()=>askCopilot129();
  document.querySelector('#copilotInput129').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();askCopilot129()}};
  renderCopilotMessages129();refreshCopilotStatus129();
}
async function saveCopilotConfig129(){
  const key=document.querySelector('#copilotKey129').value.trim(),model=document.querySelector('#copilotModel129').value.trim();
  const btn=document.querySelector('#copilotSave129');btn.disabled=true;btn.textContent='Kaydediliyor…';
  try{
    const r=await fetch('/api/copilot/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key,model})});
    const d=await r.json();copilotStatus129=d;
    document.querySelector('#copilotKey129').value='';
    document.querySelector('#copilotConfig129').classList.remove('open');
    await refreshCopilotStatus129();
  }catch(e){alert('Copilot ayarı kaydedilemedi: '+e.message)}
  finally{btn.disabled=false;btn.textContent='Yerel cihazda kaydet'}
}
async function askCopilot129(prefill=''){
  ensureCopilot129();
  const panel=document.querySelector('#copilotPanel129');panel.classList.add('open');panel.setAttribute('aria-hidden','false');
  const input=document.querySelector('#copilotInput129');
  const message=String(prefill||input.value||'').trim();if(!message)return;
  input.value='';copilotHistory129.push({role:'user',content:message});saveCopilotHistory129();renderCopilotMessages129();
  const send=document.querySelector('#copilotSend129');send.disabled=true;send.textContent='…';
  document.querySelector('#copilotTicker129').textContent=state.current;document.querySelector('#copilotView129').textContent=state.view;
  try{
    const resp=await fetch('/api/copilot/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,ticker:state.current,view:state.view,history:copilotHistory129.slice(0,-1),context:copilotContext129()})});
    const d=await resp.json();
    copilotHistory129.push({role:'assistant',content:d.answer||'Yanıt alınamadı.'});saveCopilotHistory129();renderCopilotMessages129();
    if(d.status==='NOT_CONFIGURED')document.querySelector('#copilotConfig129').classList.add('open');
  }catch(e){copilotHistory129.push({role:'assistant',content:'Copilot bağlantı hatası: '+e.message});renderCopilotMessages129()}
  finally{send.disabled=false;send.textContent='Gönder'}
}
window.askCopilot129=askCopilot129;

const render59=render;
render=function(...args){
  render59(...args);
  ensureCopilot129();
  const t=document.querySelector('#copilotTicker129'),v=document.querySelector('#copilotView129');if(t)t.textContent=state.current;if(v)v.textContent=state.view;
  if(state.view==='overview'){
    els.title.textContent='Premium Market Command Center';
    els.subtitle.textContent='Aktif hisse · fırsatlar · risk · watchlist · kazananlar/kaybedenler · BIST AI Copilot';
    els.content.innerHTML=dashboard129();
  }else if(state.view==='watchlist'){
    els.title.textContent='Takip Ettiklerim';
    els.subtitle.textContent='Watchlist · fiyat · günlük değişim · hızlı aktif hisse geçişi';
    els.content.innerHTML=watchlist129();
  }
};
ensureCopilot129();
