/**
 * renderer-v2.js
 * Wires the JARVIS UI to the Python backend via window.jarvis (preload bridge).
 *
 * Flow:
 *   Start Listening btn → window.jarvis.startVoice()
 *     → Electron main.js sends __VOICE__ to Python stdin
 *     → Python voice_listener captures mic → transcribes → router.py routes
 *     → Python emits [TRANSCRIPTION], [ROUTER], [TASK STARTED/RUNNING/COMPLETE]
 *     → Electron main.js forwards each line to renderer via ipcRenderer
 *     → window.jarvis.onOutput fires → CommandRouter.parse() → UI update
 *
 * NO hardcoded demo triggers. All command execution happens in Python.
 */

(function () {
  'use strict';

  // ── DOM refs ──────────────────────────────────────────────────────────────

  const userText    = document.getElementById('user-text');
  const jarvisText  = document.getElementById('jarvis-text');
  const statusPill  = document.getElementById('status-pill');
  const micPill     = document.getElementById('mic-pill');
  const cmdCount    = document.getElementById('cmd-count');
  const startBtn    = document.getElementById('start-listening');
  const stopBtn     = document.getElementById('stop-listening');

  // ── State ─────────────────────────────────────────────────────────────────

  let commandsRun   = 0;
  let isListening   = false;
  let serverReady   = false;

  // ── Clock ─────────────────────────────────────────────────────────────────

  function updateClock() {
    const clocks = document.querySelectorAll('#main-clock');
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    clocks.forEach((el) => { el.textContent = `${hh}:${mm}`; });
  }
  updateClock();
  setInterval(updateClock, 30000);

  // ── UI helpers ────────────────────────────────────────────────────────────

  function setStatus(text, active) {
    if (statusPill) {
      statusPill.textContent = text;
      const card = statusPill.closest('.status-card');
      if (card) card.classList.toggle('active', !!active);
    }
  }

  function setMic(text, active) {
    if (micPill) {
      micPill.textContent = text;
      const card = micPill.closest('.status-card');
      if (card) card.classList.toggle('active', !!active);
    }
  }

  function showUserText(text) {
    if (!userText) return;
    userText.textContent = text;
    userText.classList.remove('placeholder');
    const box = userText.closest('.response-box');
    if (box) box.classList.add('active');
  }

  function showJarvisText(text) {
    if (!jarvisText) return;
    jarvisText.textContent = text;
    const box = jarvisText.closest('.response-box');
    if (box) box.classList.add('active');
  }

  function incrementCommands() {
    commandsRun++;
    if (cmdCount) cmdCount.textContent = commandsRun;
  }

  function setListeningState(listening) {
    isListening = listening;
    if (startBtn) startBtn.disabled = listening;
    if (stopBtn)  stopBtn.disabled  = !listening;
    setMic(listening ? 'LISTENING' : 'ACTIVE', listening);
  }

  // ── Python output handler ─────────────────────────────────────────────────

  function handlePyLine(line) {
    if (!line) return;

    console.log(`[PY→UI] ${line}`);

    const event = window.CommandRouter ? window.CommandRouter.parse(line) : null;

    if (!event) {
      // Raw log line — ignore in UI, already visible in DevTools console
      return;
    }

    switch (event.type) {

      case 'server_ready':
        serverReady = true;
        setStatus('READY', true);
        showJarvisText('JARVIS is online. Press Start Listening or type a command.');
        console.log('[RENDERER] Python server ready');
        break;

      case 'voice':
        setStatus('LISTENING', true);
        setListeningState(true);
        showJarvisText(event.message);
        console.log(`[VOICE] ${event.message}`);
        break;

      case 'transcription':
        // Real transcribed text from microphone
        showUserText(event.text);
        setStatus('PROCESSING', true);
        setListeningState(false);
        console.log(`[TRANSCRIPTION] ${event.text}`);
        break;

      case 'router':
        // Show which tool Python is routing to
        showJarvisText(`Routing: ${event.message}`);
        console.log(`[ROUTER] ${event.message}`);
        break;

      case 'task_started':
        setStatus('RUNNING', true);
        showJarvisText(`Starting: ${event.goal}`);
        console.log(`[TASK STARTED] ${event.goal}`);
        break;

      case 'task_running':
        setStatus('RUNNING', true);
        showJarvisText('Processing...');
        break;

      case 'task_complete':
        setStatus(event.success ? 'READY' : 'ERROR', event.success);
        setListeningState(false);
        incrementCommands();

        if (event.success) {
          // Trim to first 200 chars for display — full result in console
          const display = event.result.length > 200
            ? event.result.substring(0, 200) + '...'
            : event.result;
          showJarvisText(display);
        } else {
          showJarvisText(`Error: ${event.result}`);
        }

        console.log(`[TASK COMPLETE] [${event.success ? 'OK' : 'FAIL'}] [${event.tool}] ${event.result}`);
        break;
    }
  }

  // ── Button handlers ───────────────────────────────────────────────────────

  if (startBtn) {
    startBtn.addEventListener('click', () => {
      if (!window.jarvis) {
        showJarvisText('Error: Not running inside Electron. Use python main.py --voice instead.');
        return;
      }
      if (!serverReady) {
        showJarvisText('Python backend is still starting up. Please wait...');
        return;
      }
      if (isListening) return;

      console.log('[RENDERER] Start Listening clicked');
      setListeningState(true);
      setStatus('LISTENING', true);
      showJarvisText('Hold F9 and speak your command...');

      // Send __VOICE__ to Python — triggers one listen_ptt() cycle
      window.jarvis.startVoice();
    });
  }

  if (stopBtn) {
    stopBtn.addEventListener('click', () => {
      if (!window.jarvis) return;
      console.log('[RENDERER] Stop clicked');
      setListeningState(false);
      setStatus('READY', true);
      showJarvisText('Stopped. Press Start Listening to continue.');
      window.jarvis.stopVoice();
    });
  }

  // ── Text input (Enter key on any focused input) ───────────────────────────
  // Allows typing commands directly in the UI without voice

  document.addEventListener('keydown', (e) => {
    // Only handle if no input/textarea is focused (avoid double-firing)
    const tag = document.activeElement ? document.activeElement.tagName : '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;

    // Press T to open a quick text prompt
    if (e.key === 't' || e.key === 'T') {
      const goal = window.prompt('Enter command:');
      if (goal && goal.trim() && window.jarvis) {
        showUserText(goal.trim());
        setStatus('PROCESSING', true);

        // Log route before sending
        console.log(`[RENDERER] Sending goal: ${goal.trim()}`);
        window.jarvis.sendGoal(goal.trim());
      }
    }
  });

  // ── Register Python output listener ──────────────────────────────────────

  if (window.jarvis) {
    window.jarvis.onOutput(handlePyLine);
    console.log('[RENDERER] Listening for Python output via IPC');
  } else {
    // Running in a plain browser (not Electron) — show a warning
    console.warn('[RENDERER] window.jarvis not available. Run via: npm start');
    setStatus('NO BACKEND', false);
    showJarvisText('Open this app via "npm start" to connect to the Python backend.');
  }

  // ── Initial state ─────────────────────────────────────────────────────────

  setStatus('STARTING', false);
  setListeningState(false);
  showJarvisText('Connecting to Python backend...');

  console.log('[RENDERER] renderer-v2.js loaded');

})();
