const { app, BrowserWindow, Menu, shell, dialog, Tray, nativeImage, screen } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const http = require('http');

let mainWindow = null;
let backend = null;
let backendPort = null;
let quitting = false;
let tray = null;
let alertTimer = null;
let lastAlertId = null;
let lastCommitteeAlertId = 0;
let toastWindow = null;

app.setName('BIST AI Terminal');
if (process.platform === 'win32') app.setAppUserModelId('com.bistai.terminal');

const singleInstanceLock = app.requestSingleInstanceLock();
if (!singleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
  });
}

function backendExecutable() {
  if (!app.isPackaged) return null;
  const exe = process.platform === 'win32' ? 'bist-ai-backend.exe' : 'bist-ai-backend';
  return path.join(process.resourcesPath, 'backend', exe);
}

function startBackend(port) {
  if (app.isPackaged) {
    const exe = backendExecutable();
    backend = spawn(exe, [], {
      cwd: path.dirname(exe),
      windowsHide: true,
      stdio: 'ignore',
      env: { ...process.env, BIST_AI_PORT: String(port), BIST_AI_DESKTOP: '1', PYTHONUNBUFFERED: '1' }
    });
  } else {
    const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
    backend = spawn(python, ['-m', 'app.desktop_server'], {
      cwd: path.resolve(__dirname, '..'),
      windowsHide: true,
      stdio: 'inherit',
      env: { ...process.env, BIST_AI_PORT: String(port), BIST_AI_DESKTOP: '1', PYTHONUNBUFFERED: '1' }
    });
  }

  backend.on('exit', (code) => {
    backend = null;
    if (!quitting && mainWindow && !mainWindow.isDestroyed()) {
      dialog.showErrorBox('BIST AI Terminal', 'Yerel veri motoru beklenmedik şekilde kapandı. Kod: ' + code);
    }
  });
}

function waitForBackend(port, timeoutMs = 30000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const retry = () => {
      if (Date.now() - started > timeoutMs) return reject(new Error('Backend startup timeout'));
      setTimeout(tryOnce, 250);
    };
    const tryOnce = () => {
      const req = http.get({ host: '127.0.0.1', port, path: '/health', timeout: 1200 }, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      });
      req.on('timeout', () => { req.destroy(); retry(); });
      req.on('error', retry);
    };
    tryOnce();
  });
}

function showMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.show(); mainWindow.focus();
  if (process.platform === 'darwin' && app.dock) app.dock.show();
}
function backendJSON(pathname, method = 'GET') {
  return new Promise((resolve, reject) => {
    if (!backendPort) return reject(new Error('backend not ready'));
    const req=http.request({host:'127.0.0.1',port:backendPort,path:pathname,method,timeout:2500},res=>{let body='';res.on('data',d=>body+=d);res.on('end',()=>{try{resolve(JSON.parse(body||'{}'))}catch(e){reject(e)}})});
    req.on('error',reject);req.on('timeout',()=>{req.destroy();reject(new Error('timeout'))});req.end();
  });
}

function showDesktopToast(title, body, tone='info') {
  try {
    if (toastWindow && !toastWindow.isDestroyed()) toastWindow.destroy();
    const wa=screen.getPrimaryDisplay().workArea;
    toastWindow=new BrowserWindow({width:390,height:118,x:wa.x+wa.width-410,y:wa.y+18,frame:false,transparent:true,resizable:false,alwaysOnTop:true,skipTaskbar:true,focusable:false,show:false,webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true}});
    const border=tone==='risk'?'#ff5e72':tone==='money'?'#f6b94a':'#28d17c';
    const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const html='<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;color:#edf6fb}.box{margin:7px;background:#091722;border:1px solid #204258;border-left:5px solid '+border+';border-radius:12px;padding:14px 16px;box-shadow:0 18px 44px #0009}b{display:block;font-size:13px}p{margin:7px 0 0;color:#a4b7c3;font-size:11px;line-height:1.4}</style><div class="box"><b>'+esc(title)+'</b><p>'+esc(body)+'</p></div>';
    toastWindow.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent(html));toastWindow.once('ready-to-show',()=>toastWindow.showInactive());
    toastWindow.webContents.on('before-input-event',()=>showMainWindow());
    setTimeout(()=>{try{if(toastWindow&&!toastWindow.isDestroyed())toastWindow.destroy()}catch(_){}},9000);
  } catch (_) {}
}

