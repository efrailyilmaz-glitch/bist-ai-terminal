/* Price/time anchored drawings rendered on the native main-price pane. */
(function(root){
 const timeKey=t=>typeof t==='object'?`${t.year}-${String(t.month).padStart(2,'0')}-${String(t.day).padStart(2,'0')}`:String(t);
 function distance(p,a,b){const dx=b.x-a.x,dy=b.y-a.y,k=dx*dx+dy*dy;const t=k?Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/k)):0;return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy);}
 function channel(a,b,c){const dx=b.x-a.x;if(Math.abs(dx)<1)return null;const off=c.y-(a.y+(b.y-a.y)*(c.x-a.x)/dx);return [{x:a.x,y:a.y+off},{x:b.x,y:b.y+off}];}
 const names={cursor:'Seç / gezin',line:'Çizgi',horizontal:'Yatay çizgi',parallel:'Paralel kanal',ruler:'Cetvel'};
 class Drawings{
  constructor(chart,series,candles,ticker,interval,toolbar){
   Object.assign(this,{chart,series,candles,ticker,interval,toolbar});this.key=`bist-drawings-v1:${ticker}:${interval}`;this.tool='cursor';this.pending=[];this.hover=null;this.selected=null;this.undoStack=[];this.redoStack=[];
   try{this.items=JSON.parse(localStorage.getItem(this.key)||'[]').filter(x=>names[x.type]&&Array.isArray(x.points)&&x.points.every(p=>p&&Number.isFinite(p.price)&&p.price>0&&p.time!=null)).slice(0,100);}catch(e){this.items=[];}
   this.indices=new Map(candles.map((c,i)=>[timeKey(c.time),i]));
   this.view={zOrder:()=> 'top',renderer:()=>({draw:target=>target.useMediaCoordinateSpace(scope=>this.draw(scope.context,scope.mediaSize))})};
   this.click=e=>this.onClick(e);this.move=e=>{this.hover=this.anchor(e);this.refresh();};
   this.keydown=e=>{if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)||e.target.isContentEditable)return;if(e.key==='Escape'){this.setTool('cursor');}if(e.key==='Delete'&&this.selected){e.preventDefault();this.removeSelected();}};
   series.attachPrimitive(this);
   this.bind();this.status();
  }
  attached({requestUpdate}){this.requestUpdate=requestUpdate;this.chart.subscribeClick(this.click);this.chart.subscribeCrosshairMove(this.move);document.addEventListener('keydown',this.keydown);}
  detached(){this.chart.unsubscribeClick(this.click);this.chart.unsubscribeCrosshairMove(this.move);document.removeEventListener('keydown',this.keydown);this.requestUpdate=null;}
  paneViews(){return [this.view];} updateAllViews(){}
  refresh(){this.requestUpdate?.();}
  point(p){const x=this.chart.timeScale().timeToCoordinate(p.time),y=this.series.priceToCoordinate(p.price);return x==null||y==null?null:{x,y};}
  anchor(e){if(!e.point||(e.paneIndex!=null&&e.paneIndex!==0))return null;const size=this.chart.paneSize(0);if(e.point.y<0||e.point.y>size.height||e.point.x<0||e.point.x>size.width)return null;const logical=this.chart.timeScale().coordinateToLogical(e.point.x);if(logical==null)return null;const i=Math.round(logical),bar=this.candles[i],price=this.series.coordinateToPrice(e.point.y);return bar&&Number.isFinite(price)&&price>0?{time:bar.time,price}:null;}
  snapshot(){this.undoStack.push(JSON.stringify(this.items));if(this.undoStack.length>50)this.undoStack.shift();this.redoStack=[];}
  save(){try{localStorage.setItem(this.key,JSON.stringify(this.items));this.storageError=false;}catch(e){this.storageError=true;}this.status();this.refresh();}
  setTool(tool){this.tool=tool;this.pending=[];this.hover=null;this.chart.applyOptions({handleScroll:tool==='cursor'});this.toolbar.querySelectorAll('[data-draw]').forEach(b=>{b.classList.toggle('active',b.dataset.draw===tool);b.setAttribute('aria-pressed',b.dataset.draw===tool?'true':'false');});this.status();this.refresh();}
  status(){const hint=this.toolbar.closest('.drawingWorkspace').querySelector('.drawingHint');if(hint)hint.textContent=this.storageError?'Çizim kaydedilemedi; bu sayfada görünür.':`${names[this.tool]} · ${this.items.length} çizim · ${this.tool==='cursor'?'Çizime tıklayın, ardından Seçileni sil.':this.tool==='parallel'?'İki uç nokta, sonra kanal genişliği için üçüncü nokta.':this.tool==='horizontal'?'Fiyat bölgesinde tek noktaya tıklayın.':'Fiyat bölgesinde başlangıç ve bitişe tıklayın.'} Esc: iptal. ${this.interval} çizimleri bu tarayıcıda saklanır.`;}
  onClick(e){const anchor=this.anchor(e);if(!anchor)return;
   if(this.tool==='cursor'){this.selected=null;for(const item of [...this.items].reverse()){const pts=item.points.map(p=>this.point(p));if(pts.some(x=>!x))continue;let lines=item.type==='horizontal'?[[{x:0,y:pts[0].y},{x:this.chart.paneSize(0).width,y:pts[0].y}]]:pts.length>=2?[[pts[0],pts[1]]]:[];if(item.type==='parallel'&&pts.length===3){const other=channel(...pts);if(other)lines.push(other);}if(lines.some(([a,b])=>distance(e.point,a,b)<9)){this.selected=item.id;break;}}this.refresh();return;}
   this.pending.push(anchor);const need=this.tool==='horizontal'?1:this.tool==='parallel'?3:2;
   if(this.pending.length===need){if(this.tool==='parallel'&&timeKey(this.pending[0].time)===timeKey(this.pending[1].time)){this.pending=[];this.status();return;}if(this.items.length>=100){this.pending=[];this.toolbar.closest('.drawingWorkspace').querySelector('.drawingHint').textContent='En fazla 100 çizim. Önce bir çizimi silin.';return;}this.snapshot();this.items.push({id:crypto.randomUUID(),type:this.tool,points:this.pending,color:this.toolbar.querySelector('[type=color]').value});this.selected=this.items.at(-1).id;this.pending=[];this.save();this.setTool('cursor');}else this.refresh();
  }
  removeSelected(){if(!this.selected)return;this.snapshot();this.items=this.items.filter(x=>x.id!==this.selected);this.selected=null;this.save();}
  undo(){if(!this.undoStack.length)return;this.redoStack.push(JSON.stringify(this.items));this.items=JSON.parse(this.undoStack.pop());this.pending=[];this.selected=null;this.save();}
  redo(){if(!this.redoStack.length)return;this.undoStack.push(JSON.stringify(this.items));this.items=JSON.parse(this.redoStack.pop());this.save();}
  bind(){this.toolbar.querySelectorAll('[data-draw]').forEach(b=>b.onclick=()=>this.setTool(b.dataset.draw));this.toolbar.querySelector('[data-action=undo]').onclick=()=>this.undo();this.toolbar.querySelector('[data-action=redo]').onclick=()=>this.redo();this.toolbar.querySelector('[data-action=delete]').onclick=()=>this.removeSelected();this.toolbar.querySelector('[data-action=clear]').onclick=()=>{if(!this.items.length)return;this.snapshot();this.items=[];this.selected=null;this.save();};}
  draw(ctx,size){ctx.save();ctx.beginPath();ctx.rect(0,0,size.width,size.height);ctx.clip();const draft=this.pending.length?{id:'draft',type:this.tool,color:this.toolbar.querySelector('[type=color]').value,points:[...this.pending,...(this.hover?[this.hover]:[])]}:null;
   for(const item of [...this.items,...(draft?[draft]:[])]){const pts=item.points.map(p=>this.point(p));if(!pts.length||pts.some(x=>!x))continue;ctx.strokeStyle=item.color;ctx.fillStyle=item.color;ctx.lineWidth=item.id===this.selected?3:2;ctx.setLineDash(item.id==='draft'?[5,4]:[]);const line=(a,b)=>{ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();};
    if(item.type==='horizontal'){line({x:0,y:pts[0].y},{x:size.width,y:pts[0].y});ctx.font='12px sans-serif';ctx.fillText(item.points[0].price.toFixed(2),8,Math.max(14,pts[0].y-5));}
    else if(pts.length>=2){line(pts[0],pts[1]);if(item.type==='parallel'&&pts.length>=3){const other=channel(...pts);if(other){line(...other);ctx.globalAlpha=.1;ctx.beginPath();ctx.moveTo(pts[0].x,pts[0].y);ctx.lineTo(pts[1].x,pts[1].y);ctx.lineTo(other[1].x,other[1].y);ctx.lineTo(other[0].x,other[0].y);ctx.closePath();ctx.fill();ctx.globalAlpha=1;}}
     if(item.type==='ruler'){const [a,b]=item.points,delta=b.price-a.price,percent=delta/a.price*100,bars=Math.abs(this.indices.get(timeKey(b.time))-this.indices.get(timeKey(a.time)));ctx.setLineDash([3,3]);line(pts[0],{x:pts[1].x,y:pts[0].y});line({x:pts[1].x,y:pts[0].y},pts[1]);ctx.setLineDash([]);ctx.font='12px sans-serif';const label=`${delta>=0?'+':''}${delta.toFixed(2)} TL / ${percent.toFixed(2)}% / ${bars} bar`;const w=ctx.measureText(label).width+12,x=Math.max(0,Math.min(size.width-w,Math.min(pts[0].x,pts[1].x))),y=Math.max(20,Math.min(pts[0].y,pts[1].y));ctx.fillStyle='#112634';ctx.fillRect(x,y-19,w,21);ctx.fillStyle=item.color;ctx.fillText(label,x+6,y-4);}
    }
    if(item.id===this.selected||item.id==='draft')for(const p of pts){ctx.beginPath();ctx.arc(p.x,p.y,4,0,Math.PI*2);ctx.fill();}
   }ctx.restore();
  }
 }
 const api={Drawings,distance,channel,timeKey};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BistDrawings=api;
})(typeof window!=='undefined'?window:this);
