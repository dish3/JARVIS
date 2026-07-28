/**
 * Electron Preload — exposes a safe bridge between renderer and main process.
 * contextIsolation: true means renderer cannot access Node directly.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jarvis', {
  // Send a text goal to Python
  sendGoal: (goal) => ipcRenderer.send('send-goal', goal),

  // Trigger one voice listen cycle
  startVoice: () => ipcRenderer.send('start-voice'),

  // Stop voice
  stopVoice: () => ipcRenderer.send('stop-voice'),

  // Listen for lines coming back from Python stdout
  onOutput: (callback) => ipcRenderer.on('py-output', (_event, line) => callback(line)),

  // Listen for live system stats
  onStats: (callback) => ipcRenderer.on('sys-stats', (_event, stats) => callback(stats)),

  // Remove all output listeners (cleanup)
  removeOutputListeners: () => {
    ipcRenderer.removeAllListeners('py-output');
    ipcRenderer.removeAllListeners('sys-stats');
  },
});
