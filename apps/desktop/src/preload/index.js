const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("ytApi", {
  getSettings: () => ipcRenderer.invoke("settings:get"),
  setSavePath: (savePath) => ipcRenderer.invoke("settings:set", savePath),
  selectSavePath: () => ipcRenderer.invoke("settings:select-folder"),
  startDownload: (payload) => ipcRenderer.invoke("download:start", payload),
  getProgress: () => ipcRenderer.invoke("download:progress"),
  cancelDownload: () => ipcRenderer.invoke("download:cancel"),
  getHistory: () => ipcRenderer.invoke("history:get"),
  openFile: (filePath) => ipcRenderer.invoke("file:open", filePath),
  openFolder: (filePath) => ipcRenderer.invoke("folder:open", filePath)
});
