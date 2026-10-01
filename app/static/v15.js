const V15_GUIDES={
overview:'Komuta Merkezi, BIST genelindeki kısa/uzun vade güç dağılımını gösterir. Yüksek skor tek başına işlem kararı değildir; detay ekranında hedef, stop ve komite teyidini kontrol edin.',
opportunity:'Fırsat Avcısı, teknik + temel + analist + KAP + haber + makro veriyi tek aday skorunda toplar. MEGA/STRONG adaylar araştırma önceliğidir, otomatik al emri değildir.',
premium:'Premium Lab, değerleme ve bilanço kalitesini özetler. Fair Value model tahminidir; piyasa fiyatının mutlaka oraya gideceği anlamına gelmez.',
committee:'Investment Committee, bir adayı almamak için neden arar. Hard gate başarısızsa sistem adayı veto eder. PASS araştırma onayıdır, garanti değildir.',
smartmoney:'Smart Money ekranı OHLCV’den birikim/dağıtım davranışı arar. Belirli bir kişi veya kurumun işlem yaptığını kanıtlamaz.',
smradar:'Pre-Markup Radar, henüz fiyat hareketi başlamadan birikim benzeri yapı arar. En faydalı kullanım: alarm sonrası hedef/stop ve komite ekranıyla teyit.',
protools:'Pro Toolkit, VWAP/AVWAP, ATR, Donchian, Keltner, Pivot ve forensic muhasebe kontrollerini birlikte gösterir.',
peers:'Peer Comparison, şirketi aynı sektördeki benzer şirketlerle karşılaştırır. Percentile yüksekse ilgili metrikte peer grubuna göre daha güçlü konumdadır.',
compare:'Sembol Karşılaştırma, birden çok hisseyi aynı metriklerle yan yana değerlendirir. Başlıklara tıklayarak sıralayabilirsiniz.',
proalerts:'Pro Alert Center, birden fazla koşul aynı anda gerçekleştiğinde alarm üretir. ALL tüm koşullar, ANY koşullardan en az biri demektir.',
regime:'Market Regime, piyasanın trend/volatilite/breadth yapısını özetler. Aynı hisse sinyali farklı rejimlerde farklı başarı gösterebilir.',
rrg:'Relative Rotation, hisselerin XU100’e göre göreli güç ve momentum yönünü gösterir. Leading güçlü; Improving güç kazanan; Weakening güç kaybeden; Lagging zayıf bölgedir.',
seasonality:'Seasonality, geçmiş takvim davranışını gösterir. Geçmiş mevsimsellik gelecekte tekrar etmek zorunda değildir.',
riskintel:'Risk Intelligence beta, korelasyon, drawdown ve tail-risk ölçer. Downside beta yüksekse XU100 düşerken hisse daha sert tepki verebilir.',
heatmap:'Watchlist Heatmap, izleme listenizdeki hisselerin alpha, kısa/uzun skor ve riskini tek bakışta karşılaştırır.',
alpha:'Alpha Validation, geçmişte benzer teknik skorların XU100’e karşı ne kadar işe yaradığını ölçer. N küçükse güven düşüktür.',
ensemble:'Ensemble, farklı teknik modeller aynı yönde mi diye kontrol eder. Agreement LOW ise sinyaller birbiriyle çelişiyor demektir.',
sectors:'Sektör Rotasyonu, hangi sektörlerin göreli güç kazandığını gösterir.',
eventstudy:'KAP Event Study, geçmiş KAP olaylarından sonra 1/5/20 günlük getirileri inceler. Küçük örneklemde sonuçlar dikkatle yorumlanmalıdır.',
multichart:'Multi Chart, birden fazla hisseyi aynı anda görsel olarak karşılaştırır.',
replay:'Bar Replay, geçmiş grafiği ileri doğru oynatarak sinyalleri hindsight olmadan incelemenize yardımcı olur.',
alerts:'Signal Inbox, sistemin oluşturduğu önemli fırsat ve risk sinyallerini toplar.',
internals:'Market Internals, piyasa genişliği ve iç güç dağılımını gösterir.',
all:'Tüm BIST tablosunda başlıklara tıklayarak artan/azalan sıralama yapabilirsiniz.',
short:'Kısa Vade, günler–haftalar için momentum ve breakout odaklı adayları sıralar.',
long:'Uzun Vade, aylar için uzun trend, kalite ve göreli güç odaklı adayları sıralar.',
factors:'Factor Lab; value, quality, growth, momentum ve risk faktörlerini karşılaştırır.',
fundamental:'Temel Analiz, şirketin değerleme, büyüme, kârlılık ve bilanço sağlığını inceler.',
setups:'Setup Radar, Golden Cross, squeeze, divergence ve trend alignment gibi teknik yapıları tarar.',
anomaly:'Anomali Radar, olağandışı fiyat/hacim davranışını gösterir; manipülasyon iddiası değildir.',
portfolio:'Model Portföy, risk azaltılmış örnek araştırma sepetidir; gerçek portföy önerisi değildir.',
watchlist:'Watchlist, seçtiğiniz hisseleri tek yerde izler.',
detail:'Hisse Analizi, grafik + göstergeler + hedef/stop + karar seviyelerini bir araya getirir.',
backtest:'Strategy Lab, stratejilerin geçmiş performansını işlem maliyeti ve slippage ile test eder.',
catalysts:'Catalyst Calendar, KAP/temettü/bilanço gibi potansiyel fiyat katalizörlerini toplar.',
journal:'Research Journal, araştırma notlarını ve tezleri kaydetmek içindir.',
health:'Data Health, hangi veri kaynağının çalıştığını ve verinin gecikmeli/eksik olup olmadığını gösterir.',
kap:'KAP & Haber, şirket açıklamaları ve haber akışını araştırma bağlamında toplar.',
execution:'Execution Center paper emir, risk limitleri ve broker köprüsünü yönetir. Direct live emir resmi broker API doğrulanana kadar kilitlidir.',
experience:'Experience Lab, canlı oluşan sinyallerin 5/20/60 gün sonra ne yaptığını ölçer; sistemin gerçek tecrübe hafızasıdır.'
};
const V15_METRIC_HELP={RSI:'RSI 0–100 momentum göstergesidir. 70 üzeri aşırı güçlü/aşırı alım, 30 altı aşırı zayıf/aşırı satım bölgesi olabilir.',ADX:'ADX trend gücünü ölçer; 25 üzeri genellikle daha belirgin trend demektir. Yönü +DI/-DI belirler.','Smart Money':'Fiyat/hacim davranışından türetilen proxy skordur; gerçek takas veya broker akışı değildir.','Health Score':'Bilanço ve finansal kalite özetidir.','Fair Value':'Model bazlı değer aralığıdır, garanti hedef değildir.','Risk':'Volatilite ve fiyat davranışından türetilmiş risk skorudur.','Alpha':'XU100’e karşı göreli araştırma gücü skorudur.'};
function v15Guide(){const t=V15_GUIDES[state.view];return t?'<div class="pageGuide"><b>Bu sayfa ne anlatıyor?</b><span>'+t+'</span></div>':''}
function v15AddGuide(){if(!$('#content')||$('#content .pageGuide'))return;const g=v15Guide();if(g)$('#content').insertAdjacentHTML('beforeend',g)}
function v15MetricHelp(){document.querySelectorAll('.indicatorCard,.stat,.metric,.premiumHero>div,.componentGrid>div').forEach(el=>{if(el.dataset.helped)return;const label=(el.querySelector('span')?.textContent||'').trim();const hit=Object.entries(V15_METRIC_HELP).find(([k])=>label.toLowerCase().includes(k.toLowerCase()));if(hit){el.dataset.helped='1';el.title=hit[1];el.insertAdjacentHTML('beforeend','<small class="metricHelp">'+hit[1]+'</small>')}})}
function v15ParseCell(td){
  const raw=(td?.textContent||'').trim(), cleaned=raw.replace(/[₺%x]/gi,'').trim();
  if(!cleaned)return '';
  let s=cleaned.replace(/\s/g,'');
  const hasComma=s.includes(','),hasDot=s.includes('.');
  if(hasComma&&hasDot){
    if(s.lastIndexOf(',')>s.lastIndexOf('.'))s=s.replace(/\./g,'').replace(',','.');
    else s=s.replace(/,/g,'');
  }else if(hasComma){
    s=s.replace(/\./g,'').replace(',','.');
  }else if(hasDot){
    const parts=s.split('.');
    if(parts.length>2)s=parts.slice(0,-1).join('')+'.'+parts.at(-1);
  }
  const n=Number(s);
  return Number.isFinite(n)?n:raw.toLocaleLowerCase('tr');
}
function v15SortTables(){document.querySelectorAll('table.stockTable').forEach(table=>{table.querySelectorAll('thead th').forEach((th,i)=>{if(th.dataset.sortable)return;th.dataset.sortable='1';th.classList.add('sortableTh');th.title='Sıralamak için tıkla';th.addEventListener('click',()=>{const body=table.tBodies[0];if(!body)return;const asc=th.dataset.dir!=='asc';table.querySelectorAll('th').forEach(x=>{x.dataset.dir='';x.classList.remove('sortAsc','sortDesc')});th.dataset.dir=asc?'asc':'desc';th.classList.add(asc?'sortAsc':'sortDesc');const rows=[...body.rows];rows.sort((a,b)=>{const A=v15ParseCell(a.cells[i]),B=v15ParseCell(b.cells[i]);if(typeof A==='number'&&typeof B==='number')return asc?A-B:B-A;return asc?String(A).localeCompare(String(B),'tr'):String(B).localeCompare(String(A),'tr')});rows.forEach(r=>body.appendChild(r))})})})}
async function v15DecisionLevels(){if(!['detail','committee','smartmoney'].includes(state.view))return;if($('#decisionLevelsBox'))return;const root=$('#content .panel');if(!root)return;root.insertAdjacentHTML('beforeend','<div id="decisionLevelsBox" class="panelSub"><div class="subTitle"><b>Karar Seviyeleri</b><span>hedef · stop · breakout · olası dip bölgesi</span></div><div class="loading">Seviyeler hesaplanıyor…</div></div>');const b=$('#decisionLevelsBox');try{const d=await getJSON('/api/decision-levels/'+state.current);b.innerHTML='<div class="decisionGrid"><div><span>Kısa Vade Hedef</span><b>₺'+fmt(d.short_target)+'</b><small>günler–haftalar</small></div><div><span>Orta Vade Hedef</span><b>₺'+fmt(d.medium_target)+'</b><small>1–3 ay senaryosu</small></div><div><span>Uzun Vade Hedef</span><b>₺'+fmt(d.long_target)+'</b><small>6–12 ay teknik senaryo</small></div><div><span>Breakout Teyidi</span><b class="up">₺'+fmt(d.breakout_confirmation)+'</b><small>üzeri kapanış teyidi</small></div><div><span>Stop Referansı</span><b class="down">₺'+fmt(d.stop_reference)+'</b><small>altı tez zayıflar</small></div><div><span>Hard Invalidation</span><b class="down">₺'+fmt(d.hard_invalidation)+'</b><small>güçlü teknik geçersizlik</small></div></div><div class="dipZone"><div><span>Olası Dip / Tepki Bölgesi</span><b>₺'+fmt(d.dip_zone_low)+' – ₺'+fmt(d.dip_zone_high)+'</b><small>Güven '+d.dip_zone_confidence+'/100'+(d.trend_down?' · düşüş trendi aktif':'')+'</small></div><p>'+d.guidance.dip+'</p></div><div class="actionGuide"><p><b>Yukarı teyit:</b> '+d.guidance.breakout+'</p><p><b>Risk yönetimi:</b> '+d.guidance.stop+'</p><p><b>Hedefler:</b> '+d.guidance.targets+'</p></div><p class="muted">'+d.note+'</p>'}catch(e){b.innerHTML='<div class="empty">'+e.message+'</div>'}}
let v15LastAlert=Number(localStorage.getItem('v15-alert-id')||0);
function v15Toast(title,body,type='info'){let stack=$('#toastStack');if(!stack){document.body.insertAdjacentHTML('beforeend','<div id="toastStack" class="toastStack"></div>');stack=$('#toastStack')}const el=document.createElement('div');el.className='bistToast '+type;el.innerHTML='<b>'+title+'</b><span>'+body+'</span>';stack.prepend(el);setTimeout(()=>el.classList.add('show'),20);setTimeout(()=>{el.classList.remove('show');setTimeout(()=>el.remove(),250)},8500)}
async function v15PollAlerts(){try{const d=await getJSON('/api/background/alerts?limit=20&since='+v15LastAlert);for(const x of (d.alerts||[]).slice().reverse()){v15LastAlert=Math.max(v15LastAlert,Number(x.id)||0);const typ=(x.type==='DISTRIBUTION_RISK'||x.type==='CYCLE_SELL_RISK')?'risk':x.type==='PRE_MARKUP_WATCH'?'money':'good';v15Toast((x.type||'BIST AI')+' · '+x.ticker,x.message||'',typ)}localStorage.setItem('v15-alert-id',String(v15LastAlert))}catch(e){}}
function v15Enhance(){setTimeout(()=>{v15AddGuide();v15MetricHelp();v15SortTables();v15DecisionLevels()},0)}
const v15RenderBase=render;render=function(){v15RenderBase();v15Enhance()}
let v15SortTimer=null;
try{
  const root=$('#content');
  if(root){
    const obs=new MutationObserver(()=>{clearTimeout(v15SortTimer);v15SortTimer=setTimeout(()=>{try{v15SortTables()}catch(e){}},60)});
    obs.observe(root,{childList:true,subtree:true});
  }
}catch(e){}
setInterval(v15PollAlerts,60000);setTimeout(v15PollAlerts,3500);

let v15Observer=null;
function v15InstallObserver(){
  if(v15Observer||!document.body)return;
  let queued=false;
  v15Observer=new MutationObserver(()=>{
    if(queued)return;queued=true;
    requestAnimationFrame(()=>{queued=false;v15SortTables();v15MetricHelp()});
  });
  const root=$('#content')||document.body;
  v15Observer.observe(root,{childList:true,subtree:true});
}
setTimeout(v15InstallObserver,100);
