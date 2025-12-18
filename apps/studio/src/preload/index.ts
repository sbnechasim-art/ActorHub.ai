/**
 * ActorHub Studio - Preload Script
 */
import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'

const api = {
  // File dialogs
  openFile: (options?: { filters?: Electron.FileFilter[] }) =>
    ipcRenderer.invoke('dialog:openFile', options),

  openMultiple: (options?: { filters?: Electron.FileFilter[] }) =>
    ipcRenderer.invoke('dialog:openMultiple', options),

  saveFile: (options?: { defaultPath?: string; filters?: Electron.FileFilter[] }) =>
    ipcRenderer.invoke('dialog:saveFile', options),

  // App info
  getVersion: () => ipcRenderer.invoke('app:version'),

  // Training progress
  onTrainingProgress: (callback: (progress: number, step: string) => void) => {
    ipcRenderer.on('training:progress', (_, progress, step) => callback(progress, step))
    return () => ipcRenderer.removeAllListeners('training:progress')
  },

  onTrainingComplete: (callback: (result: any) => void) => {
    ipcRenderer.on('training:complete', (_, result) => callback(result))
    return () => ipcRenderer.removeAllListeners('training:complete')
  },

  onTrainingError: (callback: (error: string) => void) => {
    ipcRenderer.on('training:error', (_, error) => callback(error))
    return () => ipcRenderer.removeAllListeners('training:error')
  },
}

if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore
  window.electron = electronAPI
  // @ts-ignore
  window.api = api
}