function startAlertPolling() {
  if (alertTimer) clearInterval(alertTimer);
  const poll=async()=>{try{const data=await backendJSON('/api/alerts?limit=30'),rows=data.alerts||[];if(lastAlertId===null){lastAlertId=rows.length?rows[0].id:0;return}const fresh=rows.filter(x=>Number(x.id)>Number(lastAlertId)).sort((a,b)=>a.id-b.id);for(const x of fresh){if(x.grade!=='MEGA'&&!(x.grade==='STRONG'&&Number(x.score||0)>=84))continue;const t=x.targets||{};showDesktopToast('BIST AI · '+(x.grade==='MEGA'?'BÜYÜK FIRSAT':'GÜÇLÜ FIRSAT')+' · '+x.ticker,'Skor '+x.score+'/100 · Kısa '+x.short_score+' · Uzun '+x.long_score+(t.short_target_1?' · T1 ₺'+t.short_target_1:''),'good')}if(fresh.length)lastAlertId=Math.max(...fresh.map(x=>Number(x.id)||0),Number(lastAlertId)||0)}catch(_){}
    try{
      const d=await backendJSON('/api/background/alerts?limit=30&since='+lastCommitteeAlertId),rows=d.alerts||[];
      for(const x of rows.slice().reverse()){
        lastCommitteeAlertId=Math.max(lastCommitteeAlertId,Number(x.id)||0);
        if(x.type==='COMMITTEE_PASS'){showDesktopToast('BIST AI · KOMİTE ONAYI · '+x.ticker,x.message||('Komite skoru '+x.score),'good')} else if(x.type==='PRE_MARKUP_WATCH'){showDesktopToast('BIST AI · PRE-MARKUP WATCH · '+x.ticker,x.message||('Birikim skoru '+x.score),'money')} else if(x.type==='DISTRIBUTION_RISK'){showDesktopToast('BIST AI · DISTRIBUTION RISK · '+x.ticker,x.message||('Dağıtım riski '+x.score),'risk')} else if(x.type==='CYCLE_BUY_WINDOW'){showDesktopToast('BIST AI · ALIM PENCERESİ · '+x.ticker,x.message||('Döngü güveni '+x.score),'good')} else if(x.type==='CYCLE_SELL_RISK'){showDesktopToast('BIST AI · SATIŞ RİSKİ · '+x.ticker,x.message||('Döngü riski '+x.score),'risk')}
      }
    }catch(_){}
  };poll();alertTimer=setInterval(poll,60000);
}
function buildTray() {
  try{let icon=nativeImage.createFromPath(path.join(__dirname,'..','build','icon.png'));if(!icon.isEmpty())icon=icon.resize({width:18,height:18});tray=new Tray(icon);tray.setToolTip('BIST AI Terminal · Fırsat Avcısı');const login=app.getLoginItemSettings().openAtLogin;tray.setContextMenu(Menu.buildFromTemplate([{label:'BIST AI Terminal’i Aç',click:showMainWindow},{label:'Fırsat Radarını Şimdi Tara',click:()=>backendJSON('/api/radar/refresh','POST').catch(()=>{})},{type:'separator'},{label:'Oturum açılışında başlat',type:'checkbox',checked:login,click:item=>app.setLoginItemSettings({openAtLogin:item.checked})},{type:'separator'},{label:'Tamamen Çık',click:()=>{quitting=true;app.quit()}}]));tray.on('click',showMainWindow)}catch(_){}
}
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1480,
    height: 940,
    minWidth: 1120,
    minHeight: 720,
    show: true,
    backgroundColor: '#07121a',
    title: 'BIST AI Terminal',
    autoHideMenuBar: process.platform !== 'darwin',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'splash.html'));
  mainWindow.on('close',event=>{if(!quitting){event.preventDefault();mainWindow.hide();if(process.platform==='darwin'&&app.dock)app.dock.hide();}});

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    const allowed = backendPort && url.startsWith('http://127.0.0.1:' + backendPort);
    if (!allowed && !url.startsWith('file://')) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
}

function buildMenu() {
  const template = [
    ...(process.platform === 'darwin' ? [{
      label: 'BIST AI Terminal',
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { label: 'Güncellemeleri Gör', click: () => shell.openExternal('https://github.com/efrailyilmaz-glitch/bist-ai-terminal/releases') },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    }] : []),
    {
      label: 'Dosya',
      submenu: [
        { label: 'Yenile', accelerator: 'CmdOrCtrl+R', click: () => mainWindow?.reload() },
        { type: 'separator' },
        ...(process.platform === 'darwin' ? [] : [{ role: 'quit', label: 'Çıkış' }])
      ]
    },
    {
      label: 'Görünüm',
      submenu: [
        { role: 'reload', label: 'Yenile' },
        { role: 'togglefullscreen', label: 'Tam Ekran' },
        { type: 'separator' },
        { role: 'zoomIn', label: 'Yakınlaştır' },
        { role: 'zoomOut', label: 'Uzaklaştır' },
        { role: 'resetZoom', label: 'Normal Boyut' }
      ]
    },
    {
      label: 'Yardım',
      submenu: [
        { label: 'GitHub', click: () => shell.openExternal('https://github.com/efrailyilmaz-glitch/bist-ai-terminal') },
        { label: 'Güncellemeleri Gör', click: () => shell.openExternal('https://github.com/efrailyilmaz-glitch/bist-ai-terminal/releases') }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

app.whenReady().then(async () => {
  buildMenu();
  createWindow();
  buildTray();
  try {
    backendPort = await freePort();
    startBackend(backendPort);
    await waitForBackend(backendPort);
    await mainWindow.loadURL('http://127.0.0.1:' + backendPort);
    startAlertPolling();
  } catch (err) {
    dialog.showErrorBox('BIST AI Terminal Başlatılamadı', String(err && err.message ? err.message : err));
    app.quit();
  }
});

app.on('window-all-closed', () => {});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0 && backendPort) {
    createWindow();
    mainWindow.loadURL('http://127.0.0.1:' + backendPort);
  }
});

app.on('before-quit', () => {
  quitting = true;
  if (alertTimer) { clearInterval(alertTimer); alertTimer = null; }
  if (backend) {
    try { backend.kill(); } catch (_) {}
    backend = null;
  }
});
