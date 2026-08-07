#!/usr/bin/env python3
"""
JARVIS Voice Audio Capture
Microphone enumeration, virtual device warning/override, and recording setup.
"""

import sys
import logging

logger = logging.getLogger('VOICE.CAPTURE')

VIRTUAL_KEYWORDS = [
    "voicemod", "vb-cable", "vb-audio", "cable", "virtual", 
    "steam", "nvidia", "obs", "mapper", "stereo mix", "stereomix"
]

def list_input_devices() -> list:
    """
    Query and return a list of all available input devices.
    """
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = []
        for idx, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                name = dev['name']
                is_virtual = any(kw in name.lower() for kw in VIRTUAL_KEYWORDS)
                input_devices.append({
                    'index': idx,
                    'name': name,
                    'channels': dev['max_input_channels'],
                    'sample_rate': dev['default_samplerate'],
                    'is_virtual': is_virtual
                })
        return input_devices
    except Exception as e:
        logger.error(f"[VOICE] Error querying sound devices: {e}")
        return []

def select_mic_device() -> int | None:
    """
    Selects a microphone device, prints the list of available devices,
    flags virtual devices, and prompts the user interactively (Y/N / manual index) if virtual
    mics exist and sys.stdin is a TTY.
    
    Returns:
        The selected device index or None (sounddevice default).
    """
    devices = list_input_devices()
    if not devices:
        logger.warning("[VOICE] Microphone detected: None found!")
        return None
        
    try:
        import sounddevice as sd
        default_input_idx = sd.default.device[0]
    except Exception as e:
        logger.error(f"[VOICE] Error getting default sounddevice: {e}")
        default_input_idx = -1

    logger.info("[VOICE] Microphone detected: Listing all available input devices:")
    print("=" * 60)
    print("                 AVAILABLE INPUT DEVICES                 ")
    print("=" * 60)
    
    virtual_found = False
    physical_devices = []
    
    for dev in devices:
        idx = dev['index']
        name = dev['name']
        is_virtual = dev['is_virtual']
        
        marker = ""
        if idx == default_input_idx:
            marker += " [SYSTEM DEFAULT]"
        if is_virtual:
            marker += " [VIRTUAL]"
            virtual_found = True
        else:
            physical_devices.append(dev)
            
        print(f" [{idx}]: {name} (channels={dev['channels']}, rate={dev['sample_rate']}Hz){marker}")
    print("=" * 60)

    # 1. Determine automatic fallback (prefer system default if physical)
    selected_idx = None
    if default_input_idx >= 0:
        default_is_virtual = any(d['index'] == default_input_idx and d['is_virtual'] for d in devices)
        if not default_is_virtual:
            selected_idx = default_input_idx

    # 2. Pick first physical device matching 'mic' or 'microphone'
    if selected_idx is None and physical_devices:
        for dev in physical_devices:
            if 'microphone' in dev['name'].lower() or 'mic' in dev['name'].lower():
                selected_idx = dev['index']
                break
        if selected_idx is None:
            selected_idx = physical_devices[0]['index']

    # 3. Last fallback
    if selected_idx is None:
        selected_idx = default_input_idx if default_input_idx >= 0 else devices[0]['index']

    # 4. Check if the auto-selected device is virtual
    is_selected_virtual = any(d['index'] == selected_idx and d['is_virtual'] for d in devices)

    if virtual_found or is_selected_virtual:
        logger.warning("[VOICE] Virtual microphone(s) detected in the system configuration.")
        print("[WARNING] Virtual audio device(s) or Voicemod detected. Virtual devices can cause silent/corrupted recordings.")
        
        if sys.stdin.isatty():
            print(f"JARVIS automatically selected device [{selected_idx}]: "
                  f"{[d['name'] for d in devices if d['index'] == selected_idx][0]}")
                  
            # Check if user wants to continue or override
            if is_selected_virtual:
                while True:
                    ans = input("WARNING: Selected device is VIRTUAL. Continue? (Y/N): ").strip().lower()
                    if ans in ('y', 'yes'):
                        break
                    elif ans in ('n', 'no'):
                        # Ask for override index
                        override = input("Enter a different device index to use: ").strip()
                        try:
                            o_idx = int(override)
                            if any(d['index'] == o_idx for d in devices):
                                selected_idx = o_idx
                                is_selected_virtual = any(d['index'] == selected_idx and d['is_virtual'] for d in devices)
                                break
                            else:
                                print("[ERROR] Invalid device index. Try again.")
                        except ValueError:
                            print("[ERROR] Index must be an integer.")
            else:
                override = input(f"Enter a different index to override, or press Enter to continue with default [{selected_idx}]: ").strip()
                if override:
                    try:
                        o_idx = int(override)
                        if any(d['index'] == o_idx for d in devices):
                            selected_idx = o_idx
                    except ValueError:
                        print(f"[ERROR] Invalid input. Sticking with default [{selected_idx}].")
        else:
            logger.info(f"[VOICE] Running in non-interactive environment. Automatically selecting safe device [{selected_idx}] to avoid virtual mic issues.")

    # Get details of chosen device
    chosen_dev = [d for d in devices if d['index'] == selected_idx][0]
    logger.info(f"[VOICE] Selected device: [{chosen_dev['index']}] {chosen_dev['name']}")
    logger.info(f"[VOICE] Sample rate: {chosen_dev['sample_rate']} Hz")
    logger.info(f"[VOICE] Channels: {chosen_dev['channels']}")
    return selected_idx
