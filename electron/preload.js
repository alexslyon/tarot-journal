const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openFile: (options) => ipcRenderer.invoke('dialog:openFile', options),
  openDirectory: (options) => ipcRenderer.invoke('dialog:openDirectory', options),
  saveFile: (options) => ipcRenderer.invoke('dialog:saveFile', options),
  isElectron: true,
});
