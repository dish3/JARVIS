#!/usr/bin/env python3
"""
JARVIS Automation Tool - Desktop GUI Automation
Wraps pyautogui functions for mouse, keyboard, and screen control with safety limits.
"""

import logging
import os
from typing import Dict, Any

logger = logging.getLogger('AUTOMATION_TOOL')


class AutomationTool:
    """Desktop automation via pyautogui with strict safety rules."""
    
    def __init__(self):
        logger.info("Initializing Automation Tool...")
        self.logs = []
        self.screenshots = []
        try:
            import pyautogui
            pyautogui.FAILSAFE = True   # Keep failsafe ON for safety
            pyautogui.PAUSE = 0.1
            self._pyautogui = pyautogui
            self._available = True
            logger.info("[OK] Automation Tool initialized")
        except ImportError:
            self._available = False
            self._pyautogui = None
            logger.warning("[WARN] pyautogui not installed — automation disabled")
            
    def _log(self, msg: str):
        logger.info(msg)
        self.logs.append(msg)

    def _make_result(self, status: str, result_val: Any, state: str = "") -> Dict[str, Any]:
        return {
            "status": status,
            "logs": list(self.logs),
            "screenshots": list(self.screenshots),
            "state": state,
            "result": {"message": result_val} if isinstance(result_val, str) else result_val
        }

    def _is_destructive_action(self, action: str, params: Dict) -> bool:
        """Detect potentially destructive keyboard operations."""
        if action == 'hotkey':
            keys = params.get('keys', [])
            if isinstance(keys, str):
                keys = [k.strip().lower() for k in keys.split('+')]
            else:
                keys = [str(k).lower() for k in keys]
            
            # Block Alt+F4, Ctrl+W, Shift+Delete
            if 'alt' in keys and 'f4' in keys:
                return True
            if 'ctrl' in keys and 'w' in keys:
                return True
            if 'shift' in keys and 'delete' in keys:
                return True
        elif action == 'press_key':
            key = str(params.get('key', '')).lower()
            if key in ('delete', 'backspace'):
                return True
        return False

    def _log_coordinates(self, action: str, params: Dict):
        """Log mouse operation coordinates."""
        if action in ('click', 'double_click', 'right_click', 'move_mouse'):
            x = params.get('x', 0)
            y = params.get('y', 0)
            self._log(f"[AUTOMATION] Mouse action coordinates: X={x}, Y={y}")
        elif action == 'drag_drop':
            x1 = params.get('x1', 0)
            y1 = params.get('y1', 0)
            x2 = params.get('x2', 0)
            y2 = params.get('y2', 0)
            self._log(f"[AUTOMATION] Drag coordinates: From ({x1}, {y1}) to ({x2}, {y2})")

    def _verify_screenshot(self, params: Dict) -> Dict[str, Any]:
        """Verify screenshot file is correctly created on disk."""
        filename = params.get('filename', 'screenshot.png')
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated_images')
        filepath = os.path.join(save_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            if size > 0:
                self._log(f"[VERIFY] Screenshot verified: file exists, size={size} bytes")
                self.screenshots.append(filepath)
                return {"success": True}
            else:
                return {"success": False, "error": "Screenshot file is empty (0 bytes)."}
        return {"success": False, "error": "Screenshot file does not exist on disk."}
    
    def execute(self, parameters: Dict) -> Dict[str, Any]:
        self.logs = []
        self.screenshots = []

        if not self._available:
            self._log("Automation unavailable — pyautogui is not installed.")
            return self._make_result("failed", "pyautogui not installed")
        
        action = parameters.get('action', '')
        self._log(f"[AUTOMATION] Executing: {action} with params: {parameters}")
        
        # 1. Dry Run simulation
        if parameters.get('dry_run', False):
            self._log(f"[DRY-RUN] Simulating action: {action}")
            return self._make_result("success", f"Dry-run simulated: {action} successfully")
            
        # 2. Destructive safety check
        if self._is_destructive_action(action, parameters) and not parameters.get('confirm', False):
            self._log(f"[SAFETY] Destructive action blocked: {action}. Set 'confirm': true to run.")
            return self._make_result("failed", "Destructive action blocked. Please set 'confirm': true to execute.")

        # 3. Active Window Verification
        target_win = parameters.get('target_window')
        if target_win:
            active_win = self._pyautogui.getActiveWindowTitle() or ""
            self._log(f"[SAFETY] Verifying active window. Expected: '{target_win}', Active: '{active_win}'")
            if target_win.lower() not in active_win.lower():
                self._log(f"[SAFETY] Abort: Active window '{active_win}' does not match expected '{target_win}'")
                return self._make_result("failed", f"Active window verification failed: '{active_win}'")

        # 4. Emergency stop reminder
        self._log("[SAFETY] Emergency Stop: slam mouse cursor into any corner of the screen to trigger Failsafe.")

        # 5. Coordinate logging
        self._log_coordinates(action, parameters)
        
        try:
            if action == 'click':
                res = self._click(parameters)
            elif action == 'double_click':
                res = self._double_click(parameters)
            elif action == 'right_click':
                res = self._right_click(parameters)
            elif action == 'type':
                res = self._type_text(parameters)
            elif action == 'press_key':
                res = self._press_key(parameters)
            elif action == 'hotkey':
                res = self._hotkey(parameters)
            elif action == 'screenshot':
                res = self._screenshot(parameters)
                verify_res = self._verify_screenshot(parameters)
                if not verify_res["success"]:
                    return self._make_result("failed", verify_res["error"])
            elif action == 'move_mouse':
                res = self._move_mouse(parameters)
            elif action == 'get_mouse_position':
                res = self._get_mouse_position()
            elif action == 'get_screen_size':
                res = self._get_screen_size()
            elif action == 'scroll':
                res = self._scroll(parameters)
            elif action == 'drag_drop':
                res = self._drag_drop(parameters)
            elif action == 'locate_image':
                res = self._locate_image(parameters)
            else:
                res = f"Unknown automation action: {action}"
                return self._make_result("failed", res)
                
            return self._make_result("success", res)
            
        except Exception as e:
            self._log(f"[ERROR] Error in {action}: {e}")
            return self._make_result("failed", f"Automation error: {str(e)}")
    
    # ── Actions ────────────────────────────────────────────────────────────────
    
    def _click(self, params: Dict) -> str:
        x = params.get('x', 0)
        y = params.get('y', 0)
        button = params.get('button', 'left')
        self._pyautogui.click(x, y, button=button)
        return f"Clicked at ({x}, {y}) with {button} button"
    
    def _double_click(self, params: Dict) -> str:
        x = params.get('x', 0)
        y = params.get('y', 0)
        self._pyautogui.doubleClick(x, y)
        return f"Double-clicked at ({x}, {y})"
    
    def _right_click(self, params: Dict) -> str:
        x = params.get('x', 0)
        y = params.get('y', 0)
        self._pyautogui.rightClick(x, y)
        return f"Right-clicked at ({x}, {y})"
    
    def _type_text(self, params: Dict) -> str:
        text = params.get('text', '')
        delay = params.get('delay', 50) / 1000.0
        self._pyautogui.typewrite(text, interval=delay)
        return f"Typed text"
    
    def _press_key(self, params: Dict) -> str:
        key = params.get('key', 'enter')
        self._pyautogui.press(key)
        return f"Pressed key: {key}"
    
    def _hotkey(self, params: Dict) -> str:
        keys = params.get('keys', [])
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.split('+')]
        self._pyautogui.hotkey(*keys)
        return f"Pressed hotkey: {'+'.join(keys)}"
    
    def _screenshot(self, params: Dict) -> str:
        filename = params.get('filename', 'screenshot.png')
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generated_images')
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)
        img = self._pyautogui.screenshot()
        img.save(filepath)
        return f"Screenshot saved: {filepath}"
    
    def _move_mouse(self, params: Dict) -> str:
        x = params.get('x', 0)
        y = params.get('y', 0)
        self._pyautogui.moveTo(x, y)
        return f"Mouse moved to ({x}, {y})"
    
    def _get_mouse_position(self) -> str:
        x, y = self._pyautogui.position()
        return f"Mouse position: ({x}, {y})"
    
    def _get_screen_size(self) -> str:
        width, height = self._pyautogui.size()
        return f"Screen size: {width}x{height}"
    
    def _scroll(self, params: Dict) -> str:
        clicks = params.get('clicks', 5)
        x = params.get('x', None)
        y = params.get('y', None)
        if x is not None and y is not None:
            self._pyautogui.moveTo(x, y)
        self._pyautogui.scroll(clicks)
        direction = 'up' if clicks > 0 else 'down'
        return f"Scrolled {direction} {abs(clicks)} clicks"
    
    def _drag_drop(self, params: Dict) -> str:
        x1 = params.get('x1', 0)
        y1 = params.get('y1', 0)
        x2 = params.get('x2', 0)
        y2 = params.get('y2', 0)
        self._pyautogui.moveTo(x1, y1)
        self._pyautogui.drag(x2 - x1, y2 - y1)
        return f"Dragged from ({x1}, {y1}) to ({x2}, {y2})"
    
    def _locate_image(self, params: Dict) -> str:
        image_path = params.get('image_path', '')
        location = self._pyautogui.locateOnScreen(image_path)
        if location:
            return f"Image found at: ({location[0]}, {location[1]})"
        return "Image not found on screen"
