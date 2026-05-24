#!/usr/bin/env python3
"""
Application Automation Backend for JARVIS
Handles mouse, keyboard, and screen automation
"""

import sys
import json
import time
import pyautogui
from PIL import Image
import io

# Disable pyautogui safety features for faster execution
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

def type_text(args):
    """Type text in active window"""
    text = args.get('text', '')
    delay = args.get('delay', 50) / 1000.0  # Convert ms to seconds
    
    try:
        pyautogui.typewrite(text, interval=delay)
        return {'success': True, 'message': f'Typed: {text}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def click(args):
    """Click at coordinates"""
    x = args.get('x', 0)
    y = args.get('y', 0)
    button = args.get('button', 'left')
    
    try:
        pyautogui.click(x, y, button=button)
        return {'success': True, 'message': f'Clicked at ({x}, {y})'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def move_mouse(args):
    """Move mouse to coordinates"""
    x = args.get('x', 0)
    y = args.get('y', 0)
    
    try:
        pyautogui.moveTo(x, y)
        return {'success': True, 'message': f'Moved to ({x}, {y})'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def press_key(args):
    """Press a key"""
    key = args.get('key', 'enter')
    
    try:
        pyautogui.press(key)
        return {'success': True, 'message': f'Pressed: {key}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def hotkey(args):
    """Press keyboard shortcut"""
    keys = args.get('keys', [])
    
    try:
        pyautogui.hotkey(*keys)
        return {'success': True, 'message': f'Hotkey: {"+".join(keys)}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_mouse_position(args):
    """Get current mouse position"""
    try:
        x, y = pyautogui.position()
        return {'success': True, 'x': x, 'y': y}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_screen_size(args):
    """Get screen dimensions"""
    try:
        width, height = pyautogui.size()
        return {'success': True, 'width': width, 'height': height}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def screenshot(args):
    """Take screenshot"""
    filename = args.get('filename', 'screenshot.png')
    
    try:
        img = pyautogui.screenshot()
        img.save(filename)
        return {'success': True, 'message': f'Screenshot saved: {filename}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def locate_image(args):
    """Find image on screen"""
    image_path = args.get('image_path', '')
    
    try:
        location = pyautogui.locateOnScreen(image_path)
        if location:
            return {'success': True, 'x': location[0], 'y': location[1]}
        else:
            return {'success': False, 'error': 'Image not found on screen'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def scroll(args):
    """Scroll at coordinates"""
    x = args.get('x', 0)
    y = args.get('y', 0)
    clicks = args.get('clicks', 5)
    
    try:
        pyautogui.moveTo(x, y)
        pyautogui.scroll(clicks)
        return {'success': True, 'message': f'Scrolled {clicks} clicks'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def double_click(args):
    """Double click at coordinates"""
    x = args.get('x', 0)
    y = args.get('y', 0)
    
    try:
        pyautogui.doubleClick(x, y)
        return {'success': True, 'message': f'Double clicked at ({x}, {y})'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def right_click(args):
    """Right click at coordinates"""
    x = args.get('x', 0)
    y = args.get('y', 0)
    
    try:
        pyautogui.rightClick(x, y)
        return {'success': True, 'message': f'Right clicked at ({x}, {y})'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def drag_drop(args):
    """Drag and drop"""
    x1 = args.get('x1', 0)
    y1 = args.get('y1', 0)
    x2 = args.get('x2', 0)
    y2 = args.get('y2', 0)
    
    try:
        pyautogui.moveTo(x1, y1)
        pyautogui.drag(x2 - x1, y2 - y1)
        return {'success': True, 'message': f'Dragged from ({x1}, {y1}) to ({x2}, {y2})'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Command dispatcher
COMMANDS = {
    'type': type_text,
    'click': click,
    'move_mouse': move_mouse,
    'press_key': press_key,
    'hotkey': hotkey,
    'get_mouse_position': get_mouse_position,
    'get_screen_size': get_screen_size,
    'screenshot': screenshot,
    'locate_image': locate_image,
    'scroll': scroll,
    'double_click': double_click,
    'right_click': right_click,
    'drag_drop': drag_drop,
}

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'success': False, 'error': 'No command provided'}))
        return
    
    command = sys.argv[1]
    args = {}
    
    if len(sys.argv) > 2:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            pass
    
    if command not in COMMANDS:
        print(json.dumps({'success': False, 'error': f'Unknown command: {command}'}))
        return
    
    result = COMMANDS[command](args)
    print(json.dumps(result))

if __name__ == '__main__':
    main()
