const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jarvisDesktop', {
  setPhase: (phase) => ipcRenderer.send('desktop-phase', phase),
  focusOverlay: () => ipcRenderer.send('desktop-focus'),
});
