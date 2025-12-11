import win32api
import win32con
import win32gui
import threading
import time
import queue
from capture import capture_fullscreen, capture_region, RegionSelector, save_screenshot
from editor import edit_image
from config import Config
from settings import settings_manager

# Queue for communicating with main thread
action_queue = queue.Queue()


def parse_hotkey(hotkey_str):
    """
    Parse hotkey string like 'Alt+S' or 'Ctrl+Shift+F9' into (modifier, vk_code)
    Returns None if invalid or empty
    """
    if not hotkey_str or hotkey_str == "(disabled)":
        return None
        
    parts = hotkey_str.split('+')
    if not parts:
        return None
        
    modifier = 0
    key = None
    
    for part in parts:
        part = part.strip()
        part_upper = part.upper()
        
        if part_upper == 'CTRL':
            modifier |= win32con.MOD_CONTROL
        elif part_upper == 'ALT':
            modifier |= win32con.MOD_ALT
        elif part_upper == 'SHIFT':
            modifier |= win32con.MOD_SHIFT
        else:
            # This is the key
            key = part_upper
    
    if not key:
        return None
        
    # Convert key to virtual key code
    vk_code = get_vk_code(key)
    if vk_code is None:
        return None
        
    return (modifier, vk_code)


def get_vk_code(key):
    """Convert key name to virtual key code"""
    # Single letters
    if len(key) == 1 and key.isalpha():
        return ord(key.upper())
    
    # Single digits
    if len(key) == 1 and key.isdigit():
        return ord(key)
    
    # Function keys
    if key.startswith('F') and key[1:].isdigit():
        num = int(key[1:])
        if 1 <= num <= 24:
            return win32con.VK_F1 + num - 1
    
    # Special keys
    special_keys = {
        'SPACE': win32con.VK_SPACE,
        'ENTER': win32con.VK_RETURN,
        'RETURN': win32con.VK_RETURN,
        'TAB': win32con.VK_TAB,
        'BACKSPACE': win32con.VK_BACK,
        'DELETE': win32con.VK_DELETE,
        'INSERT': win32con.VK_INSERT,
        'HOME': win32con.VK_HOME,
        'END': win32con.VK_END,
        'PAGEUP': win32con.VK_PRIOR,
        'PAGEDOWN': win32con.VK_NEXT,
        'UP': win32con.VK_UP,
        'DOWN': win32con.VK_DOWN,
        'LEFT': win32con.VK_LEFT,
        'RIGHT': win32con.VK_RIGHT,
        'PRINTSCREEN': win32con.VK_PRINT,
        'SCROLLLOCK': win32con.VK_SCROLL,
        'PAUSE': win32con.VK_PAUSE,
        'NUMLOCK': win32con.VK_NUMLOCK,
        'CAPSLOCK': win32con.VK_CAPITAL,
        'ESCAPE': win32con.VK_ESCAPE,
        'ESC': win32con.VK_ESCAPE,
    }
    
    return special_keys.get(key.upper())


class HotkeyThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.registered_hotkeys = []
        
    def run(self):
        # Load hotkeys from settings
        hotkey_configs = [
            (1, settings_manager.get('hotkey_fullscreen', 'Alt+S'), "Fullscreen", 'fullscreen'),
            (2, settings_manager.get('hotkey_region', 'Alt+R'), "Region", 'region'),
            (3, settings_manager.get('hotkey_settings', 'Ctrl+P'), "Settings", 'settings'),
        ]
        
        print("\nRegistering hotkeys...")
        
        for hotkey_id, hotkey_str, name, action in hotkey_configs:
            if not hotkey_str:
                print(f"  ⚫ {name} - disabled")
                continue
                
            parsed = parse_hotkey(hotkey_str)
            if not parsed:
                print(f"  ✗ {name} ({hotkey_str}) - invalid hotkey")
                continue
                
            modifier, vk_code = parsed
            
            try:
                win32gui.RegisterHotKey(None, hotkey_id, modifier, vk_code)
                self.registered_hotkeys.append((hotkey_id, hotkey_str, action))
                print(f"  ✓ {name}: {hotkey_str}")
            except Exception as e:
                print(f"  ✗ {name} ({hotkey_str}) - already in use or error")
        
        if not self.registered_hotkeys:
            print("\n❌ ERROR: No hotkeys could be registered!")
            print("Check your settings or close conflicting programs.")
            return
            
        print(f"\n✓ {len(self.registered_hotkeys)} hotkey(s) ready!\n")
        
        try:
            msg = win32gui.GetMessage(None, 0, 0)
            while msg:
                if msg[1][1] == win32con.WM_HOTKEY:
                    hotkey_id = msg[1][2]
                    
                    # Find which action this hotkey triggers
                    for reg_id, hotkey_str, action in self.registered_hotkeys:
                        if reg_id == hotkey_id:
                            # Put action in queue for main thread to handle
                            action_queue.put(action)
                            break
                        
                msg = win32gui.GetMessage(None, 0, 0)
        finally:
            for hotkey_id, hotkey_str, action in self.registered_hotkeys:
                win32gui.UnregisterHotKey(None, hotkey_id)


def take_screenshot_fullscreen():
    print("📸 Capturing full screen...")
    img = capture_fullscreen()
    
    edited_img = edit_image(img)
    
    if edited_img:
        filepath = save_screenshot(edited_img)
        print(f"✓ Saved: {filepath}")
    else:
        print("❌ Cancelled")


def take_screenshot_region():
    print("🎯 Select region (Escape to cancel)...")
    time.sleep(0.2)
    
    selector = RegionSelector()
    region = selector.select_region()
    
    if region:
        print("📸 Capturing selected region...")
        img = capture_region(region)
        
        edited_img = edit_image(img)
        
        if edited_img:
            filepath = save_screenshot(edited_img)
            print(f"✓ Saved: {filepath}")
        else:
            print("❌ Cancelled")
    else:
        print("❌ Cancelled")


def process_action(action):
    """Process action in main thread"""
    if action == 'fullscreen':
        take_screenshot_fullscreen()
    elif action == 'region':
        take_screenshot_region()
    elif action == 'settings':
        settings_manager.show_settings_window()


def main():
    # Load current hotkey settings for display
    hk_full = settings_manager.get('hotkey_fullscreen', 'Alt+S')
    hk_region = settings_manager.get('hotkey_region', 'Alt+R')
    hk_settings = settings_manager.get('hotkey_settings', 'Ctrl+P')
    
    print("=" * 60)
    print("  📷 Screenshot Tool Running")
    print("=" * 60)
    print(f"  Hotkeys (from settings):")
    print(f"    {hk_full or '(disabled)'} = Capture Fullscreen")
    print(f"    {hk_region or '(disabled)'} = Capture Region")
    print(f"    {hk_settings or '(disabled)'} = Open Settings")
    print(f"    CTRL+C = Quit")
    print(f"\n  Save location: {Config.SAVE_FOLDER}")
    print("=" * 60)
    
    hotkey_thread = HotkeyThread()
    hotkey_thread.start()
    
    # Give thread time to register hotkeys
    time.sleep(0.5)
    
    try:
        while True:
            try:
                # Check for actions from hotkey thread (non-blocking with timeout)
                action = action_queue.get(timeout=0.1)
                process_action(action)
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        print("\n👋 Exiting...")


if __name__ == "__main__":
    main()