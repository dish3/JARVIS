#!/usr/bin/env python3
"""
JARVIS Automation Tool - Desktop GUI Automation
Wraps pyautogui functions for mouse, keyboard, and screen control.
Used by the Orchestrator for desktop automation commands.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger('AUTOMATION_TOOL')


class AutomationTool:
    """Desktop automation via pyautogui.
    
    Provides mouse control, keyboard input, screenshots,
    and screen inspection capabilities.
    """
    
    def __init__(self):
        logger.info("Initializing Automation Tool...")
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
    
    def execute(self, parameters: Dict) -> Any:
        """Execute an automation action.
        
        Args:
            parameters: Dict with 'action' key and action-specific params.
            
        Returns:
            Result string or dict.
        """
        if not self._available:
            return "Automation unavailable — install pyautogui: pip install pyautogui"
        
        action = parameters.get('action', '')
        logger.info(f"[AUTOMATION] Executing: {action} with {parameters}")
        
        try:
            if action == 'click':
                return self._click(parameters)
            elif action == 'double_click':
                return self._double_click(parameters)
            elif action == 'right_click':
                return self._right_click(parameters)
            elif action == 'type':
                return self._type_text(parameters)
            elif action == 'press_key':
                return self._press_key(parameters)
            elif action == 'hotkey':
                return self._hotkey(parameters)
            elif action == 'screenshot':
                return self._screenshot(parameters)
            elif action == 'move_mouse':
                return self._move_mouse(parameters)
            elif action == 'get_mouse_position':
                return self._get_mouse_position()
            elif action == 'get_screen_size':
                return self._get_screen_size()
            elif action == 'scroll':
                return self._scroll(parameters)
            elif action == 'drag_drop':
                return self._drag_drop(parameters)
            elif action == 'locate_image':
                return self._locate_image(parameters)
            else:
                return f"Unknown automation action: {action}"
        except Exception as e:
            logger.error(f"[AUTOMATION] Error in {action}: {e}")
            return f"Automation error: {str(e)}"
    
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
        return f"Typed: {text}"
    
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
        import os
        filename = params.get('filename', 'screenshot.png')
        # Save to generated_images directory
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
