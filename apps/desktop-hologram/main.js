const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let win;

const PHASE_SETTINGS = {
  idle:      { opacity: 0.55, alwaysOnTop: 'normal',      focus: false },
  listening: { opacity: 0.95, alwaysOnTop: 'screen-saver', focus: true  },
  thinking:  { opacity: 0.85, alwaysOnTop: 'screen-saver', focus: false },
  speaking:  { opacity: 0.95, alwaysOnTop: 'screen-saver', focus: true  },
  offline:   { opacity: 0.35, alwaysOnTop: 'normal',       focus: false },
};

function applyWindowMode(phase) {
  if (!win) return;
  const cfg = PHASE_SETTINGS[phase] || PHASE_SETTINGS.idle;
  win.setOpacity(cfg.opacity);
  win.setAlwaysOnTop(true, cfg.alwaysOnTop);
  if (cfg.focus) win.focus();
}

app.whenReady().then(() => {
  win = new BrowserWindow({
    width: 340,
    height: 520,
    x: 20,
    y: 20,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
    },
  });

  win.loadFile('index.html');
  applyWindowMode('idle');

  // Right-click drag support
  win.on('will-move', () => {});
});

ipcMain.on('desktop-phase', (_, phase) => applyWindowMode(phase));
ipcMain.on('desktop-focus', () => { if (win) win.focus(); });

app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
