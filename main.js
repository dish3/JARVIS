/**
 * Electron Main Process — JARVIS
 * Spawns the Python backend (main.py) as a child process.
 * Bridges renderer ↔ Python via ipcMain / stdin-stdout.
 */

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');

let win = null;
let pyProcess = null;

// ── Python process ─────────────────────────────────────────────────────────────

function startPython() {
  const scriptPath = path.join(__dirname, 'main.py');

  // Use the venv python if it exists, otherwise fall back to system python
  const venvPython = path.join(__dirname, '.venv', 'Scripts', 'python.exe');
  const fs = require('fs');
  const pythonExe = fs.existsSync(venvPython) ? venvPython : 'python';

  console.log(`[ELECTRON] Starting Python: ${pythonExe} ${scriptPath}`);

  pyProcess = spawn(pythonExe, [scriptPath, '--text-server'], {
    cwd: __dirname,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' },
  });

  // ── stdout → renderer ──────────────────────────────────────────────────────
  pyProcess.stdout.on('data', (data) => {
    const lines = data.toString('utf8').split('\n');
    lines.forEach((line) => {
      line = line.trim();
      if (!line) return;
      console.log(`[PY] ${line}`);

      // Forward every line to renderer so it can parse status tags
      if (win && !win.isDestroyed()) {
        win.webContents.send('py-output', line);
      }
    });
  });

  pyProcess.stderr.on('data', (data) => {
    const text = data.toString('utf8').trim();
    if (text) console.error(`[PY ERR] ${text}`);
  });

  pyProcess.on('close', (code) => {
    console.log(`[ELECTRON] Python exited with code ${code}`);
    pyProcess = null;
  });
}

// ── IPC: renderer → Python ─────────────────────────────────────────────────────

// Text command from renderer
ipcMain.on('send-goal', (_event, goal) => {
  console.log(`[IPC] send-goal: ${goal}`);
  if (pyProcess && pyProcess.stdin.writable) {
    pyProcess.stdin.write(goal + '\n');
  } else {
    console.error('[IPC] Python process not running');
    if (win && !win.isDestroyed()) {
      win.webContents.send('py-output', '[TASK COMPLETE] [FAIL] Python backend not running');
    }
  }
});

// Voice trigger from renderer — tells Python to do one listen_ptt cycle
ipcMain.on('start-voice', (_event) => {
  console.log('[IPC] start-voice');
  if (pyProcess && pyProcess.stdin.writable) {
    pyProcess.stdin.write('__VOICE__\n');
  }
});

// Stop voice
ipcMain.on('stop-voice', (_event) => {
  console.log('[IPC] stop-voice');
  if (pyProcess && pyProcess.stdin.writable) {
    pyProcess.stdin.write('__STOP_VOICE__\n');
  }
});

// ── Window ─────────────────────────────────────────────────────────────────────

// Helpers for calculating live stats
function getCPUUsage() {
  const cpus = os.cpus();
  let user = 0, nice = 0, sys = 0, idle = 0, irq = 0;
  for (let cpu of cpus) {
    if (!cpu.times) continue;
    user += cpu.times.user;
    nice += cpu.times.nice;
    sys += cpu.times.sys;
    idle += cpu.times.idle;
    irq += cpu.times.irq;
  }
  const total = user + nice + sys + idle + irq;
  return { idle, total };
}

let startCPU = getCPUUsage();

function calculateCPUPercentage() {
  const endCPU = getCPUUsage();
  const idleDifference = endCPU.idle - startCPU.idle;
  const totalDifference = endCPU.total - startCPU.total;
  startCPU = endCPU;
  
  if (totalDifference === 0) return 0;
  return Math.min(100, Math.max(0, Math.floor(100 - (100 * idleDifference / totalDifference))));
}

function getRAMStats() {
  const totalMem = os.totalmem();
  const freeMem = os.freemem();
  const usedMem = totalMem - freeMem;
  const percentage = Math.floor((usedMem / totalMem) * 100);
  const totalGB = (totalMem / (1024 ** 3)).toFixed(1);
  const usedGB = (usedMem / (1024 ** 3)).toFixed(1);
  return { percentage, usedGB, totalGB };
}

function createWindow() {
  win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'JARVIS',
    backgroundColor: '#f5f7fa',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  win.loadFile('index.html');

  // Start polling system metrics every 2 seconds
  const statsInterval = setInterval(() => {
    if (win && !win.webContents.isDestroyed()) {
      const cpu = calculateCPUPercentage();
      const ram = getRAMStats();
      win.webContents.send('sys-stats', { cpu, ram });
    }
  }, 2000);

  win.on('closed', () => {
    win = null;
    clearInterval(statsInterval);
  });
}

// ── App lifecycle ──────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  startPython();
  createWindow();
});

app.on('window-all-closed', () => {
  if (pyProcess) {
    pyProcess.stdin.end();
    pyProcess.kill();
  }
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
