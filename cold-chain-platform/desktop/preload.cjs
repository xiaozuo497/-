const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  start: () => ipcRenderer.invoke("desktop:start"),
  stop: () => ipcRenderer.invoke("desktop:stop"),
  openExternal: () => ipcRenderer.invoke("desktop:open-external"),
  projectRoot: () => ipcRenderer.invoke("desktop:project-root"),
  onStatus: (callback) => ipcRenderer.on("desktop-status", (_event, payload) => callback(payload)),
  onLog: (callback) => ipcRenderer.on("desktop-log", (_event, payload) => callback(payload))
});
