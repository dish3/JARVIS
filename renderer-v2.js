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

  const chatContainer     = document.getElementById('chat-container');
  const commandTextInput  = document.getElementById('command-text-input');
  const sendCommandBtn    = document.getElementById('send-command-btn');
  const cpuVal            = document.getElementById('cpu-val');
  const ramVal            = document.getElementById('ram-val');
  const statusPill        = document.getElementById('status-pill');
  const micPill           = document.getElementById('mic-pill');
  const cmdCount          = document.getElementById('cmd-count');
  const startBtn          = document.getElementById('start-listening');
  const stopBtn           = document.getElementById('stop-listening');

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

  function escapeHTML(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatMarkdown(text) {
    const parts = text.split('```');
    return parts.map((part, index) => {
      if (index % 2 === 1) {
        const firstNewline = part.indexOf('\n');
        let code = part;
        if (firstNewline !== -1) {
          code = part.substring(firstNewline + 1);
        }
        return `<pre><code>${escapeHTML(code.trim())}</code></pre>`;
      } else {
        let formatted = escapeHTML(part);
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        formatted = formatted.replace(/\n/g, '<br>');
        return formatted;
      }
    }).join('');
  }

  function appendChatMessage(sender, text) {
    if (!chatContainer || !text) return;
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${sender}-message`;
    
    const senderDiv = document.createElement('div');
    senderDiv.className = 'message-sender';
    senderDiv.textContent = sender.toUpperCase();
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = sender === 'system' ? text : formatMarkdown(text);
    
    msgDiv.appendChild(senderDiv);
    msgDiv.appendChild(contentDiv);
    chatContainer.appendChild(msgDiv);
    
    // Auto scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
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
        appendChatMessage('jarvis', 'JARVIS is online. Press Start Listening or type a command.');
        console.log('[RENDERER] Python server ready');
        break;

      case 'voice':
        setStatus('LISTENING', true);
        setListeningState(true);
        appendChatMessage('system', `Voice status: ${event.message}`);
        console.log(`[VOICE] ${event.message}`);
        break;

      case 'transcription':
        // Real transcribed text from microphone
        appendChatMessage('user', event.text);
        setStatus('PROCESSING', true);
        setListeningState(false);
        console.log(`[TRANSCRIPTION] ${event.text}`);
        break;

      case 'router':
        appendChatMessage('system', `Routing directive: ${event.message}`);
        console.log(`[ROUTER] ${event.message}`);
        break;

      case 'task_started':
        setStatus('RUNNING', true);
        appendChatMessage('system', `Executing: ${event.goal}`);
        console.log(`[TASK STARTED] ${event.goal}`);
        break;

      case 'task_running':
        setStatus('RUNNING', true);
        break;

      case 'task_complete':
        setStatus(event.success ? 'READY' : 'ERROR', event.success);
        setListeningState(false);
        incrementCommands();

        if (event.success) {
          appendChatMessage('jarvis', event.result);
        } else {
          appendChatMessage('system', `Execution Error: ${event.result}`);
        }

        console.log(`[TASK COMPLETE] [${event.success ? 'OK' : 'FAIL'}] [${event.tool}] ${event.result}`);
        break;
    }
  }

  // ── Text Command Submission ────────────────────────────────────────────────

  function submitTextCommand() {
    if (!commandTextInput) return;
    const goal = commandTextInput.value.trim();
    if (!goal) return;

    if (!window.jarvis) {
      appendChatMessage('system', 'Error: Not running inside Electron. Use python main.py instead.');
      return;
    }

    if (!serverReady) {
      appendChatMessage('system', 'Python backend is still starting up. Please wait...');
      return;
    }

    // Append user message locally
    appendChatMessage('user', goal);
    commandTextInput.value = '';

    setStatus('PROCESSING', true);
    console.log(`[RENDERER] Sending goal: ${goal}`);
    window.jarvis.sendGoal(goal);
  }

  if (sendCommandBtn) {
    sendCommandBtn.addEventListener('click', submitTextCommand);
  }

  if (commandTextInput) {
    commandTextInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        submitTextCommand();
      }
    });
  }

  // ── Button handlers ───────────────────────────────────────────────────────

  if (startBtn) {
    startBtn.addEventListener('click', () => {
      if (!window.jarvis) {
        appendChatMessage('system', 'Error: Not running inside Electron. Use python main.py --voice instead.');
        return;
      }
      if (!serverReady) {
        appendChatMessage('system', 'Python backend is still starting up. Please wait...');
        return;
      }
      if (isListening) return;

      console.log('[RENDERER] Start Listening clicked');
      setListeningState(true);
      setStatus('LISTENING', true);
      appendChatMessage('system', 'Listening... speak your command now.');

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
      appendChatMessage('system', 'Stopped. Ready for new command.');
      window.jarvis.stopVoice();
    });
  }

  // ── Keyboard shortcuts ─────────────────────────────────────────────────────

  document.addEventListener('keydown', (e) => {
    const tag = document.activeElement ? document.activeElement.tagName : '';
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;

    // Focus command text input on any alphanumeric keypress
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      if (commandTextInput) {
        commandTextInput.focus();
      }
    }
  });

  // ── Register Python listeners & Stats ──────────────────────────────────────

  if (window.jarvis) {
    window.jarvis.onOutput(handlePyLine);
    console.log('[RENDERER] Listening for Python output via IPC');

    // Handle incoming system metrics
    window.jarvis.onStats((stats) => {
      if (cpuVal) {
        cpuVal.textContent = `${stats.cpu}%`;
        const card = cpuVal.closest('.status-card');
        if (card) card.classList.toggle('active', stats.cpu > 10);
      }
      if (ramVal) {
        ramVal.textContent = `${stats.ram.percentage}% (${stats.ram.usedGB}/${stats.ram.totalGB} GB)`;
        const card = ramVal.closest('.status-card');
        if (card) card.classList.toggle('active', true);
      }
    });
    console.log('[RENDERER] Listening for system metrics via IPC');
  } else {
    console.warn('[RENDERER] window.jarvis not available. Run via: npm start');
    setStatus('NO BACKEND', false);
    appendChatMessage('system', 'Open this app via "npm start" to connect to the Python backend.');
  }

  // ── Initial state ─────────────────────────────────────────────────────────

  setStatus('STARTING', false);
  setListeningState(false);
  appendChatMessage('system', 'Connecting to Python backend...');

  console.log('[RENDERER] renderer-v2.js loaded');

})();
