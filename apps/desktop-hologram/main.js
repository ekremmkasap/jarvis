const { app, BrowserWindow, ipcMain, screen } = require("electron");
const path = require("path");

let windowRef = null;

const PHASE_SETTINGS = {
  idle: { opacity: 0.58, alwaysOnTop: "normal", interactive: false, focus: false },
  listening: { opacity: 0.96, alwaysOnTop: "screen-saver", interactive: true, focus: true },
  thinking: { opacity: 0.88, alwaysOnTop: "screen-saver", interactive: false, focus: false },
  speaking: { opacity: 0.96, alwaysOnTop: "screen-saver", interactive: true, focus: true },
  muted: { opacity: 0.48, alwaysOnTop: "normal", interactive: false, focus: false },
  offline: { opacity: 0.35, alwaysOnTop: "normal", interactive: false, focus: false },
};

function applyWindowMode(phase) {
  if (!windowRef) return;

  const settings = PHASE_SETTINGS[phase] || PHASE_SETTINGS.idle;
  windowRef.setOpacity(settings.opacity);
  windowRef.setAlwaysOnTop(true, settings.alwaysOnTop);
  windowRef.setIgnoreMouseEvents(!settings.interactive, { forward: !settings.interactive });

  if (settings.focus) {
    windowRef.show();
    windowRef.focus();
  } else if (!windowRef.isVisible()) {
    windowRef.showInactive();
  }
}

function createWindow() {
  const { workAreaSize } = screen.getPrimaryDisplay();
  // Swarm modunda pencere biraz daha geniş — 7 ajan bar'ı için
  const isSwarm = process.env.JARVIS_SWARM_HOLOGRAM === "1";
  const width = isSwarm ? 400 : 340;
  const height = 520;
  const x = Math.max(workAreaSize.width - width - 28, 0);
  const y = Math.max(workAreaSize.height - height - 36, 0);

  windowRef = new BrowserWindow({
    width,
    height,
    x,
    y,
    transparent: true,
    backgroundColor: "#00000000",
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    maximizable: false,
    minimizable: false,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  windowRef.loadFile("index.html");
  applyWindowMode("idle");

  windowRef.on("closed", () => {
    windowRef = null;
  });
}

app.whenReady().then(() => {

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

ipcMain.on("desktop-phase", (_, phase) => applyWindowMode(phase));
ipcMain.on("desktop-focus", () => {
  if (!windowRef) return;
  windowRef.show();
  windowRef.focus();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
