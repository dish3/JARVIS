/**
 * command-router-v2.js
 * Frontend command router — parses Python stdout lines and dispatches
 * UI updates. All actual routing happens in Python (router.py).
 * This file only handles display logic.
 */

window.CommandRouter = {
  /**
   * Parse a raw stdout line from Python and return a structured event.
   * Returns null if the line is not a recognised status tag.
   */
  parse(line) {
    if (line.startsWith('[TASK STARTED]')) {
      return { type: 'task_started', goal: line.replace('[TASK STARTED]', '').trim() };
    }
    if (line.startsWith('[TASK RUNNING]')) {
      return { type: 'task_running', goal: line.replace('[TASK RUNNING]', '').trim() };
    }
    if (line.startsWith('[TASK COMPLETE]')) {
      const body = line.replace('[TASK COMPLETE]', '').trim();
      // Format: [OK] [tool] result text
      const statusMatch = body.match(/^\[(OK|FAIL)\]\s*\[([^\]]+)\]\s*(.*)/s);
      if (statusMatch) {
        return {
          type: 'task_complete',
          success: statusMatch[1] === 'OK',
          tool: statusMatch[2],
          result: statusMatch[3].trim(),
        };
      }
      return { type: 'task_complete', success: false, tool: 'unknown', result: body };
    }
    if (line.startsWith('[VOICE]')) {
      return { type: 'voice', message: line.replace('[VOICE]', '').trim() };
    }
    if (line.startsWith('[TRANSCRIPTION]')) {
      return { type: 'transcription', text: line.replace('[TRANSCRIPTION]', '').trim() };
    }
    if (line.startsWith('[ROUTER]')) {
      return { type: 'router', message: line.replace('[ROUTER]', '').trim() };
    }
    if (line.startsWith('[JARVIS SERVER]')) {
      return { type: 'server_ready', message: line.replace('[JARVIS SERVER]', '').trim() };
    }
    return null;
  },
};
