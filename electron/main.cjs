const { app, BrowserWindow, Menu, shell, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const http = require('http');

let mainWindow = null;
let backend = null;
let backendPort = null;
let quitting = false;

app.setName('BIST AI Terminal');

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
      env: { ...process.env, BIST_AI_PORT: String(port), PYTHONUNBUFFERED: '1' }
    });
  } else {
    const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
    backend = spawn(python, ['-m', 'app.desktop_server'], {
      cwd: path.resolve(__dirname, '..'),
      windowsHide: true,
      stdio: 'inherit',
      env: { ...process.env, BIST_AI_PORT: String(port), PYTHONUNBUFFERED: '1' }
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
  try {
    backendPort = await freePort();
    startBackend(backendPort);
    await waitForBackend(backendPort);
    await mainWindow.loadURL('http://127.0.0.1:' + backendPort);
  } catch (err) {
    dialog.showErrorBox('BIST AI Terminal Başlatılamadı', String(err && err.message ? err.message : err));
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0 && backendPort) {
    createWindow();
    mainWindow.loadURL('http://127.0.0.1:' + backendPort);
  }
});

app.on('before-quit', () => {
  quitting = true;
  if (backend) {
    try { backend.kill(); } catch (_) {}
    backend = null;
  }
});
